"""Find out what the machine ran out of. Run:  python memcheck.py

A "Killed" message with no traceback means the operating system's out-of-memory
killer stopped the process. Python never sees it coming, so nothing useful is
printed at the moment of death - the only clue is the LAST line that made it out.

So this script loads the pipeline one piece at a time, printing memory after each
piece and flushing immediately. If it gets killed, the last line you see names the
step that would not fit. If it finishes, it prints a verdict.

Send back everything it prints, including the last partial line.
"""
import gc
import os
import platform
import sys


def _say(s=""):
    sys.stdout.write(s + "\n")
    sys.stdout.flush()          # so the line survives a SIGKILL on the next step


def rss_mb():
    """Resident memory of this process, in MB."""
    try:                         # Linux
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    try:                         # macOS / BSD
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / (1024.0 * 1024.0) if sys.platform == "darwin" else r / 1024.0
    except Exception:
        return float("nan")


def system_memory():
    """(total_mb, available_mb, swap_total_mb) - any may be None."""
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, v = line.partition(":")
                info[k] = int(v.split()[0]) / 1024.0
        return info.get("MemTotal"), info.get("MemAvailable"), info.get("SwapTotal")
    except Exception:
        pass
    try:
        import subprocess
        if sys.platform == "darwin":
            tot = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 1048576.0
            return tot, None, None
    except Exception:
        pass
    return None, None, None


def oom_evidence():
    """Ask the system whether it killed something recently. Direct proof beats inference.

    Two different things can send SIGKILL and they log in different places: the
    kernel OOM killer writes to the kernel ring buffer, while systemd-oomd (on
    recent Fedora/Ubuntu desktops) writes to the system journal and can kill under
    memory *pressure* even when some RAM is free. Both are checked.
    """
    import subprocess

    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout or ""
        except Exception:
            return ""

    kernel = run(["dmesg", "-T"]) or run(["dmesg"]) or run(["journalctl", "-k", "--no-pager", "-n", "500"])
    journal = run(["journalctl", "--no-pager", "-n", "500"])

    hits = []
    for line in kernel.splitlines():
        low = line.lower()
        if "out of memory" in low or "oom-kill" in low or "killed process" in low:
            hits.append("kernel : " + line[-140:])
    for line in journal.splitlines():
        if "oomd" in line.lower() and "kill" in line.lower():
            hits.append("oomd   : " + line[-140:])

    if hits:
        return ("SYSTEM LOG: something HAS been killed for memory recently -\n"
                + "\n".join("   " + h for h in hits[-4:]))
    if kernel or journal:
        return ("system log readable, no memory kill recorded in it.\n"
                "   If the run is killed anyway, suspect endpoint security / antivirus on a\n"
                "   managed laptop, or a memory cap on the container or WSL instance.")
    return ("system log not readable without sudo. If you can, run:\n"
            "   sudo dmesg -T | grep -i -e 'out of memory' -e 'killed process' | tail\n"
            "and send the result - it says outright whether memory was the cause.")


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


step = 0


def mark(label):
    global step
    step += 1
    _say(f"  [{step}] {label:<44} RSS {rss_mb():7.0f} MB")


def main():
    require_files("face_landmarker.task", "gaze_model.joblib")
    _say("GazeSpeakZero - memory check")
    _say("-" * 62)
    _say(f"python   {platform.python_version()} ({platform.machine()})")
    _say(f"system   {platform.system()} {platform.release()}")
    tot, avail, swap = system_memory()
    if tot:
        _say(f"RAM      {tot:.0f} MB total"
             + (f", {avail:.0f} MB available" if avail is not None else "")
             + (f", {swap:.0f} MB swap" if swap is not None else ""))
        if avail is not None and avail < 1200:
            _say("         ^ this is low. Close your browser and anything heavy, then re-run.")
        if swap is not None and swap == 0:
            _say("         ^ no swap: the OOM killer acts immediately when RAM runs out.")
    else:
        _say("RAM      could not read (not Linux?)")
    _say(oom_evidence())
    _say("-" * 62)
    _say("Loading the pipeline step by step. If this stops without a verdict,")
    _say("the last line below is the step that did not fit.")
    _say()

    mark("start")

    import numpy                                    # noqa: F401
    mark("numpy")

    import cv2
    mark(f"opencv {cv2.__version__}")

    import joblib
    model = joblib.load(os.path.join(HERE, "gaze_model.joblib"))
    n_feat = len(model.get("features", []))
    mark(f"gaze model ({n_feat} features)")

    import mediapipe as mp
    mark("mediapipe imported")

    base = mp.tasks.BaseOptions(model_asset_path=os.path.join(HERE, "face_landmarker.task"))
    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp.tasks.vision.RunningMode.VIDEO,
        output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1)
    mark("landmarker options")

    lm = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
    mark("FACE LANDMARKER BUILT")      # <- the step the reported log died on

    from camera import measure_fps, open_camera
    cap, info = open_camera(0, 1280, 720)
    mark(f"camera open {info['width']}x{info['height']} [{info['fourcc']}]")

    if not info["opened"]:
        _say("\nThe camera would not open, but memory was fine. Different problem - tell Sudaroli.")
        return

    fps = measure_fps(cap, seconds=2.0)
    mark(f"camera running at {fps:.1f} fps")

    peak = rss_mb()
    for i in range(30):
        ok, frame = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        lm.detect_for_video(img, i * 40)
        peak = max(peak, rss_mb())
    mark(f"30 frames processed (peak {peak:.0f} MB)")
    cap.release()
    gc.collect()

    _say()
    _say("-" * 62)
    _say(f"VERDICT: the whole pipeline ran and used about {peak:.0f} MB.")
    _say("For reference it uses ~245 MB on a healthy machine, so if this was")
    _say("killed for memory, the machine had almost nothing free at the time.")
    if tot and avail is not None and peak > avail:
        _say("It fit this time only because something else closed. Keep the browser shut.")
    if fps < 15:
        _say(f"Memory is fine, but the camera is still at {fps:.1f} fps (need 15+).")
        _say("Run  python camera_probe.py  and send that output too.")
    else:
        _say(f"Camera is at {fps:.1f} fps. Both checks pass - try the session again.")


if __name__ == "__main__":
    main()
