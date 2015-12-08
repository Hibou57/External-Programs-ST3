
`External_Programs` for Sublime Text 3
==============================================================================

A plug-in for integration of external programs into Sublime Text 3, as text
commands and window commands.

Program invocation *is not interactive*; if one needs to edit a command line
on each invocation or wish to use an interpreter from Sublime Text, xe better
use one of the two alternatives mentioned in [Rationals][].

 * [Summary][]
 * [Installation][]
 * [The `external_program` text command][]
 * [The `build_like` window command][]
 * [Rationals][]
 * [License][]


Summary
------------------------------------------------------------------------------
Provides `external_program`, a command to run an external program on, either:

 * the current file;
 * the file URI with/without character position/range fragment identifier;
 * the current selection;
 * nothing.

Passes the data to the program via, either:

 * a single argument;
 * its standard input stream;
 * nothing (makes sense when the argument is nothing).

Writes back the result from the program taken from its standard output,
either:

 * inserted at the caret;
 * as a replacement of the selected text;
 * to an output panel;
 * to nothing.

“Selection” means single selection, not multiple selections.

In case of errors, messages are written to the status bar. If the invoked
program sent text to its standard error stream, it will be displayed in an
errors output panel. Note: this is not where the plug-in writes its own error
messages, including the program returned status code (when non-zero), which
always go to the status bar.

Two commands are available from the command palette, to show the errors and
output panel: “External Program: Show Errors” and “External Program: Show
Output”.

External programs are executed *synchronously*.

Additionally provides `build_like` a convenient work-around to run a program
like in a build system, from `*.sublime-commands` files (where you add
something to the command palette), with the active file name as an argument:
the `$file` variable only exists for `*.sublime-build` files, not for
`*.sublime-commands` files (where the variable is left literally as-is,
not-expanded). This plug-in provides a way to work around this. This
additional command is independent from the one described above.


Installation
------------------------------------------------------------------------------
The plug-in is to be installed as `External_Programs`. Using another name,
would break file references.


The `external_program` text command
------------------------------------------------------------------------------
Integration of external program with simple invocation (no complex command
line), mainly as text command.

A part of this command's documentation is in [Summary][].

Two helper commands are provided:

 * `external_program_show_errors`;
 * `external_program_show_output`.

 Which are available from the command palette as:

 * “External Program: Show Errors”;
 * “External Program: Show Output”.

### Creating a command

Example usage from a `*.sublime-commands` file:

	{
	    "caption": "Text: Format",
	    "command": "external_program",
	    "args": {
	        "executable": "format-text",
	        "source": "selected_text",
	        "through": "stdin",
	        "destination": "insert_replace",
	        "panels": "reset"
	    }
	}

Valid parameter values:

 * `destination`: [enum] `insert_replace` | `output_panel` | `nothing`;
 * `executable`: [string] name or path to the program;
 * `panels`: [enum] `reset` (default) | `accumulate`;
 * `source`: [enum] `selected_text`|`file_name`|`file_uri`|`text_uri`|`nothing`;
 * `through`: [enum] `stdin` | `single_argument` | `nothing`.

All parameters but `panels` are required.

When `panels` is `accumulate` means new content to the output and errors
panels, is appended to their previous content.

More mon `source`:

 * `selected_text`: the selected text where the selection is not empty and not
    a multiple selection;
 * `file_name`: the simple file name, that is, base name with extension (note
    the working directory is that of the file);
 * `file_uri`: URI with the `file:` protocol and an absolute path,
    percent-encoded as necessary;
 * `text_uri`: file URI with text position or range fragment identifier, after
    [RFC 5147](http://tools.ietf.org/html/rfc5147), using the `char` scheme
    only, where the selection is not a multiple selection (when no selection,
    this is the same as `file_uri`).

### Settings

The command uses these settings:

 * `errors_panel_name`, which defaults to `errors`;
 * `output_panel_name`, which defaults to `output`;
 * `timeout_delay`, which defaults to 3 (seconds, not milliseconds).

If a setting is not found, the above default values are used.

Changing the `errors_panel_name` and `output_panel_name` settings, actually
requires a restart to apply (this may change in a future version).

Notes: to display a panel using a Sublime Text Command, the panel name must
be prefixed with `output.` (also note the dot). Ex: `output.output`, for
the output panel or `output.errors` for the errors panel. None of these two
panels exists before something was to be written to it.

The panels are displayed using the color scheme after the corresponding
Sublime Text preferences, and panels switch color scheme when this preference
is changed.


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

### Creating a command

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

### Settings

`default_file_regex`, as described above.


Rationals
------------------------------------------------------------------------------
The program invocation is purposely simple and executed synchronously. This
plug-in provides what I believe should be part of the core of an editor, and
that's not the purpose of an editor to be another shell or to provide command
line edition features (that's the purpose of plug-ins). So there never will be
more than single argument passing or (exclusive or) passing via standard input
stream.

This plug-in is to invoke external specially crafted simple commands as
external programs or wrapper scripts (which is a convenient tactic, as it
allows the reuse of these commands from editor to editor, in a simple manner):

 * If one needs to run a shell or interpreter from from Sublime Text, xe
   better use
   [External REPL](https://packagecontrol.io/packages/External%20REPL) for
   this purpose.
 * If one needs to run external commands interactively without wishing for an
   interpreter, xe better use
   [External Command](https://packagecontrol.io/packages/External%20Command),
   a plug-in, similar to this one at a abstract level, but different
   enough for this plug-in to have a reason to be.
 * If one needs to run possibly long running commands asynchronously, xe
   better use
   [External Command](https://packagecontrol.io/packages/External%20Command).

They may be installed together, as their features do not overlap (I'm
personally using a patched version of `External Command` along to
`External_Programs`).


License
------------------------------------------------------------------------------
See [LICENSE](LICENSE) file.

<a href='https://pledgie.com/campaigns/30727'><img
     alt='Donate to software development under BSD license at pledgie.com !'
     src='https://pledgie.com/campaigns/30727.png?skin_name=chrome'
     border='0' ></a>
