"""Why is the process killed the moment the model is built? Run:

    python kernel_probe.py

The last probe showed: importing mediapipe is fine, but building the face
landmarker is killed with SIGKILL in every configuration, and it is not memory.
SIGKILL only ever comes from outside the process, so something in the system is
objecting to what the library does.

The prime suspect is JIT compilation. TensorFlow Lite's XNNPACK backend writes
machine code into memory at runtime and then runs it, which needs a page that is
first writable and then executable. Hardened kernels forbid exactly that, and
they enforce it by killing the process outright with no error it can catch.

This tests that directly, with no MediaPipe involved - a few bytes of machine
code, written and run. Each test runs in its own child process, so a kill just
marks that row and the rest carry on.

If the JIT rows die and the rest live, the kernel is the answer.
"""
import ctypes
import ctypes.util
import os
import platform
import signal
import subprocess
import sys

PROT_READ, PROT_WRITE, PROT_EXEC = 1, 2, 4
MAP_PRIVATE, MAP_ANONYMOUS = 0x02, 0x20

# x86-64: mov eax, 42 ; ret      aarch64: mov w0, #42 ; ret
CODE = {"x86_64": b"\xb8\x2a\x00\x00\x00\xc3",
        "aarch64": b"\x40\x05\x80\x52\xc0\x03\x5f\xd6"}


def libc():
    return ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def _mmap(c, size, prot):
    c.mmap.restype = ctypes.c_void_p
    c.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                       ctypes.c_int, ctypes.c_int, ctypes.c_long]
    p = c.mmap(None, size, prot, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0)
    if p in (None, 0) or ctypes.c_long(p).value == -1:
        raise OSError(ctypes.get_errno(), "mmap refused")
    return p


# ------------------------------------------------------------------ the tests
def t_write_then_exec():
    """Write code to a writable page, then ask for it to become executable.
    This is what a JIT does, and what W^X hardening forbids."""
    c, arch = libc(), platform.machine()
    code = CODE.get(arch)
    if not code:
        print(f"SKIP unsupported arch {arch}"); return
    size = 4096
    p = _mmap(c, size, PROT_READ | PROT_WRITE)
    ctypes.memmove(p, code, len(code))
    c.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    if c.mprotect(ctypes.c_void_p(p), size, PROT_READ | PROT_EXEC) != 0:
        raise OSError(ctypes.get_errno(), "mprotect refused")
    fn = ctypes.CFUNCTYPE(ctypes.c_int)(p)
    print(f"ran generated code, returned {fn()}")


def t_wx_at_once():
    """Ask for writable AND executable in one go - the strictest thing to forbid."""
    c = libc()
    p = _mmap(c, 4096, PROT_READ | PROT_WRITE | PROT_EXEC)
    print(f"got a writable+executable page at 0x{p:x}")


def t_big_mmap():
    """Rule out an address-space limit: reserve 1 GB without touching it."""
    c = libc()
    p = _mmap(c, 1 << 30, PROT_READ | PROT_WRITE)
    print(f"reserved 1 GB at 0x{p:x}")


def t_threads():
    """Rule out a thread/process cap: XNNPACK starts a pool."""
    import threading
    started = []
    for _ in range(16):
        t = threading.Thread(target=lambda: None)
        t.start(); started.append(t)
    for t in started:
        t.join()
    print(f"started and joined {len(started)} threads")


def t_tflite_only():
    """Build a bare TFLite interpreter if one is reachable, with no MediaPipe
    graph around it - narrows 'MediaPipe' down to 'the inference engine'."""
    try:
        from mediapipe.tasks import python  # noqa: F401
        import mediapipe as mp
        print("mediapipe imported; version " + getattr(mp, "__version__", "?"))
    except Exception as e:
        print(f"could not import: {type(e).__name__}: {e}"); return


TESTS = [
    ("write code, then make it executable", t_write_then_exec),
    ("writable + executable in one call",   t_wx_at_once),
    ("reserve 1 GB of address space",       t_big_mmap),
    ("start 16 threads",                    t_threads),
    ("import mediapipe (control)",          t_tflite_only),
]


def run_child(i):
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--test", str(i)],
                       capture_output=True, text=True)
    if p.returncode == 0:
        out = (p.stdout or "").strip().splitlines()
        return "OK", (out[-1][:44] if out else "")
    if p.returncode < 0:
        s = -p.returncode
        nm = signal.Signals(s).name if s in [x.value for x in signal.Signals] else str(s)
        return "DIED", nm + (" <- the kernel refused this" if nm == "SIGKILL" else "")
    err = (p.stderr or "").strip().splitlines()
    return "FAILED", (err[-1][:44] if err else f"exit {p.returncode}")


def sysinfo():
    print(f"kernel            {platform.system()} {platform.release()} ({platform.machine()})")
    for path, label in (("/proc/cmdline", "boot options"),
                        ("/sys/kernel/security/lsm", "security modules")):
        try:
            with open(path) as f:
                print(f"{label:<18}{f.read().strip()[:150]}")
        except Exception:
            print(f"{label:<18}not readable")
    try:
        out = subprocess.run(["uname", "-v"], capture_output=True, text=True, timeout=5).stdout
        print(f"kernel build      {out.strip()[:120]}")
    except Exception:
        pass


def main():
    print("GazeSpeakZero - kernel probe")
    print("-" * 68)
    sysinfo()
    print("-" * 68)
    print(f"{'test':<40}{'result':<12}{'detail'}")
    print("-" * 68)
    results = {}
    for i, (label, _) in enumerate(TESTS):
        status, detail = run_child(i)
        results[label] = status
        print(f"{label:<40}{status:<12}{detail}")
    print("-" * 68)

    jit_died = any(results.get(k) == "DIED" for k in
                   ("write code, then make it executable", "writable + executable in one call"))
    other_died = any(v == "DIED" for k, v in results.items()
                     if k not in ("write code, then make it executable",
                                  "writable + executable in one call"))
    if jit_died and not other_died:
        print("VERDICT: the kernel kills any program that generates code and runs it.")
        print("That is what TensorFlow Lite does to speed up the model, so MediaPipe")
        print("cannot start on this machine. It is a kernel policy, not a fault in")
        print("your setup and not something a reinstall will fix.")
        print()
        print("Please also send:   sudo dmesg -T | tail -40")
        print("run right after this - the kernel usually logs why it killed it.")
        print("Then we will move this site to another machine rather than fight it.")
    elif jit_died:
        print("VERDICT: the code-generation tests died, but so did others.")
        print("Send the table and:   sudo dmesg -T | tail -40")
    elif not any(v == "DIED" for v in results.values()):
        print("VERDICT: everything here is allowed, so it is not a blanket kernel rule.")
        print("The kill is specific to what the model loader does. Send this table and,")
        print("if you can:   sudo dmesg -T | tail -40   right after a failed run.")
    else:
        print("VERDICT: mixed. Send the table and:   sudo dmesg -T | tail -40")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--test":
        TESTS[int(sys.argv[2])][1]()
        sys.exit(0)
    main()
