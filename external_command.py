""" Run an external program on the current file, selection or nothing.

Two commands are defined, designed to be used from `*.sublime-commands` files:
`build_like` (`BuildLikeCommand`, a `WindowCommand`) and `external_command`
('ExternalCommandCommand', a `TextCommand`).

For usage, see the documentation of the two individual classes.

Limitations:

 * the `file_regex` argument passed to `exec` by `build_like`, is statically
   defined.
 * the output panel and error panel used by `external_command`, is never
   erased and always accumulates.

"""

import os.path
import sublime
import sublime_plugin
import subprocess


class BuildLikeCommand(sublime_plugin.WindowCommand):

    """ `WindowCommand` to run an external command on a file, using `exec`.

    The build system allows to pass a `$file` argument to external programs
    invoked with `exec`. Defining a command using `exec` is possible from a
    `*.sublime-commands` file, but the `$file` variable is not available in
    this context (and is passed literally to the invoked program). That's the
    reason why this command class was created: it invokes an external program
    though `exec`, passing it the active file name in the active window, even
    when used from a `*.sublime-commands` file.

    The file argument is passed implicitly, as the single argument to the
    external program.

    Example usage from a `*.sublime-commands` file:

        {
            "caption": "Markdown: Preview",
            "command": "build_like",
            "args": { "executable": "multimarkdown-preview" },
        }

    The only required argument to `build_like`, is the executable name or full
    path.

    """

    def __init__(self, arg2):
        """ Just invoke the parent class constructor. """
        super().__init__(arg2)

    def run(self, executable):
        """ Invoke `executable` using `exec`.

        If there's no active file (on disk) in the active window, display an
        error message in the status bar, and do nothing. Otherwise, output
        goes to the `exec` output panel as usual.

        Note: pass a standard regular expression for `file_regex` to `exec`.

        """
        variables = self.window.extract_variables()
        if "file" not in variables:
            sublime.status_message("Error: no file")
        else:
            file = variables["file"]
            parts = os.path.split(file)
            directory = parts[0]
            filename = parts[1]
            self.window.run_command(
                "exec",
                {
                    "cmd": [executable, filename],
                    "working_dir": directory,
                    "file_regex": "^(.+):([0-9]+):() (.+)$",
                    })

    @staticmethod
    def description():
        """ Return a long sentence as a description. """
        return (
            "Run an external command with the current file path and name as "
            "a single argument.")


