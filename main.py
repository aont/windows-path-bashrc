def get_env_path(root, path):
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


def get_combined_path_list(expandvars = True):
    import winreg
    import os

    # ユーザー環境変数
    user_path = get_env_path(
        winreg.HKEY_CURRENT_USER,
        r"Environment"
    )

    # システム環境変数
    system_path = get_env_path(
        winreg.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"
    )

    # ";" で分割してリスト化（空要素は除去）
    if expandvars:
        do_expandvars = os.path.expandvars
    else:
        def do_expandvars(input):
            return input

    user_list = [do_expandvars(p) for p in user_path.split(";") if p]
    system_list = [do_expandvars(p) for p in system_path.split(";") if p]

    # 結合
    combined_list = system_list + user_list

    return combined_list

def split_path(dirs: list[str]):
    import os

    prepend_dirs = []
    append_dirs = []

    windowsapps_path = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft\\WindowsApps")

    for d in dirs:

        if os.path.exists(d) and os.path.samefile(windowsapps_path, d):
            # append_dirs.append(d)
            continue
        
        if os.path.isfile(os.path.join(d, "python.exe")):
            prepend_dirs.append(d)
            continue
        
        if os.path.isfile(os.path.join(d, "pip.exe")):
            prepend_dirs.append(d)
            continue

        append_dirs.append(d)
        continue

    return prepend_dirs, append_dirs

def win_to_msys(path_list: list[str]) -> str:
    """
    Windows形式のパスを MSYS2 形式のパスに変換する。
    
    Parameters
    ----------
    path : str
        Windows形式のパス (例: 'C:\\foo\\bar')
    msys_bash : str
        MSYS2 の bash.exe のパス (デフォルト: c:\\msys64\\usr\\bin\\bash.exe)
    
    Returns
    -------
    str
        MSYS2 形式のパス (例: '/c/foo/bar')
    """

    import subprocess
    import shlex
    # import os

    cmd = tuple(("c:\\msys64\\usr\\bin\\cygpath", "-u", *path_list))
    # cmd = f'{msys_bash} --login -c {shlex.quote(shlex.join(("cygpath", "-u", path)))}'

    # env = os.environ.copy()
    # env = dict()
    # env["MSYSTEM"] = "MSYS"
    # env["PATH"] = r"C:\msys64\ucrt64\bin;C:\msys64\usr\local\bin;C:\msys64\usr\bin;C:\msys64\usr\bin;C:\msys64\usr\bin\site_perl;C:\msys64\usr\bin\vendor_perl;C:\msys64\usr\bin\core_perl"
    # env["PATH"] = r"C:\msys64\usr\local\bin;C:\msys64\usr\bin;C:\msys64\usr\bin"
    # env["PATH"] = r"C:\msys64\usr\bin"

    # 実行して標準出力を取得
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        # env=env
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"cygpath failed: {result.stderr}")
    
    # return result.stdout.strip()
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
    import shlex
    from json.encoder import encode_basestring as double_quote
    sys.stderr.write("PATH=" + double_quote(":".join(prepend_dirs_msys) + ":$PATH") + "\n")
    sys.stderr.write("PATH=" + double_quote("$PATH:" + ":".join(append_dirs_msys)) + "\n")
