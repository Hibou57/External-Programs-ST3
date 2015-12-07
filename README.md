
External_Programs for Sublime Text 3
==============================================================================

A plug-in for integration of external programs into Sublime Text 3, as text
commands and window commands.

Summary
------------------------------------------------------------------------------
Provides `external_program`, a command to run an external program on the
current file, selection or nothing, pass the data to the program via a single
argument, its standard input stream, or nothing, write back the result from
the program taken from its standard output stream, inserted at the caret,
written as a replacement of the selected text, to an output panel, or to
nothing.

In case of errors, messages are written to the status bar. If the invoked
program sent text to its standard error stream, it will be displayed in an
errors output panel. Note: this is not where the plug-in writes its own error
messages, which always go to the status bar.

Two commands are available from the command palette, to show the errors and
output panel.

Additionally provides `build_like` a convenient work-around to run a program like in a
build system, from `*.sublime-commands` files (where you add something to the
command palette), with the active file name as an argument: the `$file`
variable only exists for `*.sublime-build` files, not for `*.sublime-commands`
(the variable is left literally as-is, not-expanded). This plug-in provides a
way to work around this. This additional command is independent from the one
described above.


The `build_like` window command
------------------------------------------------------------------------------
A window command to run an external command on a file, using `exec`, like from
a build system, thus with output sent to the build result panel and its
convenient error messages navigation and parsing.

The build system allows to pass a `$file` argument to external programs
invoked with `exec`. Defining a command using `exec` is possible from a
`*.sublime-commands` file, but the `$file` variable is not available in this
context (and is passed literally to the invoked program). That's the reason
why this command exists: it invokes an external program though `exec`, passing
it the active file name in the active window, even when used from a
`*.sublime-commands` file.

The file argument is passed implicitly, as the single argument to the
external program.

Example usage from a `*.sublime-commands` file:

    {
        "caption": "Markdown: Preview",
        "command": "build_like",
        "args": {
        	"executable": "multimarkdown-preview",
        	"file_regex": "^(.+):([0-9]+):() (.+)$",
        },
    }

The only required argument to `build_like`, is the executable name or full
path. The `file_regex` argument may be omitted, in which case it is taken from
the `default_file_regex` setting (see “Preferences/Package Settings/External
Programs”), or if this setting does not exist, the default
`"^(.+):([0-9]+):()(.+)$"` is used.

The active file name is passed to the program, as a simple name (base name
with extension), and the program is executed from the directory owning the
file.

The `external_program` text command
------------------------------------------------------------------------------
Full integration of external program, mainly as text command.

External programs can be invoked with either one of these: the current
file name, the text content of the current selection or no argument at
all.

The output from the external program, taken from its standard output, can
go to either: replacement of the current selection, insertion at the caret
location (when the current selection is empty), to an output panel named
`output.output` or nowhere.

The argument (text in selection or file name or nothing), can be passed to
the program either: as a single parameter or written to its standard
input.

Error stream from the program, is displayed back in an error output panel,
named `output.errors`. Other error messages, not from the program itself go to
the status bar.


Example usage from a `*.sublime-commands` file:

	{
	    "caption": "Text: Format",
	    "command": "external_command",
	    "args": {
	        "executable": "format-text",
	        "source": "selected_text",
	        "through": "stdin",
	        "destination": "insert_replace",
	        "panels": "reset"
	    }
	}

Valid parameter values:

 * `executable`: [string] name or path to the program.
 * `source`: [enum] "selected_text" | "file_name" | "nothing"
 * `through`: [enum] "stdin" | "single_argument" | "nothing"
 * `destination`: [enum] "insert_replace" | "output_panel" | "nothing"
 * `panels`: [enum] "reset" (default) | "accumulate"

All parameters but `panels` are required.

`accumulate` means new content to the output and errors panel, is appended
to their previous content.

Note: for `file_name` the simple file name is passed (base name with
extension), and the working directory is that of the file.

The command uses this settings:

 * `timeout_delay`, which defaults to 3 (seconds, not milliseconds)
 * `output_panel_name`, which defaults to `output`
 * `errors_panel_name`, which defaults to `errors`

If a setting is not found, the above default values are used.

Note: to display a panel using a Sublime Text Command, the panel name must
be prefixed with `output.` (also note the dot). Ex: `output.output`, for
to output panel or `output.errors` for the errors panel. None of these panel
exists before something was to be written to it.

The panels are displayed using the color scheme after Sublime Text
preferences, are switch color scheme when the user change this preference.
