# Managing Windows PATH for MSYS2 and Bash Integration

This Python script helps manage and configure the **Windows PATH environment variable** for use in **MSYS2** and bash shells. It retrieves both **user and system PATH values** from the Windows Registry, splits them into logical groups (e.g., Python, pip, SSH, VS Code), and converts them into **MSYS2-style paths** using `cygpath`.

The script also ensures that these paths are correctly added to the shell by generating a config snippet and appending it to `~/.bashrc`. This process is **idempotent**, meaning the script won’t add duplicate entries if run multiple times.

Key features include:

* Reading and combining PATH values from the registry
* Filtering and categorizing directories (prepend, append, special cases like VS Code or SSH)
* Converting Windows paths to MSYS2 format
* Automatically updating `~/.bashrc` with PATH adjustments and optional functions (e.g., VS Code CLI support)

In short, this tool makes it easier to **synchronize Windows PATH with MSYS2 environments**, ensuring a smoother developer workflow across shells.