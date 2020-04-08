
`External_Programs` for Sublime Text 3
==============================================================================

A plug-in for integration of external programs into Sublime Text 3, as text
commands and window commands.

Program invocation *is not interactive*; if one needs to edit a command line
on each invocation, wish to use an interpreter from Sublime Text or
fully-featured options for program invocation, xe better use one of the three
alternatives mentioned in [Rationals](#rationals).

 * [Summary](#summary)
 * [Installation](#installation)
 * [The `external_program` text command](#external_program)
 * [Rationals](#rationals)
 * [License](#license)


<a name="summary"></a>

Summary
------------------------------------------------------------------------------
Provides `external_program`, a command to run an external program on, either:

 * the current file;
 * the file URI with/without character position/range fragment identifier;
 * the current selection (or whole buffer if there is no selection);
 * nothing.

Passes the data to the program via, either:

 * a single argument;
 * its standard input stream;
 * a temporary file;
 * nothing (makes sense when the argument is nothing).

Writes back the result from the program taken from its standard output (or the
temporary file, if desired), either:

 * inserted at the caret;
 * as a replacement of the selected text (or whole buffer if there was no selection
   in the first place);
 * to an output panel;
 * to a Sublime Text phantom;
 * to nothing.

“Selection” means single selection, not multiple selections. If there is no selection,
the plugin takes the whole buffer, no matter it's saved to a file or not.

In case of errors, messages are written to the status bar. If the invoked
program sent text to its standard error stream, it will be displayed in an
errors output panel. Note: this is not where the plug-in writes its own error
messages, including the program returned status code (when non-zero), which
always go to the status bar.

Two commands are available from the command palette, to show the errors and
output panel: “External Program: Show Errors” and “External Program: Show
Output”.

External programs are executed asynchronously.


<a name="installation"></a>

Installation
------------------------------------------------------------------------------
Either using [Package Control](https://packagecontrol.io), or manually using a
source archive. For manual install in `Packages/`, the plug-in is to be
installed as  `External_Programs`, as using another name, would break file
references.


<a name="external_program"></a>

The `external_program` text command
------------------------------------------------------------------------------
Integration of external program with simple invocation (no complex command
line), mainly as text command.

A part of this command's documentation is in [Summary](#summary).

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
	        "source": "selected_text",
	        "through": "stdin",
          "executable": "format-text",
          // "executable": ["format-text", "--file", "$file"],
          "output": "stdout",
	        "destination": "insert_replace",
	        "panels": "reset"
	    }
	}

Main parameters and their options are shown in the below diagram:

```
   "source"     -->     "through"      -->  "executable" (*) -->     "output"     -->  "destination"
---------------     -----------------       ----------------     ----------------     ----------------
"selected_text"          "stdin"              string|array         "stdout" (d)       "insert_replace"
 "file_name"        "single_argument"                            "temporary_file"      "output_panel"
  "file_uri"        "temporary_file"                                                     "phantom"
  "text_uri"

                                *: required
                                d: default
```

And the additional parameters:

 * `panels`: [enum] `reset` (default) | `accumulate`;

Only `executable` parameter is required. If you omit a parameter that doesn't have a
default value, that feature is not used.

If there won't be any arguments for the `executable`, it can be represented as string.
Otherwise it can be an array which contains all the arguments (see the example above). Also
if the `executable` parameter is an array, it may contain some special variables. These are
[the same variables](http://www.sublimetext.com/docs/3/build_systems.html#variables)
that Sublime Text uses in its build system. See the list below:

|       Variable       |                                     Description                                     |
|----------------------|-------------------------------------------------------------------------------------|
| `$packages`          | The path to the Packages/ folder                                                    |
| `$platform`          | A string containing the platform Sublime Text is running on: `windows`, `osx` or `linux`. |
| `$file`              | The full path, including folder, to the file in the active view.                    |
| `$file_path`         | The path to the folder that contains the file in the active view.                   |
| `$file_name`         | The file name (sans folder path) of the file in the active view.                    |
| `$file_base_name`    | The file name, exluding the extension, of the file in the active view.              |
| `$file_extension`    | The extension of the file name of the file in the active view.                      |
| `$folder`            | The full path to the first folder open in the side bar.                             |
| `$project`           | The full path to the current project file.                                          |
| `$project_path`      | The path to the folder containing the current project file.                         |
| `$project_name`      | The file name (sans folder path) of the current project file.                       |
| `$project_base_name` | The file name, excluding the extension, of the current project file.                |
| `$project_extension` | The extension of the current project file.                                          |

If the command you're running starts a GUI application, then don't set the `destination`
parameter. If the `destination` is set, then the plugin waits for the command's stdout and
return code. This typically ends with a timeout error for a GUI application which
is expected to run for a long time.

When the `destination` is `insert_replace`, modifying selections or the buffer
aborts the command to display results (actual program is not aborted).

When `panels` is `accumulate` means new content to the output and errors
panels, is appended to their previous content.

As for the `through` parameter, `temporary_file` option is useful when sending a
selection string to a command which only accepts a file argument and doesn't support
`stdin`. It saves the selection to a temporary file (located in the `Packages` folder)
and then sends its path to the command as an argument. After the execution is completed,
temporary file is deleted automatically. If you want to read the output from the same
temporary file (instead of `stdout`), set the `output` parameter to `temporary_file`.

More on `source`:

 * `selected_text`: the selected text where the selection is not
    a multiple selection; if there is no selection, whole buffer is used;
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


<a name="rationals"></a>

Rationals
------------------------------------------------------------------------------
The program invocation is purposely simple. This
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
 * If one needs to run external commands interactively, or possibly long
   running process asynchronously, there is also:
   [External Command](https://packagecontrol.io/packages/External%20Command).
 * If one needs fully-featured options, xe better use
   [Commando](https://packagecontrol.io/packages/Commando).

This package with the two firsts, may be installed together, as their features
do not overlap (I'm personally using a patched version of `External Command`
along to `External_Programs`). The third will supersede this one if one wants
features which a purposely simple program invocation will never provides.


<a name="license"></a>

License
------------------------------------------------------------------------------
See [LICENSE](LICENSE) file.

<a href='https://pledgie.com/campaigns/30727'><img
     alt='Donate to software development under BSD license at pledgie.com !'
     src='https://pledgie.com/campaigns/30727.png?skin_name=chrome'
     border='0' ></a>