class ExternalCommandCommand(sublime_plugin.TextCommand):
    """ Full integration of external program, mainly as text command.

    External programs can be invoked with either one of these: the current
    file name, the text content of the current selection or no argument at
    all.

    The output from the external program, taken from its standard output, can
    go to either: replacement of the current selection, insertion at the caret
    location (when the current selection is empty) or to an output panel named
    `output.output`.

    The argument (text in selection or file name or nothing), can be passed to
    the program either: as a single parameter or written to its standard
    input.

    Error stream from the program, is displayed back in an error output panel, 
    named `output.errors`. Other error messages go to the status bar.


    Example usage from a `*.sublime-commands` file:

    {
        "caption": "Text: Format",
        "command": "external_command",
        "args": {
            "executable": "format-text",
            "source": "selected_text",
            "through": "stdin",
            "destination": "insert_replace",
        }
    }

    Valid parameter values:

     * `executable`: [string] name or path to the program.
     * `source`: [enum] "selected_text" | "file_name" | "nothing"
     * `through`: [enum] "stdin" | "single_argument" | "nothing"
     * `destination`: [enum] "insert_replace" | "output_panel"

    All parameters are required.

    Note: for `file_name` the simple file name is passed (base name with
    extension), and the working directory is that of the file.

    """

    BUSY = False
    ERRORS_PANEL = None
    ERRORS_NAME = "errors"
    OUTPUT_PANEL = None
    OUTPUT_NAME = "output"

    def __init__(self, arg2):
        """ Just invoke the parent class constructor. """
        super().__init__(arg2)

    def errors_panel(self):
        """ Return the single instance of the panel for errors output.

        The panel is created on the first invocation.

        """
        cls = type(self)
        if cls.ERRORS_PANEL is None:
            window = self.view.window()
            cls.ERRORS_PANEL = window.create_output_panel(cls.ERRORS_NAME)
            color_scheme = window.active_view().settings().get("color_scheme")
            cls.ERRORS_PANEL.settings().set("color_scheme", color_scheme)

        result = cls.ERRORS_PANEL
        return result

    def output_panel(self):
        """ Return the single instance of the panel for “normal” output.

        The panel is created on the first invocation.

        """
        cls = type(self)
        if cls.OUTPUT_PANEL is None:
            window = self.view.window()
            cls.OUTPUT_PANEL = window.create_output_panel(cls.OUTPUT_NAME)
            color_scheme = window.active_view().settings().get("color_scheme")
            cls.OUTPUT_PANEL.settings().set("color_scheme", color_scheme)

        result = cls.OUTPUT_PANEL
        return result

    def write_error(self, text):
        """ Write `text` to the errors panel and shows it. """
        cls = type(self)
        errors_panel = self.errors_panel()
        window = self.view.window()
        errors_panel.run_command("insert", {"characters": text})
        window.run_command(
            "show_panel",
            {"panel": "output.%s" % cls.ERRORS_NAME})

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

    def get_output_panel_writer(self):
        """ Return a method to write to the output panel.

        The method returned expects a single `text` argument.

        This is the method to be used when `destination` is `output_panel`.

        """
        cls = type(self)
        output_panel = self.output_panel()
        window = self.view.window()
        window.run_command(
            "show_panel",
            {"panel": "output.%s" % cls.OUTPUT_NAME})
        result = lambda text: output_panel.run_command(
            "insert",
            {"characters": text})
        return result

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
            if region.a >= region.b:
                sublime.status_message("Error: empty selection")
            else:
                result = view.substr(region)
        return result

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

    def get_input(self, source):
        """ Return the text to be passed to the program or `None`.

        If `source` is unknown, additionally to returning `None`, display an
        error message in the status bar.

        This method handles the `source` argument to `external_command`.

        """
        result = None
        if source == "selected_text":
            result = self.get_selected_text()
        elif source == "file_name":
            result = self.get_file_name()
        elif source == "nothing":
            result = ""
        else:
            sublime.status_message(
                "Error: unknown source `%s`"
                % source)
        return result

    def get_output_method(self, destination, edit):
        """ Return the method to write the program result or `None`.

        If `destination` is unknown, additionally to returning `None`, display
        an error message in the status bar.

        The method returned expects a single `text` argument.

        This method handles the `destination` argument to `external_command`.

        """
        result = None
        if destination == "insert_replace":
            result = self.get_insert_replace_writer(edit)
        elif destination == "output_panel":
            result = self.get_output_panel_writer()
        else:
            sublime.status_message(
                "Error: unknown destination `%s`"
                % destination)
        return result

    @staticmethod
    def get_invokation_method(executable, directory, through):
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
        and `return_code` set to `None`, however, `stderr` is still a string, as
        indeed, if the program was stopped due to a time-out, it may have sent
        something to `stderr` (however, `stdout` is then to be ignored, and
        that's why it is set to `None`).

        In case of error, the method returned, will write an error message to
        the status bar.

        """

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
            except:  # pylint: disable=broad-except
                sublime.status_message(
                    "Unknown error while attempting to run `%s`"
                    % executable)
            return stderr

        def invok_using_stdin(text):
            """ Invoked the program with `text` passed through its `stdin`.

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
                (stdout, stderr) = process.communicate(input=text, timeout=3)
                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        def invok_using_single_argument(text):
            """ Invoked the program with `text` passed as a single argument.

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
                (stdout, stderr) = process.communicate(timeout=3)
                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        def invok_using_nothing():
            """ Invoked the program with nothing (no argument, no input).

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
                (stdout, stderr) = process.communicate(timeout=3)
                result = (stdout, stderr, process.returncode)
            except Exception as error:  # pylint: disable=broad-except
                result = (None, on_error(error, process), None)
            return result

        if through == "stdin":
            result = invok_using_stdin
        elif through == "single_argument":
            result = invok_using_single_argument
        elif through == "nothing":
            result = invok_using_nothing
        else:
            result = None
            sublime.status_message(
                "Error: unknown channel `%s`"
                % through)

        return result

    def run(self, edit, executable, source, through, destination):
        """ Invoked `executable` as specified by the three last parameters.

        In case of error(s), write an error message to the status bar.

        Return nothing.

        """
        cls = type(self)
        directory = self.get_working_directory()
        input = self.get_input(source)
        invok = self.get_invokation_method(executable, directory, through)
        output = self.get_output_method(destination, edit)
        if cls.BUSY:
            sublime.status_message("Error: busy")
        elif None not in [input, invok, output]:
            cls.BUSY = True
            (result, stderr, return_code) = invok(input)
            if return_code != 0:
                sublime.status_message(
                    "Error: `%s` returned status %i"
                    % (executable, return_code))
            else:
                output(result)

            if stderr != "":
                self.write_error(stderr)
                self.write_error("\n")
            cls.BUSY = False

    @staticmethod
    def description():
        """ Return a long sentence as a description. """
        return (
            "Typically, run an external command receiving the current selection on "
            "standard input and replace the current selection with what it "
            "writes on standard output.")
