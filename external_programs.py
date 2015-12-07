""" Run an external program on the current file, selection or nothing, pass
the data to the program via a single argument, its standard input stream, or
nothing, write back the result from the program taken from its standard output
stream, inserted at the caret, written as a replacement of the selected text,
to an output panel, or to nothing. Provide a work-around for `exec` from
`*.sublime-commands` files.

See [README](READEME.md).

Limitations:
 * Change to the "output_panel_name" setting, requires a restart.
 * Change to the "errors_panel_name" setting, requires a restart.

"""

import os.path
import sublime
import sublime_plugin
import subprocess

SETTINGS = sublime.load_settings("External_Programs.sublime-settings")
PREFERENCES = sublime.load_settings("Preferences.sublime-settings")


# Build_Like
# ============================================================================

# Default when no settings found
# ----------------------------------------------------------------------------
DEFAULT_FILE_REGEX = "^(.+):([0-9]+):() (.+)$"

# String constants from Sublime Text
# ----------------------------------------------------------------------------
S_CMD = "cmd"
S_EXEC = "exec"
S_FILE = "file"
S_FILE_REGEX = "file_regex"
S_WORKING_DIR = "working_dir"
S_DEFAULT_FILE_REGEX = "default_file_regex"

# String constants defined for this command
# ----------------------------------------------------------------------------
S_DEFAULT_REGEX = "default_file_regex"


# Settings
# ----------------------------------------------------------------------------
def get_default_file_regex():
    """ Return default file regex after settings or else a default. """
    result = (
        SETTINGS.get(S_DEFAULT_FILE_REGEX)
        if SETTINGS.has(S_DEFAULT_FILE_REGEX)
        else DEFAULT_FILE_REGEX)
    return result


# The class
# ----------------------------------------------------------------------------
class BuildLikeCommand(sublime_plugin.WindowCommand):

    """ A window command to run an external command on a file, using `exec`.

    See [README](READEME.md) on section `like_build`.

    """

    def __init__(self, arg2):
        """ Just invoke the parent class constructor. """
        super().__init__(arg2)

    def run(self, executable, file_regex=None):
        """ Invoke `executable` using `exec`.

        If there's no active file (on disk) in the active window, display an
        error message in the status bar, and do nothing. Otherwise, output
        goes to the `exec` output panel as usual.

        Note: pass a standard regular expression for `file_regex` to `exec`.

        """
        if file_regex is None:
            file_regex = get_default_file_regex()
        variables = self.window.extract_variables()
        if S_FILE not in variables:
            sublime.status_message("Error: no file")
        else:
            file = variables[S_FILE]
            parts = os.path.split(file)
            directory = parts[0]
            filename = parts[1]
            self.window.run_command(
                S_EXEC,
                {
                    S_CMD: [executable, filename],
                    S_WORKING_DIR: directory,
                    S_FILE_REGEX: get_default_file_regex(),
                    })

    @staticmethod
    def description():
        """ Return a long sentence as a description. """
        return (
            "Run an external command with the current file path and name as "
            "a single argument.")


# External_Command
# ============================================================================

# Main entry point is `run`
#
# Settings are handle by:
#  * `ERRORS_PANEL_NAME`
#  * `OUTPUT_PANEL_NAME`
#  * `update_color_scheme`
#  * `get_timeout_delay`
#
# Parameters are interpreted by:
#  * `get_output_method`     for `destination`
#  * `get_invokation_method` for `executable`
#  * `setup_panels`          for `panels`
#  * `get_input`             for `source`
#  * `get_invokation_method` for `through`
#
# Parameter values are handled by:
#  * `get_insert_replace_writer`   for `destination:insert_replace`
#  * `get_nothing_writer`          for `destination:nothing`
#  * `get_output_panel_writer`     for `destination:output_panel`
#  * `setup_panels` it-self        for `panels:accumulate`
#  * `erase_view_content`          for `panels:reset`
#  * `get_file_name`               for `source:file_name`
#  * `get_input` it-self           for `source:nothing`
#  * `get_selected_text`           for `source:selected_text`
#  * `invok_using_nothing`         for `though:nothing`
#  * `invok_using_single_argument` for `though:single_argument`
#  * `invok_using_stdin`           for `though:stdin`

