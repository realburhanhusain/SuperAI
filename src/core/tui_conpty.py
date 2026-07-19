"""
Windows ConPTY (pseudo-console) backend for process panes.

Uses kernel32 CreatePseudoConsole + CreateProcessW with
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE — no pywinpty dependency.

Falls back gracefully when ConPTY is unavailable (older Windows).
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
from collections import deque
from ctypes import wintypes
from typing import Any, Deque, Dict, List, Optional, Tuple


if sys.platform != "win32":
    def conpty_supported() -> bool:
        return False

    def spawn_conpty(*_a, **_k):
        raise RuntimeError("ConPTY is Windows-only")

else:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    HPCON = ctypes.c_void_p
    SSIZE_T = ctypes.c_ssize_t

    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    class STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [
            ("StartupInfo", STARTUPINFOW),
            ("lpAttributeList", ctypes.c_void_p),
        ]

    # constants
    EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    HANDLE_FLAG_INHERIT = 0x00000001

    CreatePipe = kernel32.CreatePipe
    CreatePipe.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    CreatePipe.restype = wintypes.BOOL

    SetHandleInformation = kernel32.SetHandleInformation
    SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    SetHandleInformation.restype = wintypes.BOOL

    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL

    # ConPTY APIs (Windows 10 1809+)
    try:
        CreatePseudoConsole = kernel32.CreatePseudoConsole
        CreatePseudoConsole.argtypes = [
            COORD,  # size
            wintypes.HANDLE,  # input (read end for conpty)
            wintypes.HANDLE,  # output (write end for conpty)
            wintypes.DWORD,  # flags
            ctypes.POINTER(HPCON),
        ]
        CreatePseudoConsole.restype = wintypes.HRESULT

        ClosePseudoConsole = kernel32.ClosePseudoConsole
        ClosePseudoConsole.argtypes = [HPCON]
        ClosePseudoConsole.restype = None

        ResizePseudoConsole = kernel32.ResizePseudoConsole
        ResizePseudoConsole.argtypes = [HPCON, COORD]
        ResizePseudoConsole.restype = wintypes.HRESULT

        _HAS_CONPTY = True
    except AttributeError:
        _HAS_CONPTY = False

    InitializeProcThreadAttributeList = kernel32.InitializeProcThreadAttributeList
    InitializeProcThreadAttributeList.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    InitializeProcThreadAttributeList.restype = wintypes.BOOL

    UpdateProcThreadAttribute = kernel32.UpdateProcThreadAttribute
    UpdateProcThreadAttribute.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,  # attribute as DWORD_PTR
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    UpdateProcThreadAttribute.restype = wintypes.BOOL

    DeleteProcThreadAttributeList = kernel32.DeleteProcThreadAttributeList
    DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    DeleteProcThreadAttributeList.restype = None

    CreateProcessW = kernel32.CreateProcessW
    CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOEXW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    CreateProcessW.restype = wintypes.BOOL

    ReadFile = kernel32.ReadFile
    ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    ReadFile.restype = wintypes.BOOL

    WriteFile = kernel32.WriteFile
    WriteFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    WriteFile.restype = wintypes.BOOL

    GetExitCodeProcess = kernel32.GetExitCodeProcess
    GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    GetExitCodeProcess.restype = wintypes.BOOL

    TerminateProcess = kernel32.TerminateProcess
    TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    TerminateProcess.restype = wintypes.BOOL

    STILL_ACTIVE = 259

    def conpty_supported() -> bool:
        return bool(_HAS_CONPTY)

    def _err() -> str:
        return f"winerr={ctypes.get_last_error()}"

    class ConPTYSession:
        """
        Running ConPTY session with host-side read/write handles.
        """

        def __init__(self):
            self.hpc: Optional[int] = None
            self.h_input_write: Optional[int] = None  # host → conpty
            self.h_output_read: Optional[int] = None  # conpty → host
            self.h_process: Optional[int] = None
            self.h_thread: Optional[int] = None
            self.pid: Optional[int] = None
            self._attr_list = None
            self._attr_buf = None
            self._closed = False
            self._buf: Deque[str] = deque(maxlen=5000)
            self._lock = threading.Lock()
            self._stop = threading.Event()
            self._reader: Optional[threading.Thread] = None

        def start(
            self,
            command: List[str],
            *,
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            cols: int = 120,
            rows: int = 40,
        ) -> Dict[str, Any]:
            if not _HAS_CONPTY:
                return {"ok": False, "error": "conpty_api_missing"}
            if not command:
                return {"ok": False, "error": "empty_command"}

            # Pipes: inputPipe — host writes, ConPTY reads
            input_read = wintypes.HANDLE()
            input_write = wintypes.HANDLE()
            output_read = wintypes.HANDLE()
            output_write = wintypes.HANDLE()
            if not CreatePipe(ctypes.byref(input_read), ctypes.byref(input_write), None, 0):
                return {"ok": False, "error": f"CreatePipe input {_err()}"}
            if not CreatePipe(ctypes.byref(output_read), ctypes.byref(output_write), None, 0):
                return {"ok": False, "error": f"CreatePipe output {_err()}"}

            # Don't inherit host ends
            SetHandleInformation(input_write, HANDLE_FLAG_INHERIT, 0)
            SetHandleInformation(output_read, HANDLE_FLAG_INHERIT, 0)

            hpc = HPCON()
            size = COORD(cols, rows)
            hr = CreatePseudoConsole(size, input_read, output_write, 0, ctypes.byref(hpc))
            # ConPTY duplicates the handles it needs; close our copies of those ends
            CloseHandle(input_read)
            CloseHandle(output_write)
            if hr != 0:
                CloseHandle(input_write)
                CloseHandle(output_read)
                return {"ok": False, "error": f"CreatePseudoConsole hr={hr}"}

            self.hpc = hpc.value
            self.h_input_write = input_write.value
            self.h_output_read = output_read.value

            # Attribute list for PSEUDOCONSOLE
            size_attr = ctypes.c_size_t(0)
            InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size_attr))
            self._attr_buf = (ctypes.c_byte * size_attr.value)()
            attr_list = ctypes.cast(self._attr_buf, ctypes.c_void_p)
            if not InitializeProcThreadAttributeList(attr_list, 1, 0, ctypes.byref(size_attr)):
                self.close()
                return {"ok": False, "error": f"InitializeProcThreadAttributeList {_err()}"}
            self._attr_list = attr_list

            if not UpdateProcThreadAttribute(
                attr_list,
                0,
                PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                hpc,
                ctypes.sizeof(HPCON),
                None,
                None,
            ):
                self.close()
                return {"ok": False, "error": f"UpdateProcThreadAttribute {_err()}"}

            siex = STARTUPINFOEXW()
            ctypes.memset(ctypes.byref(siex), 0, ctypes.sizeof(siex))
            siex.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            siex.lpAttributeList = attr_list

            # Command line
            if len(command) == 1:
                cmdline = command[0]
            else:
                # quote args with spaces
                parts = []
                for a in command:
                    if " " in a and not a.startswith('"'):
                        parts.append(f'"{a}"')
                    else:
                        parts.append(a)
                cmdline = " ".join(parts)
            cmd_buf = ctypes.create_unicode_buffer(cmdline)

            # Environment block (optional)
            env_block = None
            if env is not None:
                # merge with current
                merged = os.environ.copy()
                merged.update({str(k): str(v) for k, v in env.items()})
                # UTF-16 null-separated
                block = "\0".join(f"{k}={v}" for k, v in merged.items()) + "\0\0"
                env_block = ctypes.create_unicode_buffer(block)

            pi = PROCESS_INFORMATION()
            cwd_w = cwd if cwd else None
            flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT
            ok = CreateProcessW(
                None,
                cmd_buf,
                None,
                None,
                False,
                flags,
                env_block,
                cwd_w,
                ctypes.byref(siex),
                ctypes.byref(pi),
            )
            if not ok:
                self.close()
                return {"ok": False, "error": f"CreateProcessW {_err()} cmdline={cmdline[:80]}"}

            self.h_process = pi.hProcess
            self.h_thread = pi.hThread
            self.pid = int(pi.dwProcessId)

            self._stop.clear()
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()
            return {
                "ok": True,
                "backend": "conpty",
                "pid": self.pid,
                "command": command,
            }

        def _read_loop(self) -> None:
            buf = ctypes.create_string_buffer(4096)
            nread = wintypes.DWORD(0)
            while not self._stop.is_set() and self.h_output_read:
                ok = ReadFile(
                    self.h_output_read,
                    buf,
                    4096,
                    ctypes.byref(nread),
                    None,
                )
                if not ok or nread.value == 0:
                    if not self.alive():
                        break
                    continue
                text = buf.raw[: nread.value].decode("utf-8", errors="replace")
                with self._lock:
                    for line in text.splitlines(keepends=True):
                        self._buf.append(line)

        def alive(self) -> bool:
            if not self.h_process:
                return False
            code = wintypes.DWORD(0)
            if not GetExitCodeProcess(self.h_process, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE

        def read_output(self, *, max_chars: int = 8000, clear: bool = False) -> str:
            with self._lock:
                data = "".join(self._buf)
                if clear:
                    self._buf.clear()
                return data[-max_chars:] if len(data) > max_chars else data

        def write(self, data: str) -> Dict[str, Any]:
            if not self.h_input_write or not self.alive():
                return {"ok": False, "error": "not_alive"}
            raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
            written = wintypes.DWORD(0)
            ok = WriteFile(
                self.h_input_write,
                raw,
                len(raw),
                ctypes.byref(written),
                None,
            )
            if not ok:
                return {"ok": False, "error": f"WriteFile {_err()}"}
            return {"ok": True, "bytes": int(written.value)}

        def kill(self) -> Dict[str, Any]:
            self._stop.set()
            code = None
            if self.h_process:
                if self.alive():
                    TerminateProcess(self.h_process, 1)
                c = wintypes.DWORD(0)
                GetExitCodeProcess(self.h_process, ctypes.byref(c))
                code = int(c.value)
            self.close()
            return {"ok": True, "killed": True, "exit_code": code, "backend": "conpty"}

        def close(self) -> None:
            if self._closed:
                return
            self._closed = True
            self._stop.set()
            if self.hpc:
                try:
                    ClosePseudoConsole(self.hpc)
                except Exception:
                    pass
                self.hpc = None
            if self._attr_list:
                try:
                    DeleteProcThreadAttributeList(self._attr_list)
                except Exception:
                    pass
                self._attr_list = None
            for h in (self.h_input_write, self.h_output_read, self.h_thread, self.h_process):
                if h:
                    try:
                        CloseHandle(h)
                    except Exception:
                        pass
            self.h_input_write = None
            self.h_output_read = None
            self.h_thread = None
            self.h_process = None

    def spawn_conpty(
        command: List[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        cols: int = 120,
        rows: int = 40,
    ) -> Tuple[Optional[ConPTYSession], Dict[str, Any]]:
        sess = ConPTYSession()
        res = sess.start(command, cwd=cwd, env=env, cols=cols, rows=rows)
        if not res.get("ok"):
            return None, res
        return sess, res


def conpty_status() -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    return ensure_public_result(
        {
            "ok": True,
            "platform": sys.platform,
            "supported": conpty_supported() if sys.platform == "win32" else False,
            "module": "core.tui_conpty",
        },
        ok=True,
    )
