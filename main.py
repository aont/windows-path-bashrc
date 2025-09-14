import typing
import subprocess

def get_env_path(root: int, path: str) -> str:
    """
    Retrieve the 'Path' environment variable from the Windows Registry.

    Parameters
    ----------
    root : int
        Registry root key (e.g., winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE).
    path : str
        Registry path where the 'Path' variable is stored.

    Returns
    -------
    str
        The value of the 'Path' variable if found, otherwise "".
    """
    import winreg
    import sys

    try:
        with winreg.OpenKey(root, path) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return value
    except FileNotFoundError:
        sys.stderr.write(f"get_env_path: Path not found: {root=} {path=}\n")
    return ""


def get_combined_path_list(expandvars: bool = True) -> typing.List[str]:
    """
    Retrieve and combine user and system PATH variables into a single list.

    Parameters
    ----------
    expandvars : bool, optional
        If True, expand environment variables (default is True).

    Returns
    -------
    typing.List[str]
        Combined list of system and user paths.
    """
    import winreg
    import os

    user_path = get_env_path(winreg.HKEY_CURRENT_USER, r"Environment")
    system_path = get_env_path(
        winreg.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"
    )

    if expandvars:
        do_expandvars = os.path.expandvars
    else:
        def do_expandvars(input: str) -> str:
            return input

    user_list = [do_expandvars(p) for p in user_path.split(";") if p]
    system_list = [do_expandvars(p) for p in system_path.split(";") if p]

    return system_list + user_list


def split_path(dirs: typing.List[str]) -> typing.Dict:
    """
    Split a list of directories into two groups:
    - Prepend paths (e.g., directories containing python.exe or pip.exe)
    - Append paths (all others except WindowsApps)

    Parameters
    ----------
    dirs : typing.List[str]
        typing.List of directories to categorize.

    Returns
    -------
    typing.Dict
        A dict containing (prepend_dirs, append_dirs, vscode_dir).
    """
    import os

    output_dict: typing.Dict = {}
    prepend_dirs: typing.List[str] = []
    append_dirs: typing.List[str] = []
    vscode_dir: str = None

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata is not None:
        windowsapps_path = os.path.join(localappdata, "Microsoft\\WindowsApps")
    else:
        windowsapps_path = None

    for d in dirs:
        if windowsapps_path is not None and os.path.exists(d) and os.path.samefile(windowsapps_path, d):
            continue

        if "Microsoft VS Code\\bin" in d:
            vscode_dir = d
            continue

        if os.path.isfile(os.path.join(d, "ssh.exe")):
            prepend_dirs.append(d)
            continue

        if os.path.isfile(os.path.join(d, "python.exe")):
            prepend_dirs.append(d)
            continue

        if os.path.isfile(os.path.join(d, "pip.exe")):
            prepend_dirs.append(d)
            continue

        append_dirs.append(d)

    return {
        "prepend": prepend_dirs,
        "append": append_dirs,
        "vscode": vscode_dir
    }


def cygpath(path_list: typing.List[str], win_to_msys = True) -> typing.List[str]:
    """
    Convert Windows paths to MSYS2-style paths using cygpath.

    Parameters
    ----------
    path_list : typing.List[str]
        A list of Windows paths (e.g., ["C:\\foo\\bar"]).

    Returns
    -------
    typing.List[str]
        A list of MSYS2-style paths (e.g., ['/c/foo/bar']).

    Raises
    ------
    RuntimeError
        If cygpath fails.
    """
    if not isinstance(path_list, list):
        raise Exception(f"{path_list=} is not list")
    if win_to_msys:
        cmd = tuple(("c:\\msys64\\usr\\bin\\cygpath.exe", "-ua", *path_list))
    else:
        cmd = tuple(("c:\\msys64\\usr\\bin\\cygpath.exe", "-wa", *path_list))

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
    """
    Retrieve the HOME directory path using MSYS2 bash.

    Returns
    -------
    str
        The HOME directory as a str.
    """
    home = subprocess.check_output(
        ["C:\\msys64\\usr\\bin\\printenv.exe", "HOME"],
        text=True
    ).strip()
    return home