# Default when no settings found
# ----------------------------------------------------------------------------
DEFAULT_COLOR_SCHEME = None
DEFAULT_ERRORS_PANEL_NAME = "errors"
DEFAULT_OUTPUT_PANEL_NAME = "output"
DEFAULT_TIMEOUT_DELAY = 3  # Seconds, not milliseconds.

# String constants from Sublime Text
# ----------------------------------------------------------------------------
S_CHARACTERS = "characters"
S_COLOR_SCHEME = "color_scheme"
S_INSERT = "insert"
S_PANEL = "panel"
S_SHOW_PANEL = "show_panel"

# String constants defined for this command
# ----------------------------------------------------------------------------
S_ACCUMULATE = "accumulate"
S_ERRORS_PANEL_NAME = "errors_panel_name"
S_FILE_NAME = "file_name"
S_INSERT_REPLACE = "insert_replace"
S_NOTHING = "nothing"
S_OUTPUT_PANEL = "output_panel"
S_OUTPUT_PANEL_NAME = "output_panel_name"
S_RESET = "reset"
S_SELECTED_TEXT = "selected_text"
S_SINGLE_ARGUMENT = "single_argument"
S_STDIN = "stdin"
S_TIMEOUT_DELAY = "timeout_delay"

# Constants from settings
# ----------------------------------------------------------------------------
ERRORS_PANEL_NAME = (  # Changes requires restart.
    SETTINGS.get(S_ERRORS_PANEL_NAME)
    if PREFERENCES.has(S_ERRORS_PANEL_NAME)
    else DEFAULT_ERRORS_PANEL_NAME)

OUTPUT_PANEL_NAME = (  # Changes requires restart.
    SETTINGS.get(S_OUTPUT_PANEL_NAME)
    if PREFERENCES.has(S_OUTPUT_PANEL_NAME)
    else DEFAULT_OUTPUT_PANEL_NAME)


