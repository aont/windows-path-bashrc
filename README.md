# Managing Windows PATH for MSYS2 and Bash Integration

This Python package helps manage and configure the **Windows PATH environment variable** for use in **MSYS2** and bash shells. It retrieves both **user and system PATH values** from the Windows Registry, splits them into logical groups (e.g., Python, pip, SSH, VS Code), and converts them into **MSYS2-style paths** using `cygpath`.

The tool also ensures that these paths are correctly added to the shell by generating a config snippet and appending it to `~/.bashrc`. This process is **idempotent**, meaning the script won’t add duplicate entries if run multiple times.

Key features include:

* Reading and combining PATH values from the registry
* Filtering and categorizing directories (prepend, append, special cases like VS Code or SSH)
* Converting Windows paths to MSYS2 format
* Automatically updating `~/.bashrc` with PATH adjustments and optional functions (e.g., VS Code CLI support)

In short, this tool makes it easier to **synchronize Windows PATH with MSYS2 environments**, ensuring a smoother developer workflow across shells.

## Installation

Install directly from GitHub using `pip`:

```bash
pip install git+https://github.com/aont/windows-path-bashrc.git
```

The installation exposes a console command named `windows-path-bashrc`.

## Usage

Run the command from a Windows environment where MSYS2 is installed:

```bash
windows-path-bashrc
```

The command emits diagnostic information on `stderr`, writes the generated configuration to `~/.bashrc_winpath`, and ensures that the file is sourced from your main `~/.bashrc` file.