def ensure_bashrc_config(config_str: str, config_file: str = ".bashrc_winpath"):
    """
    Ensure that a configuration string is appended to a config file,
    and that the config file is sourced in ~/.bashrc. Idempotent.

    Parameters
    ----------
    config_str : str
        Configuration string (possibly multi-line) to append.
    config_file : str, optional
        Config file name under $HOME (default: ".bashrc_winpath").
    """
    import os
    import sys
    home_path = get_home()
    home_win = cygpath([home_path], win_to_msys=False)[0]
    config_path_win = os.path.join(home_win, config_file)
    bashrc_path_win = os.path.join(home_win, ".bashrc")
    sys.stderr.write(f"debug: {config_path_win=}\n")
    sys.stderr.write(f"debug: {bashrc_path_win=}\n")
    
    with open(config_path_win, "wt", encoding="utf-8") as f:
        f.write(config_str)

    import shlex
    source_line = "source \"${HOME}/\"" + shlex.quote(config_file)
    bashrc_content = ""
    if os.path.exists(bashrc_path_win):
        with open(bashrc_path_win, "rt", encoding="utf-8") as fp:
            bashrc_content = fp.read()
        # bashrc_content = bashrc_path.read_text(encoding="utf-8")

    if source_line not in bashrc_content:
        with open(bashrc_path_win, "at", encoding="utf-8") as f:
            if not bashrc_content.endswith("\n") and bashrc_content:
                f.write("\n")
            f.write(source_line + "\n")


if __name__ == "__main__":
    import sys
    from json.encoder import encode_basestring as double_quote

    path_list = get_combined_path_list()
    sys.stderr.write("# path list ====\n")
    for path in path_list:
        sys.stderr.write(path + "\n")

    split_dict = split_path(path_list)
    prepend_dirs = split_dict["prepend"]
    append_dirs = split_dict["append"]
    vscode_dir = split_dict.get("vscode")

    sys.stderr.write("# split path ====\n")
    sys.stderr.write("## prepend path\n")
    for path in prepend_dirs:
        sys.stderr.write(path + "\n")
    sys.stderr.write("## append path\n")
    for path in append_dirs:
        sys.stderr.write(path + "\n")
    if vscode_dir is not None:
        sys.stderr.write("## vscode\n")
        sys.stderr.write(vscode_dir + "\n")

    prepend_dirs_msys = cygpath(prepend_dirs)
    append_dirs_msys = cygpath(append_dirs)
    sys.stderr.write("# msys path ====\n")
    sys.stderr.write("## prepend path\n")
    for path in prepend_dirs_msys:
        sys.stderr.write(path + "\n")
    sys.stderr.write("## append path\n")
    for path in append_dirs_msys:
        sys.stderr.write(path + "\n")

    # --- PATH文字列をまとめて生成 ---
    sys.stderr.write("# msys path join ====\n")
    config_str = (
        "PATH=" + double_quote(":".join(prepend_dirs_msys) + ":$PATH") + "\n" +
        "PATH=" + double_quote("$PATH:" + ":".join(append_dirs_msys)) + "\n"
    )

    if vscode_dir is not None:
        import pathlib
        config_str += """\
function code() {
    local VSCODE_PATH=""" + double_quote(cygpath([str(pathlib.Path(vscode_dir).parent)])[0]) + """
    VSCODE_DEV= \\
    ELECTRON_RUN_AS_NODE=1 \\
    "${VSCODE_PATH}/Code.exe" \\
    "$(cygpath -w "${VSCODE_PATH}/resources/app/out/cli.js")" \\
    "$@"
}
"""
    config_str += "export RSYNC_RSH=/usr/bin/ssh\n"

    # ログ出力
    sys.stderr.write(config_str)

    # bashrc に書き込み（冪等）
    ensure_bashrc_config(config_str)