# The class
# ----------------------------------------------------------------------------
class ExternalProgramCommand(sublime_plugin.TextCommand):
    """ Full integration of external program, mainly as text command.

    See [README](READEME.md) on section `external_program`.

    """

    BUSY = False
    ERRORS_PANEL = None
    OUTPUT_PANEL = None
    COLOR_SCHEME = None
    COLOR_SCHEME_HANDLER_REGISTERED = False

    def __init__(self, arg2):
        """ Just invoke the parent class constructor. """
        super().__init__(arg2)

    # Panels
    # ------------------------------------------------------------------------

    # ### Color scheme

    @classmethod
    def update_color_scheme(cls):
        """ Set `COLOR_SCHEME` after preferences.

        `COLOR_SCHEME` may still be `None`.

        """
        cls.COLOR_SCHEME = (
            PREFERENCES.get(S_COLOR_SCHEME)
            if PREFERENCES.has(S_COLOR_SCHEME)
            else DEFAULT_COLOR_SCHEME)

    @classmethod
    def set_panel_color_scheme(cls, panel):
        """ Set panel color scheme to `COLOR_SCHEME`. """
        if cls.COLOR_SCHEME is None:
            cls.update_color_scheme()
        if cls.COLOR_SCHEME is not None:
            panel.settings().set(S_COLOR_SCHEME, cls.COLOR_SCHEME)

    @classmethod
    def on_color_scheme_changed(cls):
        """ Invoke `update_color_scheme` and `set_panel_color_scheme`. """
        cls.update_color_scheme()
        if cls.ERRORS_PANEL is not None:
            cls.set_panel_color_scheme(cls.ERRORS_PANEL)
        if cls.OUTPUT_PANEL is not None:
            cls.set_panel_color_scheme(cls.OUTPUT_PANEL)

    @classmethod
    def register_color_scheme_handler(cls):
        """ Register `on_color_scheme_changed`. """
        if not cls.COLOR_SCHEME_HANDLER_REGISTERED:
            PREFERENCES.add_on_change(
                S_COLOR_SCHEME,
                cls.on_color_scheme_changed)
            cls.COLOR_SCHEME_HANDLER_REGISTERED = True

    # ### Main

    def errors_panel(self):
        """ Return the single instance of the panel for errors output.

        The panel is created on the first invocation.

        """
        cls = type(self)
        if cls.ERRORS_PANEL is None:
            window = self.view.window()
            cls.ERRORS_PANEL = window.create_output_panel(ERRORS_PANEL_NAME)
            self.set_panel_color_scheme(cls.ERRORS_PANEL)
            self.register_color_scheme_handler()

        result = cls.ERRORS_PANEL
        return result

    def output_panel(self):
        """ Return the single instance of the panel for “normal” output.

        The panel is created on the first invocation.

        """
        cls = type(self)
        if cls.OUTPUT_PANEL is None:
            window = self.view.window()
            cls.OUTPUT_PANEL = window.create_output_panel(OUTPUT_PANEL_NAME)
            self.set_panel_color_scheme(cls.OUTPUT_PANEL)
            self.register_color_scheme_handler()

        result = cls.OUTPUT_PANEL
        return result

    def write_error(self, text):
        """ Write `text` to the errors panel and shows it. """
        errors_panel = self.errors_panel()
        window = self.view.window()
        errors_panel.run_command(S_INSERT, {S_CHARACTERS: text})
        window.run_command(
            S_SHOW_PANEL,
            {S_PANEL: "output.%s" % ERRORS_PANEL_NAME})

    @staticmethod
    def erase_view_content(view):
        """ Erase all text in `view`. """
        region = sublime.Region(0, view.size())
        view.sel().add(region)
        view.run_command(S_INSERT, {S_CHARACTERS: ""})

    def setup_panels(self, panels):
        """ Handle the `panels` argument to `external_command`.

        If the `panels` value is invalid, don't treat as error,
        and use the default instead (`reset`).

        """
        if panels == S_ACCUMULATE:
            # Keep their content
            pass
        else:
            self.erase_view_content(self.output_panel())
            self.erase_view_content(self.errors_panel())

    # See also `get_output_panel_writer`.

    # Input (text content passed to invoked program)
    # ------------------------------------------------------------------------

    def get_file_name(self):
        """ Return the simple file name of the active file or `None`.

        If there is no active file for the active view, additionally to
        returning `None`, display an error message in the status bar.

        This is to be the argument passed to the invoked program, when
        `source` is `file_name`.

        """
        result = None
        view = self.view
        file = view.file_name()
        if file is None:
            sublime.status_message("Error: no file")
        else:
            result = os.path.split(file)[1]
        return result

    def get_selected_text(self):
        """ Return the text in the current selection or `None`.

        If there is no selection, a multiple selection or the selection is
        empty, for the active window, additionally to returning `None`,
        display an error message in the status bar.

        This is to be the argument passed to the invoked program, when
        `source` is `selected_text`.

        """
        result = None
        view = self.view
        sel = view.sel()
        if len(sel) == 0:
            sublime.status_message("Error: no selection")
        elif len(sel) > 1:
            sublime.status_message("Error: multiple selections")
        else:
            region = sel[0]
            if region.a == region.b:  # Not `a >= b` (reversed region).
                sublime.status_message("Error: empty selection")
            else:
                result = view.substr(region)
        return result

    def get_input(self, source):
        """ Return the text to be passed to the program or `None`.

        If `source` is unknown, additionally to returning `None`, display an
        error message in the status bar.

        This method handles the `source` argument to `external_command`.

        """
        result = None
        if source == S_SELECTED_TEXT:
            result = self.get_selected_text()
        elif source == S_FILE_NAME:
            result = self.get_file_name()
        elif source == S_NOTHING:
            result = ""
        else:
            sublime.status_message(
                "Error: unknown source `%s`"
                % source)
        return result

    # Output (how to write text returned by invoked program)
    # ------------------------------------------------------------------------

    def get_insert_replace_writer(self, edit):
        """ Return a method to write to the current selection or `None`.

        If there is no selection or a multiple selection, additionally to
        returning `None`, display an error message in the status bar.

        The method returned expects a single `text` argument.

        This is the method to be used when `destination` is `insert_replace`.
        The selection may be empty, in which case it ends to be an “insert”,
        otherwise, it ends to be a “replace”.

        """
        result = None
        view = self.view
        sel = view.sel()
        if len(sel) == 0:
            sublime.status_message("Error: no selection")
        elif len(sel) > 1:
            sublime.status_message("Error: multiple selections")
        else:
            region = sel[0]
            result = lambda text: view.replace(edit, region, text)
        return result

    def get_output_panel_writer(self):
        """ Return a method to write to the output panel.

        The method returned expects a single `text` argument.

        This is the method to be used when `destination` is `output_panel`.

        """

        def write_output(text):
            """ Write `text` to the output panel and shows it. """
            output_panel = self.output_panel()
            window = self.view.window()
            output_panel.run_command(S_INSERT, {S_CHARACTERS: text})
            window.run_command(
                S_SHOW_PANEL,
                {S_PANEL: "output.%s" % OUTPUT_PANEL_NAME})

        result = write_output
        return result

    @staticmethod
    def get_nothing_writer():
        """ Return a method to write nothing.

        The method returned expects a single `text` argument (which is
        ignored).

        This is the method to be used when `destination` is `nothing`.

        """
        result = lambda text: None
        return result

    def get_output_method(self, destination, edit):
        """ Return the method to write the program result or `None`.

        If `destination` is unknown, additionally to returning `None`, display
        an error message in the status bar.

        The method returned expects a single `text` argument.

        This method handles the `destination` argument to `external_command`.

        """
        result = None
        if destination == S_INSERT_REPLACE:
            result = self.get_insert_replace_writer(edit)
        elif destination == S_OUTPUT_PANEL:
            result = self.get_output_panel_writer()
        elif destination == S_NOTHING:
            result = self.get_nothing_writer()
        else:
            sublime.status_message(
                "Error: unknown destination `%s`"
                % destination)
        return result

    # Process
    # ------------------------------------------------------------------------

    @staticmethod
    def get_timeout_delay():
        """ Return timeout delay after settings or else a default. """
        result = (  # Changes requires restart.
            SETTINGS.get(S_TIMEOUT_DELAY)
            if PREFERENCES.has(S_TIMEOUT_DELAY)
            else DEFAULT_TIMEOUT_DELAY)
        return result

    def get_working_directory(self):
        """ Return the directory of the active file or `None`.

        This is the directory to be used as the working directory of the
        invoked program.

        """
        result = None
        view = self.view
        file = view.file_name()
        if file is not None:
            result = os.path.split(file)[0]
        return result

    @classmethod
    def get_invokation_method(cls, executable, directory, through):
        """ Return the method to invoke the program or `None`.

        If `through` is unknown, additionally to returning `None`, display an
        error message in the status bar.

        This method handles the `through` argument to `external_command` and
        articulates the overall invocation process.

        The method depends on the way the parameter is passed to the program
        to be invoked.

        The method returned expects a single `text` argument and returns a
        triplet `(stdout, stderr, return_code)` where `stdout` and `stderr`
        are strings content returned by the program on these streams and
        `return_code` is the integer status returned by the program. If an
        error occurs (not from the program), the method returns both `stdout`
        and `return_code` set to `None`, however, `stderr` is still a string,
        as indeed, if the program was stopped due to a time-out, it may have
        sent something to `stderr` (however, `stdout` is then to be ignored,
        and that's why it is set to `None`).

        In case of error, the method returned, will write an error message to
        the status bar.

        """

        timeout_delay = cls.get_timeout_delay()

        # ### Exception handling

        def on_error(error, process):
            """ Handle `OSError` and `TimeoutExpired`, returning `stderr`.

            If no `stderr` content can be returned, return an empty string.

            Write an error message to the status bar, as much as possible.

            """
            stderr = ""
            try:
                raise error
            except OSError:
                sublime.status_message(
                    "Error: could not run `%s`"
                    % executable)
            except subprocess.TimeoutExpired as timeout:
                stderr = timeout.stderr
                process.kill()
                (_stdout, stderr_tail) = process.communicate()
                stderr += stderr_tail
                sublime.status_message(
                    "Error: `%s` takes too long"
                    % executable)
            except:  # pylint: disable=bare-except
                sublime.status_message(
                    "Unknown error while attempting to run `%s`"
                    % executable)
            return stderr

        # ### Methods

        def invok_using_stdin(text):
            """ Invoke the program with `text` passed through its `stdin`.

            Return `(stdout, stderr, return_code)`.

            """
            try:
                process = subprocess.Popen(
                    [executable],
                    cwd=directory,
                    universal_newlines=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                (stdout, stderr) = process.communicate(
                    input=text,
                    timeout=timeout_delay)
                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        def invok_using_single_argument(text):
            """ Invoke the program with `text` passed as a single argument.

            Return `(stdout, stderr, return_code)`.

            """
            try:
                process = subprocess.Popen(
                    [executable, text],
                    cwd=directory,
                    universal_newlines=True,
                    stdin=None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                (stdout, stderr) = process.communicate(timeout=timeout_delay)
                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        def invok_using_nothing():
            """ Invoke the program with nothing (no argument, no input).

            Return `(stdout, stderr, return_code)`.

            """
            try:
                process = subprocess.Popen(
                    [executable],
                    cwd=directory,
                    universal_newlines=True,
                    stdin=None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                (stdout, stderr) = process.communicate(timeout=timeout_delay)
                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        # ### Main

        if through == S_STDIN:
            result = invok_using_stdin
        elif through == S_SINGLE_ARGUMENT:
            result = invok_using_single_argument
        elif through == S_NOTHING:
            result = invok_using_nothing
        else:
            result = None
            sublime.status_message(
                "Error: unknown channel `%s`"
                % through)

        return result

    # Main
    # ------------------------------------------------------------------------

    def run(self,
            edit,
            executable,
            source,
            through,
            destination,
            panels=S_RESET):

        """ Invoke `executable` as specified by the three last parameters.

        In case of error(s), write an error message to the status bar.

        Return nothing.

        """
        cls = type(self)
        directory = self.get_working_directory()
        # Parameters interpretation begin
        self.setup_panels(panels)
        input = self.get_input(source)
        invoke = self.get_invokation_method(executable, directory, through)
        output = self.get_output_method(destination, edit)
        # Parameters interpretation end
        if cls.BUSY:
            sublime.status_message("Error: busy")
        elif None not in [input, invoke, output]:
            cls.BUSY = True
            # Core begin
            (result, stderr, return_code) = invoke(input)
            if return_code == 0:
                output(result)
            else:
                sublime.status_message(
                    "Error: `%s` returned status %i"
                    % (executable, return_code))

            if stderr != "":
                self.write_error(stderr)
                self.write_error("\n")
            # Core end
            cls.BUSY = False

    @staticmethod
    def description():
        """ Return a long sentence as a description. """
        return (
            "Typically, run an external command receiving the current "
            "selection on standard input and replace the current selection "
            "with what it writes on standard output.")


# Helper commands
# ----------------------------------------------------------------------------

# ### `external_program_show_errors`

class ExternalProgramShowErrors(sublime_plugin.WindowCommand):
    """ Command to show the errors panel. """

    def __init__(self, arg2):
        """ Just invoke the parent class constructor. """
        super().__init__(arg2)

    def run(self):
        """ Show the errors panel. """
        if ExternalProgramCommand.ERRORS_PANEL is not None:
            self.window.run_command(
                S_SHOW_PANEL,
                {S_PANEL: "output.%s" % ERRORS_PANEL_NAME})
        else:
            sublime.status_message("No errors output so far.")



# ### `external_program_show_output`

class ExternalProgramShowOutput(sublime_plugin.WindowCommand):
    """ Command to show the output panel. """

    def __init__(self, arg2):
        """ Just invoke the parent class constructor. """
        super().__init__(arg2)

    def run(self):
        """ Show the output panel. """
        if ExternalProgramCommand.OUTPUT_PANEL is not None:
            self.window.run_command(
                S_SHOW_PANEL,
                {S_PANEL: "output.%s" % OUTPUT_PANEL_NAME})
        else:
            sublime.status_message("No output result so far.")
