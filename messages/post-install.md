
Post Install Message for `External_Programs`
==============================================================================

This package does not automatically add any new directly useful commands,
instead, it allows you to define new ones.

Please, see the
[README](https://github.com/Hibou57/External-Programs-ST3/blob/master/README.md)
file at the GitHub repository.

If you're on a hurry, here is quickly, a snippet of an entry of an ST commands
file, which should match most common needs (example from the README file):

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

Just change the `caption` and `executable` part, and this will likely matches
your needs.

This package neither defines keyboard shortcuts. If you wish to have some, you
will have to edit your user key bindings. However, most of times, it's enough
and better to rely on the command palette.
