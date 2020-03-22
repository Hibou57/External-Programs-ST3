""" Run an external program on the current file, file URI, text URI, selection
or nothing, pass the data to the program via a single argument, its standard
input stream, or nothing, write back the result from the program taken from
its standard output stream, inserted at the caret, written as a replacement of
the selected text, to an output panel, or to nothing. Provide a work-around
for `exec` from `*.sublime-commands` files.

See [README](README.md).

Limitations:

 * Change to the "output_panel_name" setting, requires a restart.
 * Change to the "errors_panel_name" setting, requires a restart.

"""

import os.path
import sublime
import sublime_plugin
import subprocess
import urllib.parse
import html
import random
import tempfile


PREFERENCES_FILE = "Preferences.sublime-settings"
SETTINGS_FILE = "External_Programs.sublime-settings"
PREFERENCES = None  # Initialized by `plugin_loaded`
SETTINGS = None  # Initialized by `plugin_loaded`


# External_Program
# ============================================================================

# Main entry point is `run`
#
#
# Settings are handled by:
#
#  * `ERRORS_PANEL_NAME`
#  * `OUTPUT_PANEL_NAME`
#  * `update_color_scheme`
#  * `get_timeout_delay`
#
#
# Parameters are interpreted by:
#
#  * `get_output_method`     for `destination`
#  * `get_invokation_method` for `executable`
#  * `setup_panels`          for `panels`
#  * `get_input`             for `source`
#  * `get_invokation_method` for `through`
#
#
# Parameter values are handled by:
#
#  * `get_insert_replace_writer`    for `destination:insert_replace`
#  * `get_nothing_writer`           for `destination` not set
#  * `get_output_panel_writer`      for `destination:output_panel`
#  * `get_phantom_writer`           for `destination:phantom`
#  * `setup_panels` it-self         for `panels:accumulate`
#  * `erase_view_content`           for `panels:reset`
#  * `get_file_name`                for `source:file_name`
#  * `get_file_uri`                 for `source:file_uri`
#  * `get_input` it-self            for `source` not set
#  * `get_selected_text`            for `source:selected_text`
#  * `get_text_uri`                 for `source:text_uri`
#  * `invoke_using_nothing`         for `though` not set
#  * `invoke_using_single_argument` for `though:single_argument`
#  * `invoke_using_stdin`           for `though:stdin`


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
S_FILE_URI = "file_uri"
S_INSERT_REPLACE = "insert_replace"
S_OUTPUT_PANEL = "output_panel"
S_OUTPUT_PANEL_NAME = "output_panel_name"
S_PHANTOM = "phantom"
S_RESET = "reset"
S_SELECTED_TEXT = "selected_text"
S_SINGLE_ARGUMENT = "single_argument"
S_TEMPORARY_FILE = "temporary_file"
S_STDIN = "stdin"
S_TEXT_URI = "text_uri"
S_TIMEOUT_DELAY = "timeout_delay"

# Constants from settings
# ----------------------------------------------------------------------------
ERRORS_PANEL_NAME = None  # Initialized by `plugin_loaded`
OUTPUT_PANEL_NAME = None  # Initialized by `plugin_loaded`


