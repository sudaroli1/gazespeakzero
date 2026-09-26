"""Why is the process being killed? Run:  python mediapipe_probe.py

The previous check died inside MediaPipe's face-landmarker construction on a
machine with 8 GB free. So this asks two questions the last one could not:

1. WHO killed it. Linux keeps a per-cgroup counter of out-of-memory kills that
   the owning user can read without sudo (`memory.events`). If that counter goes
   up when the child dies, a memory CAP killed it - which is different from the
   machine running out of memory, and is invisible in the logs a normal user can
   read. If the counter does not move, memory was not the cause at all.

2. WHICH SETTING triggers it. Each configuration runs in its own child process,
   so one death no longer ends the test. The first configuration that dies names
   the feature responsible.

Send back everything this prints.
"""
import os
import resource
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

def require_files(*names):
    """Stop with a plain message if the model files are not beside this script.

    Without this the probe would run its whole table against a missing model and
    report every row as DIED - which reads exactly like the bug reproducing. A
    diagnostic that can manufacture its own false evidence is worse than none.
    """
    missing = [n for n in names if not os.path.exists(os.path.join(HERE, n))]
    if missing:
        print("This script needs these files beside it, and they are not here:")
        for n in missing:
            print("   " + n)
        print()
        print("You are probably running it from a folder that holds only the scripts.")
        print("Unzip gazespeakzero_full_package.zip somewhere fresh, then run this from")
        print("inside its `prototype` folder - everything lives there together.")
        raise SystemExit(2)


LANDMARKER = os.path.join(HERE, "face_landmarker.task")


# ----------------------------------------------------------------- cgroup facts
def cgroup_dir():
    """The cgroup v2 directory for this process, or None."""
    try:
        with open("/proc/self/cgroup") as f:
            for line in f:
                parts = line.strip().split(":", 2)
                if parts[0] == "0":                       # cgroup v2 line
                    return os.path.join("/sys/fs/cgroup", parts[2].lstrip("/"))
    except Exception:
        pass
    return None


def cg_read(name, d=None):
    d = d or cgroup_dir()
    if not d:
        return None
    try:
        with open(os.path.join(d, name)) as f:
            return f.read().strip()
    except Exception:
        return None


def oom_kill_count():
    """How many times this cgroup has had something OOM-killed."""
    txt = cg_read("memory.events") or ""
    for line in txt.splitlines():
        k, _, v = line.partition(" ")
        if k == "oom_kill":
            try:
                return int(v)
            except ValueError:
                return None
    return None


def human(v):
    if v in (None, "max", ""):
        return v or "?"
    try:
        return f"{int(v) / 1048576:.0f} MB"
    except ValueError:
        return v


# ----------------------------------------------------------------- the variants
def build(mode, blendshapes, matrices, threads=None, preload=()):
    """Construct a FaceLandmarker with the given options. Runs in a CHILD process.

    `preload` reproduces the real program's import order. This matters: OpenCV and
    MediaPipe each bundle their own copies of the same native libraries, so
    importing one before the other is not always the same as importing it alone.
    The real run imports cv2 first; the plain variants here do not.
    """
    for mod in preload:
        if mod == "model":
            import joblib
            joblib.load(os.path.join(HERE, "gaze_model.joblib"))
        else:
            __import__(mod)
    if threads:
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MEDIAPIPE_NUM_THREADS"] = str(threads)
    import mediapipe as mp
    rm = getattr(mp.tasks.vision.RunningMode, mode)
    base = mp.tasks.BaseOptions(model_asset_path=LANDMARKER)
    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=base, running_mode=rm,
        output_face_blendshapes=blendshapes,
        output_facial_transformation_matrixes=matrices, num_faces=1)
    lm = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
    rss = 0
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss = int(line.split()[1]) // 1024
    except Exception:
        pass
    print(f"RSS_MB={rss}")
    del lm


VARIANTS = [
    ("import mediapipe only",                    None),
    ("IMAGE  mode, no blendshapes",              ("IMAGE", False, False, None)),
    ("VIDEO  mode, no blendshapes",              ("VIDEO", False, False, None)),
    ("VIDEO  mode, blendshapes",                 ("VIDEO", True,  False, None)),
    ("VIDEO  mode, blendshapes + matrices",      ("VIDEO", True,  True,  None)),  # production
    ("production config, 1 thread",              ("VIDEO", True,  True,  1)),
    ("production config, 2 threads",             ("VIDEO", True,  True,  2)),
    # These reproduce the real program's import order, which the rows above do not.
    ("after importing cv2",                      ("VIDEO", True,  True,  None, ("cv2",))),
    ("after cv2 + gaze model (real order)",      ("VIDEO", True,  True,  None, ("cv2", "model"))),
]


