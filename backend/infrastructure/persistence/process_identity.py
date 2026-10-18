"""PID reuseを区別するOS開始識別子。時刻期限で生存ownerを追放しない。"""

import ctypes
import sys
from pathlib import Path


def process_identity(pid: int) -> str | None:
    if sys.platform != "win32":
        if not sys.platform.startswith("linux"):
            return _posix_process_identity(pid)
        try:
            fields = (
                (Path("/proc") / str(pid) / "stat")
                .read_text()
                .rsplit(")", 1)[1]
                .split()
            )
        except FileNotFoundError:
            return None
        return None if fields[0] == "Z" else fields[19]
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return None
        raise OSError(error, "Owner process identity cannot be established")
    kernel.GetProcessTimes.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    )
    kernel.GetExitCodeProcess.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    try:
        exit_code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise OSError(ctypes.get_last_error(), "Owner process status unavailable")
        if exit_code.value != 259:
            return None
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(
            handle, *(ctypes.byref(value) for value in times)
        ):
            raise OSError(ctypes.get_last_error(), "Owner process start unavailable")
        return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
    finally:
        kernel.CloseHandle(handle)


def _posix_process_identity(pid: int) -> str | None:
    """Use the native process API on POSIX hosts without Linux procfs."""
    import psutil

    try:
        process = psutil.Process(pid)
        if process.status() in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
            return None
        return f"posix:{process.create_time()}"
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied as error:
        raise OSError("Owner process identity cannot be established") from error
