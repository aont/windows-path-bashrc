from typing import Optional, List, Tuple


def get_env_path(root: int, path: str) -> Optional[str]:
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
    Optional[str]
        The value of the 'Path' variable if found, otherwise None.
    """
    import winreg
    import sys

    try:
        with winreg.OpenKey(root, path) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return value
    except FileNotFoundError:
        sys.stderr.write(f"get_env_path: Path not found: {root=} {path=}\n")
    except FileNotFoundError:
        sys.stderr.write(f"get_env_path: Path value not found: {root=} {path=}\n")
    return None


def get_combined_path_list(expandvars: bool = True) -> List[str]:
    """
    Retrieve and combine user and system PATH variables into a single list.

    Parameters
    ----------
    expandvars : bool, optional
        If True, expand environment variables (default is True).

    Returns
    -------
    List[str]
        Combined list of system and user paths.
    """
    import winreg
    import os

    # User environment variable
    user_path = get_env_path(
        winreg.HKEY_CURRENT_USER,
        r"Environment"
    )

    # System environment variable
    system_path = get_env_path(
        winreg.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"
    )

    # Split by ";" into a list (excluding empty elements)
    if expandvars:
        do_expandvars = os.path.expandvars
    else:
        def do_expandvars(input: str) -> str:
            return input

    user_list = [do_expandvars(p) for p in user_path.split(";") if p]
    system_list = [do_expandvars(p) for p in system_path.split(";") if p]

    # Combine lists (system first, then user)
    combined_list = system_list + user_list

    return combined_list


def split_path(dirs: List[str]) -> Tuple[List[str], List[str]]:
    """
    Split a list of directories into two groups:
    - Prepend paths (e.g., directories containing python.exe or pip.exe)
    - Append paths (all others except WindowsApps)

    Parameters
    ----------
    dirs : List[str]
        List of directories to categorize.

    Returns
    -------
    Tuple[List[str], List[str]]
        A tuple containing (prepend_dirs, append_dirs).
    """
    import os

    prepend_dirs: List[str] = []
    append_dirs: List[str] = []

    windowsapps_path = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft\\WindowsApps")

    for d in dirs:
        if os.path.exists(d) and os.path.samefile(windowsapps_path, d):
            # Skip WindowsApps
            continue

        if os.path.isfile(os.path.join(d, "python.exe")):
            prepend_dirs.append(d)
            continue

        if os.path.isfile(os.path.join(d, "pip.exe")):
            prepend_dirs.append(d)
            continue

        append_dirs.append(d)

    return prepend_dirs, append_dirs


def win_to_msys(path_list: List[str]) -> List[str]:
    """
    Convert Windows paths to MSYS2-style paths using cygpath.

    Parameters
    ----------
    path_list : List[str]
        A list of Windows paths (e.g., ["C:\\foo\\bar"]).

    Returns
    -------
    List[str]
        A list of MSYS2-style paths (e.g., ['/c/foo/bar']).

    Raises
    ------
    RuntimeError
        If cygpath fails.
    """
    import subprocess

    cmd = tuple(("c:\\msys64\\usr\\bin\\cygpath.exe", "-u", *path_list))

    # Execute cygpath and capture output
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"cygpath failed: {result.stderr}")

    return result.stdout.splitlines()


if __name__ == "__main__":
    import sys

    path_list = get_combined_path_list()
    sys.stderr.write("# path list ====\n")
    for path in path_list:
        sys.stderr.write(path + "\n")

    prepend_dirs, append_dirs = split_path(path_list)
    sys.stderr.write("# split path ====\n")
    sys.stderr.write("## prepend path\n")
    for path in prepend_dirs:
        sys.stderr.write(path + "\n")
    sys.stderr.write("## append path\n")
    for path in append_dirs:
        sys.stderr.write(path + "\n")

    prepend_dirs_msys = win_to_msys(prepend_dirs)
    append_dirs_msys = win_to_msys(append_dirs)
    sys.stderr.write("# msys path ====\n")
    sys.stderr.write("## prepend path\n")
    for path in prepend_dirs_msys:
        sys.stderr.write(path + "\n")
    sys.stderr.write("## append path\n")
    for path in append_dirs_msys:
        sys.stderr.write(path + "\n")

    sys.stderr.write("# msys path join ====\n")
    from json.encoder import encode_basestring as double_quote
    sys.stderr.write("PATH=" + double_quote(":".join(prepend_dirs_msys) + ":$PATH") + "\n")
    sys.stderr.write("PATH=" + double_quote("$PATH:" + ":".join(append_dirs_msys)) + "\n")
