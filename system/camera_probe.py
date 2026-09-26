"""Find out why the camera is slow. Run:  python camera_probe.py

Your camera is handing back uncompressed frames and every way of asking for
compressed ones may have been refused. This tries each combination of camera
backend and request order, MEASURES the frame rate each one actually delivers,
and prints the lot. Asking is not the same as getting, so nothing here is taken
on trust.

Send back the whole table.
"""
import sys

import cv2

from camera import (MIN_USABLE_FPS, _apply, _backends, _fourcc_str, _observe,
                    _strategies, diagnose_low_fps, measure_fps)


def main():
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print("GazeSpeakZero - camera probe")
    print(f"OpenCV {cv2.__version__}   camera index {index}")
    print("-" * 74)
    print(f"{'how we asked':<34}{'got':<12}{'format':<8}{'fps':>7}")
    print("-" * 74)

    rows = []
    for label, backend, order, mjpg, fps_hint in _strategies():
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            print(f"{label:<34}{'-':<12}{'-':<8}{'will not open':>7}")
            cap.release()
            continue
        _apply(cap, 1280, 720, order, mjpg, fps_hint)
        w, h, fourcc = _observe(cap)
        fps = measure_fps(cap, seconds=2.0, warmup=5)
        cap.release()
        rows.append({"label": label, "w": w, "h": h, "fourcc": fourcc, "fps": fps})
        flag = "  <-- usable" if (fps >= MIN_USABLE_FPS and w >= 1280) else ""
        print(f"{label:<34}{f'{w}x{h}':<12}{fourcc:<8}{fps:>6.1f}{flag}")

    print("-" * 74)
    if not rows:
        print("The camera could not be opened at all. Close anything that might be using")
        print("it (Teams, Zoom, Meet, Camera) and try again.")
        return

    good = [r for r in rows if r["fps"] >= MIN_USABLE_FPS and r["w"] >= 1280]
    any_mjpg = [r for r in rows if r["fourcc"].upper() in ("MJPG", "MJPB")]
    best = max(rows, key=lambda r: (r["w"] >= 1280, r["fps"]))

    if good:
        print(f"GOOD: '{good[0]['label']}' gives {good[0]['fps']:.1f} fps at "
              f"{good[0]['w']}x{good[0]['h']}.")
        print("The software picks this by itself now and remembers it. Run:")
        print("    python setup_check.py")
        print("and it should pass.")
        return

    print(f"No combination reached {MIN_USABLE_FPS:.0f} fps at 1280x720.")
    print(f"Best was '{best['label']}' at {best['fps']:.1f} fps, {best['w']}x{best['h']}, "
          f"{best['fourcc']}.")
    print()
    if not any_mjpg:
        print("Not one mode gave compressed (MJPG) frames, so this camera only offers")
        print("uncompressed video at this size - that is a hardware limit, not a setting.")
    for t in diagnose_low_fps(best["fps"], {"fourcc": best["fourcc"]}):
        print("  - " + t)
    print()
    print("Send this table to Sudaroli. If a different USB port does not fix it we will")
    print("swap the camera or the machine rather than lower the resolution.")


if __name__ == "__main__":
    main()