def run_child(idx):
    """Run one variant in a fresh interpreter. Returns (ok, detail, rss)."""
    cmd = [sys.executable, os.path.abspath(__file__), "--variant", str(idx)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    rss = ""
    for line in (p.stdout or "").splitlines():
        if line.startswith("RSS_MB="):
            rss = line.split("=", 1)[1] + " MB"
    if p.returncode == 0:
        return True, "ok", rss
    if p.returncode < 0:
        sig = -p.returncode
        name = signal.Signals(sig).name if sig in [s.value for s in signal.Signals] else str(sig)
        meaning = {"SIGKILL": "killed from outside (memory cap, OOM killer, or security software)",
                   "SIGSEGV": "segfault - a real bug or a broken build",
                   "SIGABRT": "the library aborted (often a failed allocation it caught itself)",
                   "SIGILL":  "illegal instruction - the build needs CPU features this machine lacks"
                   }.get(name, "")
        return False, f"{name} - {meaning}" if meaning else name, rss
    tail = (p.stderr or "").strip().splitlines()
    return False, f"exit {p.returncode}: {tail[-1][:110] if tail else 'no message'}", rss


def main():
    require_files("face_landmarker.task", "gaze_model.joblib")
    print("GazeSpeakZero - MediaPipe probe")
    print("-" * 74)
    d = cgroup_dir()
    print(f"cgroup        {d or 'not cgroup v2'}")
    if d:
        print(f"  memory.max   {human(cg_read('memory.max', d))}      <- a number here is a CAP")
        print(f"  memory.high  {human(cg_read('memory.high', d))}")
        print(f"  memory.peak  {human(cg_read('memory.peak', d))}")
        ev = cg_read('memory.events', d)
        print(f"  events       {(ev or 'NOT READABLE').replace(chr(10), ' | ')}")
        if not ev:
            print("               ^ without this a memory cap cannot be confirmed or ruled out")
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    print(f"ulimit -v     {'unlimited' if soft == resource.RLIM_INFINITY else human(soft)}")
    soft_d, _ = resource.getrlimit(resource.RLIMIT_DATA)
    print(f"ulimit -d     {'unlimited' if soft_d == resource.RLIM_INFINITY else human(soft_d)}")
    print("-" * 74)
    print(f"{'configuration':<40}{'result':<26}{'RSS':>8}")
    print("-" * 74)

    before = oom_kill_count()
    counter_readable = before is not None
    killed_by_cgroup = False
    first_failure = None
    for i, (label, _) in enumerate(VARIANTS):
        ok, detail, rss = run_child(i)
        after = oom_kill_count()
        tag = "OK" if ok else "DIED"
        if not ok and counter_readable and after is not None and after > before:
            detail = "cgroup OOM kill (counter moved)"
            killed_by_cgroup = True
        before = after if after is not None else before
        if not ok and first_failure is None:
            first_failure = label
        print(f"{label:<40}{tag + '  ' + detail:<26}{rss:>8}")

    print("-" * 74)
    if first_failure is None:
        print("VERDICT: every configuration built successfully.")
        print("Whatever killed the real run is not the landmarker itself. Tell Sudaroli.")
    elif killed_by_cgroup:
        print("VERDICT: a MEMORY CAP on your session killed it - not the machine running out.")
        print("The cgroup's own out-of-memory counter went up. Look at memory.max above.")
        print("This is a setting on the session, so a plain reboot or closing apps will not")
        print("help. Running the session from a plain TTY or a different terminal often does.")
    else:
        print(f"VERDICT: the first configuration to die was: {first_failure}")
        if counter_readable:
            # Only claim this when the counter was actually readable. An unreadable
            # counter is not evidence of anything - saying otherwise is how the last
            # round of this went wrong.
            print("The cgroup out-of-memory counter was readable and did NOT move, so a")
            print("memory cap is ruled out. Something else sent the kill.")
        else:
            print("The cgroup out-of-memory counter could NOT be read on this machine, so a")
            print("memory cap is NOT ruled out - there is simply no evidence either way.")
            print("If you can, run this too and send the result:")
            print("   sudo dmesg -T | grep -i -e 'out of memory' -e 'killed process' | tail")
        print("Send this table to Sudaroli - the surviving rows say what still works.")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--variant":
        spec = VARIANTS[int(sys.argv[2])][1]
        if spec is None:
            import mediapipe  # noqa: F401
        else:
            build(*spec)
        sys.exit(0)
    main()