# The class
# ----------------------------------------------------------------------------
class ExternalProgramCommand(sublime_plugin.TextCommand):

    """ Integration of external program, mainly as text command.

    See [README](README.md) on section `external_program`.

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
        cls.COLOR_SCHEME = PREFERENCES.get(
            S_COLOR_SCHEME,
            DEFAULT_COLOR_SCHEME)

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

    # ### Helper

    def get_text_fragment_identifier(self):
        """ Return a character position or range identifier after RFC 5147.

        The identifier returned contains the `#` prefix and if if there is no
        selection, return an empty string, so that the result can be directly
        appended to an URI.

        Display an error in the status bar and return `None`, in case of
        multiple selection.

        """
        result = None
        view = self.view
        sel = view.sel()
        if len(sel) == 0:
            result = ""
        elif len(sel) > 1:
            sublime.status_message("Error: multiple selections")
        else:
            region = sel[0]
            if region.a == region.b:
                result = "#char=%i" % region.a
            else:
                result = "#char=%i,%i" % (region.a, region.b)
        return result

    # ### Main

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

    def get_file_uri(self):
        """ Return the URI of the active file or `None`.

        If there is no active file for the active view, additionally to
        returning `None`, display an error message in the status bar.

        This is to be the argument passed to the invoked program, when
        `source` is `file_uri`.

        """
        result = None
        view = self.view
        file = view.file_name()
        if file is None:
            sublime.status_message("Error: no file")
        else:
            path = os.path.abspath(file)
            path = urllib.parse.quote(path)
            result = "file://%s" % path
        return result

    def get_text_uri(self):
        """ Return text URI of selection in the active file or `None`.

        If there is no selection, the result is the same as the file URI. The
        fragment identifier is from `get_text_fragment_identifier`.

        If there is no active file or a multiple selection, display an error
        message in the status bar.

        This is to be the argument passed to the invoked program, when
        `source` is `text_uri`.

        """
        file_uri = self.get_file_uri()
        if file_uri is not None:
            text_fid = self.get_text_fragment_identifier()
            if text_fid is not None:
                result = file_uri + text_fid
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

            if region.a == region.b:
                region = sublime.Region(0, view.size())

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
        elif source == S_FILE_URI:
            result = self.get_file_uri()
        elif source == S_TEXT_URI:
            result = self.get_text_uri()
        elif source is None:
            result = ""
        else:
            sublime.status_message(
                "Error: unknown source `%s`"
                % source)
        return result

    # Output (how to write text returned by invoked program)
    # ------------------------------------------------------------------------

    def get_insert_replace_writer(self, edit, source):
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

            if region.a == region.b and source == S_SELECTED_TEXT:
                region = sublime.Region(0, view.size())

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

    def get_phantom_writer(self):
        """ Return a method to write to a phantom.

        The method returned expects a single `text` argument.

        This is the method to be used when `destination` is `phantom`.
        """

        def write_output(text):
            """ Write `text` to a phantom. """

            style = '''
                <style>
                    html.dark {
                        background-color: var(--yellowish);
                    }
                    html.light {
                        background-color: #88db7d;
                    }
                    body {
                        padding-right: 1rem;

                        color: black;
                    }
                    .hide {
                        color: black;

                        text-decoration: none;
                    }
                </style>
            '''

            html_content = (
                "<body id='external-programs'>"
                    + style
                    + "<a class='hide' href='hide'>&nbsp;" + chr(0x00D7) + "&nbsp;</a>&nbsp;"
                    + "<span class='command-output'>"
                        + html.escape(text.strip()).replace("\n", "<br>")
                    + "</span>"
                + "</body>"
            )

            phantom_id = str(random.randrange(1, 1000000))
            region_end = self.view.sel()[0].end()

            self.view.add_phantom(
                # Sublime Text Phantom API doesn't provide a native mechanism to
                # hide a single phantom. In order to emulate that feature, we use
                # unique keys as "phantom set" key for each phantom and later use
                # that key to hide a particular phantom.
                "external_programs/" + phantom_id,

                # Make sure that the phantom is always displayed at the bottom of a
                # multi-line selection.
                sublime.Region(region_end, region_end),

                html_content,
                sublime.LAYOUT_BLOCK,
                on_navigate = self.get_phantom_navigate_method(phantom_id))

        return write_output

    def get_phantom_navigate_method(self, phantom_id):
        def on_phantom_navigate(url):
            if url == "hide":
                self.view.erase_phantoms("external_programs/" + phantom_id)

        return on_phantom_navigate

    @staticmethod
    def get_nothing_writer():
        """ Return a method to write nothing.

        The method returned expects a single `text` argument (which is
        ignored).

        This is the method to be used when `destination` is not set.

        """
        result = lambda text: None
        return result

    def get_output_method(self, source, destination, edit):
        """ Return the method to write the program result or `None`.

        If `destination` is unknown, additionally to returning `None`, display
        an error message in the status bar.

        The method returned expects a single `text` argument.

        This method handles the `destination` argument to `external_command`.

        """
        result = None
        if destination == S_INSERT_REPLACE:
            result = self.get_insert_replace_writer(edit, source)
        elif destination == S_OUTPUT_PANEL:
            result = self.get_output_panel_writer()
        elif destination == S_PHANTOM:
            result = self.get_phantom_writer()
        elif destination is None:
            result = self.get_nothing_writer()
        else:
            sublime.status_message(
                "Error: unknown destination `%s`"
                % destination)
        return result

    # Process
    # ------------------------------------------------------------------------

    # ### Helpers

    @staticmethod
    def get_timeout_delay():
        """ Return timeout delay after settings or else a default. """
        result = SETTINGS.get(S_TIMEOUT_DELAY, DEFAULT_TIMEOUT_DELAY)
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

    # ### Main

    @classmethod
    def get_invokation_method(cls, executable, directory, through, output, destination):
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

        # #### Exception handling

        def on_error(error, process):
            """ Handle `OSError` and `TimeoutExpired`, returning `stderr`.

            If no `stderr` content can be returned, return an empty string.

            Write an error message to the status bar, as much as possible.

            """
            stderr = ""
            try:
                raise error
            except OSError:
                message = "Error: Could not run command."
            except subprocess.TimeoutExpired as timeout:
                stderr = getattr(timeout, "stderr", "")
                process.kill()
                (_stdout, stderr_tail) = process.communicate()
                stderr += stderr_tail.decode("utf-8")
                message = "Error: Command takes too long."
            except Exception as err:  # pylint: disable=bare-except
                message = "Error while attempting to run command: " + repr(err)

            print(message);
            sublime.status_message(message);
            return stderr

        # #### Methods

        def invoke_using_stdin(text):
            """ Invoke the program with `text` passed through its `stdin`.

            Return `(stdout, stderr, return_code)`.

            """
            try:
                print("Executing: %s" % executable)

                process = subprocess.Popen(
                    executable,
                    cwd=directory,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                (stdout, stderr) = process.communicate(
                    input=text.encode("utf-8"),
                    timeout=timeout_delay)

                stdout = stdout.decode("utf-8")
                stderr = stderr.decode("utf-8")

                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        def invoke_using_single_argument(text):
            """ Invoke the program with `text` passed as a single argument.

            Return `(stdout, stderr, return_code)`.

            """
            try:
                executable.append(text)

                print("Executing: %s" % executable)

                process = subprocess.Popen(
                    executable,
                    cwd=directory,
                    shell=True,
                    stdin=None,
                    stdout = None if destination is None else subprocess.PIPE,
                    stderr = None if destination is None else subprocess.PIPE)

                if destination is not None:
                    (stdout, stderr) = process.communicate(timeout=timeout_delay)
                    stdout = stdout.decode("utf-8")
                    stderr = stderr.decode("utf-8")

                    result = (stdout, stderr, process.returncode)

                else:
                    # It's probably a GUI application. We're not interested in the output.
                    result = ("", "", 0)

            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        def invoke_using_temporary_file(text):
            """ Save the `text` to a temporary file and invoke the program with its
            path passed as a single argument.

            Return `(output_text, stderr, return_code)`.

            """
            try:
                with tempfile.NamedTemporaryFile(mode = "w+", dir = sublime.packages_path(), prefix = "external-programs-", suffix = ".temp", delete = False, encoding = "utf-8", newline = "") as file:
                    file.write(text)
                    file.close()

                    executable.append(file.name)

                    print("Executing: %s" % executable)

                    process = subprocess.Popen(
                        executable,
                        cwd = directory,
                        shell = True,
                        stdin = None,
                        stdout = None if destination is None else subprocess.PIPE,
                        stderr = None if destination is None else subprocess.PIPE)

                    if destination is not None:
                        (stdout, stderr) = process.communicate(timeout = timeout_delay)
                        stdout = stdout.decode("utf-8")
                        stderr = stderr.decode("utf-8")

                        if output == "temporary_file":
                            output_text = open(file.name, "r", encoding = "utf-8", newline = "").read()

                            if stdout:
                                print(stdout)

                        else:
                            output_text = stdout

                        result = (output_text, stderr, process.returncode)

                    else:
                        # It's probably a GUI application. We're not interested in the output.
                        result = ("", "", 0)

            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)

            finally:
                if os.path.isfile(file.name):
                    os.unlink(file.name)

            return result

        def invoke_using_nothing(ignore):
            """ Invoke the program with nothing (no argument, no input).

            Return `(stdout, stderr, return_code)`.

            """
            try:
                print("Executing: %s" % executable)

                process = subprocess.Popen(
                    executable,
                    cwd=directory,
                    shell=True,
                    stdin=None,
                    stdout = None if destination is None else subprocess.PIPE,
                    stderr = None if destination is None else subprocess.PIPE)

                if destination is not None:
                    (stdout, stderr) = process.communicate(timeout=timeout_delay)
                    stdout = stdout.decode("utf-8")
                    stderr = stderr.decode("utf-8")

                    result = (stdout, stderr, process.returncode)

                else:
                    # It's probably a GUI application. We're not interested in the output.
                    result = ("", "", 0)

            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        # #### Main

        if through == S_STDIN:
            result = invoke_using_stdin
        elif through == S_SINGLE_ARGUMENT:
            result = invoke_using_single_argument
        elif through == S_TEMPORARY_FILE:
            result = invoke_using_temporary_file
        elif through is None:
            result = invoke_using_nothing
        else:
            result = None
            sublime.status_message(
                "Error: unknown channel `%s`"
                % through)

        return result

    def selection_exists(self):
        for region in self.view.sel():
            if not region.empty():
                return True

        return False

    # Main
    # ------------------------------------------------------------------------

    def run(self,
            edit,
            executable,
            source = None,
            through = None,
            output = "stdout",
            destination = None,
            panels=S_RESET):

        """ Invoke `executable` as specified by the next three parameters.

        In case of error(s), write an error message to the status bar.

        Return nothing.

        """
        cls = type(self)
        directory = self.get_working_directory()
        # Parameters interpretation begin
        self.setup_panels(panels)

        if not type(executable) is list:
            executable = [executable]

        # Expand special variables. See: http://www.sublimetext.com/docs/3/build_systems.html#variables
        variables = self.view.window().extract_variables()
        executable = [sublime.expand_variables(value, variables) for value in executable]

        if source is None:
            through = None

        if destination is None:
            output = None

        input = self.get_input(source)
        invoke_method = self.get_invokation_method(executable, directory, through, output, destination)
        output_method = self.get_output_method(source, destination, edit)
        # Parameters interpretation end
        if cls.BUSY:
            sublime.status_message("Error: busy")
        elif None not in [input, invoke_method, output_method]:
            cls.BUSY = True
            # Core begin
            (result, stderr, return_code) = invoke_method(input)

            # Sometimes commands may return an output with a trailing newline. If
            # the input also has a trailing newline then we accept the one in the
            # output, otherwise remove it.
            if result is not None and not input.endswith("\n") and self.selection_exists():
                result = result.rstrip("\n")

            if destination == "insert_replace":
                if result:
                    output_method(result)
                else:
                    sublime.status_message("Empty output.")
            else:
                output_method(result or "[no output]")

            if return_code is not None:
                sublime.status_message("Return code: %i" % return_code)

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


# Load-time
# ============================================================================

def plugin_loaded():
    """ Initialize globals which can't be initialized at module load-time. """

    # Sorry, PyLint, there is no other way.
    # pylint: disable=global-statement

    global ERRORS_PANEL_NAME
    global OUTPUT_PANEL_NAME
    global PREFERENCES
    global SETTINGS

    PREFERENCES = sublime.load_settings(PREFERENCES_FILE)
    SETTINGS = sublime.load_settings(SETTINGS_FILE)

    ERRORS_PANEL_NAME = SETTINGS.get(  # Change requires restart
        S_ERRORS_PANEL_NAME,
        DEFAULT_ERRORS_PANEL_NAME)

    OUTPUT_PANEL_NAME = SETTINGS.get(  # Change requires restart
        S_OUTPUT_PANEL_NAME,
        DEFAULT_OUTPUT_PANEL_NAME)
