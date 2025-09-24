"""Utilities for synchronising Windows PATH entries with MSYS2 bash."""
from __future__ import annotations

from json.encoder import encode_basestring as double_quote
import pathlib
import subprocess
import sys
import typing

__all__ = [
    "get_env_path",
    "get_combined_path_list",
    "split_path",
    "cygpath",
    "get_home",
    "ensure_bashrc_config",
    "main",
]


def get_env_path(user: bool) -> str:
    """Retrieve the ``Path`` environment variable from the Windows registry."""
    import sys
    import winreg

    if user:
        root = winreg.HKEY_CURRENT_USER
        path = r"Environment"
    else:
        root = winreg.HKEY_LOCAL_MACHINE
        path = r"SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"

    try:
        with winreg.OpenKey(root, path) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return value
    except FileNotFoundError:
        sys.stderr.write(f"get_env_path: Path not found: user={user!r}\n")
    return ""


def get_combined_path_list(expandvars: bool = True) -> typing.List[str]:
    """Retrieve and combine the user and system PATH variables into a list."""
    import os

    user_path = get_env_path(True)
    system_path = get_env_path(False)

    if expandvars:
        do_expandvars = os.path.expandvars
    else:
        def do_expandvars(value: str) -> str:
            return value

    user_list = [do_expandvars(p).rstrip("\\") for p in user_path.split(";") if p]
    system_list = [do_expandvars(p).rstrip("\\") for p in system_path.split(";") if p]

    return system_list + user_list


def split_path(dirs: typing.List[str]) -> typing.Dict[str, typing.Any]:
    """Categorise the Windows PATH directories for MSYS2 consumption."""
    import os

    output_dict: typing.Dict[str, typing.Any] = {"append": [], "prepend": []}

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata is not None:
        windowsapps_path = os.path.join(localappdata, r"Microsoft\\WindowsApps")
    else:
        windowsapps_path = None

    for directory in dirs:
        if windowsapps_path is not None and os.path.exists(directory) and os.path.samefile(windowsapps_path, directory):
            continue

        if r"Microsoft VS Code\\bin" in directory:
            output_dict["vscode"] = directory
            continue

        if os.path.isfile(os.path.join(directory, "ssh.exe")):
            output_dict["ssh"] = directory
            continue

        if os.path.isfile(os.path.join(directory, "python.exe")):
            output_dict["prepend"].append(directory)
            continue

        if os.path.isfile(os.path.join(directory, "pip.exe")):
            output_dict["prepend"].append(directory)
            continue

        output_dict["append"].append(directory)

    return output_dict


def cygpath(path_list: typing.List[str], win_to_msys: bool = True) -> typing.List[str]:
    """Convert paths using MSYS2's ``cygpath`` utility."""
    if not isinstance(path_list, list):
        raise TypeError(f"path_list must be list, not {type(path_list).__name__}")

    if win_to_msys:
        cmd = (r"c:\\msys64\\usr\\bin\\cygpath.exe", "-ua", *path_list)
    else:
        cmd = (r"c:\\msys64\\usr\\bin\\cygpath.exe", "-wa", *path_list)

    result = subprocess.run(
        cmd,
        shell=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"cygpath failed: {result.stderr}")

    return result.stdout.splitlines()


def get_home() -> str:
    """Return the ``HOME`` directory reported by MSYS2 bash."""
    return subprocess.check_output(
        [r"C:\\msys64\\usr\\bin\\printenv.exe", "HOME"],
        text=True,
    ).strip()


def ensure_bashrc_config(config_str: str, config_file: str = ".bashrc_winpath") -> None:
    """Write ``config_str`` to ``config_file`` and source it from ``~/.bashrc``."""
    import os

    home_path = get_home()
    home_win = cygpath([home_path], win_to_msys=False)[0]
    config_path_win = os.path.join(home_win, config_file)
    bashrc_path_win = os.path.join(home_win, ".bashrc")
    sys.stderr.write(f"debug: config_path_win={config_path_win!r}\n")
    sys.stderr.write(f"debug: bashrc_path_win={bashrc_path_win!r}\n")

    with open(config_path_win, "wt", encoding="utf-8") as file:
        file.write(config_str)

    source_line = "source " + double_quote("${HOME}/" + config_file)
    bashrc_content = ""
    if os.path.exists(bashrc_path_win):
        with open(bashrc_path_win, "rt", encoding="utf-8") as bashrc_file:
            bashrc_content = bashrc_file.read()

    if source_line not in bashrc_content:
        with open(bashrc_path_win, "at", encoding="utf-8") as bashrc_file:
            if bashrc_content and not bashrc_content.endswith("\n"):
                bashrc_file.write("\n")
            bashrc_file.write(source_line + "\n")


def _build_config_string(
    prepend_dirs_msys: typing.Sequence[str],
    append_dirs_msys: typing.Sequence[str],
    vscode_dir: typing.Optional[str],
    ssh_path: typing.Optional[str],
) -> str:
    config_lines = [
        "PATH=" + double_quote(":".join(prepend_dirs_msys) + ":$PATH"),
        "PATH=" + double_quote("$PATH:" + ":".join(append_dirs_msys)),
    ]

    if vscode_dir is not None:
        vscode_parent = pathlib.Path(vscode_dir).parent
        vscode_parent_msys = cygpath([str(vscode_parent)])[0]
        config_lines.append(
            """function code() {
    local VSCODE_PATH=""" + double_quote(vscode_parent_msys) + """
    VSCODE_DEV= \\
    ELECTRON_RUN_AS_NODE=1 \\
    "${VSCODE_PATH}/Code.exe" \\
    "$(cygpath -w "${VSCODE_PATH}/resources/app/out/cli.js")" \\
    "$@"
}"""
        )

    if ssh_path is not None:
        config_lines.append("export RSYNC_RSH=/usr/bin/ssh")

    return "\n".join(config_lines) + "\n"


def main() -> None:
    """Entry point used by the console script."""
    path_list = get_combined_path_list()
    sys.stderr.write("# path list ====\n")
    for path in path_list:
        sys.stderr.write(path + "\n")

    split_dict = split_path(path_list)

    sys.stderr.write("# split path ====\n")
    sys.stderr.write("## prepend\n")
    for path in split_dict["prepend"]:
        sys.stderr.write(path + "\n")

    sys.stderr.write("## append\n")
    for path in split_dict["append"]:
        sys.stderr.write(path + "\n")

    for key, value in split_dict.items():
        if key not in ("append", "prepend"):
            sys.stderr.write(f"## {key}: {value}\n")

    append_dirs = list(split_dict["append"])
    prepend_dirs = list(split_dict["prepend"])
    ssh_path = split_dict.get("ssh")
    if ssh_path is not None:
        prepend_dirs.append(ssh_path)
    prepend_dirs_msys = cygpath(prepend_dirs)
    append_dirs_msys = cygpath(append_dirs)
    sys.stderr.write("# msys path ====\n")
    sys.stderr.write("## prepend path\n")
    for path in prepend_dirs_msys:
        sys.stderr.write(path + "\n")
    sys.stderr.write("## append path\n")
    for path in append_dirs_msys:
        sys.stderr.write(path + "\n")

    sys.stderr.write("# msys path join ====\n")
    config_str = _build_config_string(
        prepend_dirs_msys,
        append_dirs_msys,
        split_dict.get("vscode"),
        split_dict.get("ssh"),
    )

    sys.stderr.write(config_str)

    ensure_bashrc_config(config_str)


if __name__ == "__main__":  # pragma: no cover - allows ``python -m`` execution
    main()
