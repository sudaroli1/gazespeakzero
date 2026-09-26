"""
E1b, step 1: per-frame webcam features + synchronised Tobii gaze from the
Eye of the Typer (EOTT) dataset (Papoutsaki et al., ETRA 2018; Brown HCI, GPLv3).

For each participant and each selected task video:
  * decode the webcam .webm with PyAV and time-stamp every frame
    (recording-start epoch from the browser log + frame presentation time);
  * run MediaPipe FaceLandmarker in VIDEO mode and compute exactly the E1
    features (e1/extract_features.features_from_result);
  * attach the Tobii Pro X3-120 gaze sample nearest in time.

Also writes the raw Tobii stream for each task interval, which analysis uses
to find fixations.

    python eott_extract.py --zip eott.zip --chars participant_characteristics.csv \
        --model face_landmarker.task --out eott_features [--participants P_01 P_02] \
        [--max-seconds 20]            # dry run: first 20 s of each video

--zip reads the dataset straight from the zip and unpacks one participant at a
time into a scratch folder that is deleted afterwards, so the disk never holds
more than the zip plus one participant. (--data works on an unpacked folder.)

Resumable per participant (skips a participant whose done-marker exists).

Format facts are taken from the dataset's own extractor
(github.com/brownhci/WebGazer, www/data/src/participant.py and
webgazerExtractServer.py): browser log <startTimestamp>.json with
"recording start" events (sessionString -> '/' replaced by '-' + '.webm',
epoch in ms); Tobii log P_X/P_X.txt, one JSON object per line with
true_time (s), {left,right}_gaze_point_on_display_area (normalised),
{left,right}_pupil_validity.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "study1_zone_classification"))
sys.path.insert(0, HERE)

TASK_RE = re.compile(r"-study-(dot_test|dot_test_final|fitts_law)\.webm$")
TOBII_MATCH_MS = 20          # a frame gets a Tobii label only if a sample lies within this


# ----------------------------------------------------------------------------- inputs
def read_characteristics(path: str) -> dict:
    """participant -> {'setup': 'Laptop'|'PC', 'screen_w_px', 'screen_h_px'} (columns as in the extractor)."""
    out = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].startswith("P_"):
                continue
            try:
                out[row[0]] = {"setup": row[3].strip(), "screen_w_px": int(row[4]), "screen_h_px": int(row[5])}
            except (IndexError, ValueError):
                continue
    return out


def read_log(pdir: str) -> tuple[list[dict], str]:
    webm = glob.glob(os.path.join(pdir, "*dot_test_instructions.webm"))
    if not webm:
        raise FileNotFoundError(f"{pdir}: no *dot_test_instructions.webm (cannot find the log start timestamp)")
    start = os.path.basename(webm[0]).split("_")[0]
    log_path = os.path.join(pdir, f"{start}.json")
    with open(log_path) as f:
        log = json.load(f)
    return log, log_path


def recording_starts(log: list[dict]) -> dict:
    """video filename -> recording-start epoch (ms)."""
    starts = {}
    for ev in log:
        if ev.get("type") == "recording start" and ev.get("sessionString"):
            fn = ev["sessionString"].replace("/", "-") + ".webm"
            starts[fn] = int(ev["epoch"])
    return starts


def read_tobii(pdir: str) -> pd.DataFrame:
    pid = os.path.basename(pdir.rstrip("/\\"))
    rows = []
    with open(os.path.join(pdir, f"{pid}.txt")) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue                      # the extractor notes one truncated last line
            rv, lv = int(d["right_pupil_validity"]), int(d["left_pupil_validity"])
            def pt(key, valid):
                try:
                    x, y = (float(v) for v in d[key][:2])
                except (TypeError, ValueError, KeyError):
                    return np.nan, np.nan
                return (x, y) if valid and np.isfinite(x) and np.isfinite(y) else (np.nan, np.nan)
            r_ = pt("right_gaze_point_on_display_area", rv)
            l_ = pt("left_gaze_point_on_display_area", lv)
            with np.errstate(all="ignore"):
                x = np.nanmean([r_[0], l_[0]]) if np.isfinite([r_[0], l_[0]]).any() else np.nan
                y = np.nanmean([r_[1], l_[1]]) if np.isfinite([r_[1], l_[1]]).any() else np.nan
            ok = int(np.isfinite(x) and np.isfinite(y))
            rows.append((round(float(d["true_time"]) * 1000), float(x), float(y), ok))
    t = pd.DataFrame(rows, columns=["t_ms", "tx", "ty", "tvalid"]).sort_values("t_ms")
    return t.drop_duplicates("t_ms").reset_index(drop=True)


# ----------------------------------------------------------------------------- video
def frame_times(pts_ms: list) -> np.ndarray:
    """Per-frame times (ms from recording start) from the raw presentation times,
    as the dataset's own extractor does. The dataset notes that many webm frames
    repeat the previous frame's timestamp and some are missing: a stamp that is
    missing or not later than the previous good one is filled by linear
    interpolation between its good neighbours (by frame index). A single line
    fit is NOT used, because webcam frame rates drift and stall."""
    n = len(pts_ms)
    idx = np.arange(n, dtype=float)
    p = np.array([np.nan if v is None else float(v) for v in pts_ms])
    good = np.zeros(n, bool)
    last = -np.inf
    for i in range(n):
        if np.isfinite(p[i]) and p[i] > last:
            good[i] = True
            last = p[i]
    if good.sum() < 5:
        return idx * 33.3
    t = np.interp(idx, idx[good], p[good])
    # extrapolate beyond the last/first good stamp with the median frame period
    per = np.median(np.diff(p[good])) / max(np.median(np.diff(idx[good])), 1)
    lo, hi = np.argmax(good), n - 1 - np.argmax(good[::-1])
    t[:lo] = p[lo] - per * (lo - idx[:lo])
    t[hi + 1:] = p[hi] + per * (idx[hi + 1:] - hi)
    return t


def packet_pts(path: str, max_seconds: float | None) -> list:
    """Pass 1: presentation times (ms) from the container, without decoding pixels.
    VP8/VP9 webcam streams have no B-frames, so packet order is frame order."""
    import av
    pts = []
    with av.open(path) as c:
        s = c.streams.video[0]
        tb = float(s.time_base) if s.time_base else 0.001
        for pkt in c.demux(s):
            if pkt.size == 0:
                continue
            pts.append(None if pkt.pts is None else pkt.pts * tb * 1000.0)
            if max_seconds and pts[-1] is not None and pts[-1] > max_seconds * 1000:
                break
    return pts


def iter_frames(path: str, n_max: int):
    """Pass 2: decoded RGB frames, streamed (a whole video does not fit in memory)."""
    import av
    with av.open(path) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        for i, fr in enumerate(c.decode(s)):
            if i >= n_max:
                break
            yield fr.to_ndarray(format="rgb24")


# ----------------------------------------------------------------------------- main
def process_participant(pdir, chars, model_path, out_dir, max_seconds):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    from extract_features import features_from_result

    pid = os.path.basename(pdir.rstrip("/\\"))
    info = chars.get(pid)
    if info is None:
        print(f"{pid}: not in participant_characteristics.csv, skipped")
        return
    log, _ = read_log(pdir)
    starts = recording_starts(log)
    tob = read_tobii(pdir)
    vids = sorted(v for v in glob.glob(os.path.join(pdir, "*.webm")) if TASK_RE.search(os.path.basename(v)))
    rows, tob_keep = [], []
    vids.sort(key=lambda v: starts.get(os.path.basename(v), float("inf")))   # chronological
    for v in vids:
        n0, k0 = len(rows), len(tob_keep)
        try:
            _one_video(v, pid, info, starts, tob, model_path, max_seconds, rows, tob_keep)
        except Exception as e:
            del rows[n0:], tob_keep[k0:]                  # drop a half-processed video
            print(f"  {pid} {os.path.basename(v)}: FAILED {type(e).__name__}: {e}", flush=True)
    if not rows:
        print(f"{pid}: no task videos processed")
        return
    suffix = ".dry" if max_seconds else ""
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, f"{pid}_frames{suffix}.csv"), index=False)
    pd.concat(tob_keep).to_csv(os.path.join(out_dir, f"{pid}_tobii{suffix}.csv"), index=False)
    if not max_seconds:
        open(os.path.join(out_dir, f"{pid}.done"), "w").close()


def _one_video(v, pid, info, starts, tob, model_path, max_seconds, rows, tob_keep):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    from extract_features import features_from_result
    if True:
        fn = os.path.basename(v)
        task = TASK_RE.search(fn).group(1)
        if fn not in starts:
            print(f"  {pid} {fn}: no 'recording start' event, skipped")
            return
        t0 = time.time()
        pts = packet_pts(v, max_seconds)
        if len(pts) < 10:
            print(f"  {pid} {fn}: only {len(pts)} frames, skipped")
            return
        rel = frame_times(pts)
        epoch = starts[fn] + rel
        opts = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO, num_faces=1,
            output_face_blendshapes=True, output_facial_transformation_matrixes=True)
        # nearest Tobii sample
        tt = tob["t_ms"].values
        j = np.clip(np.searchsorted(tt, epoch), 1, len(tt) - 1)
        jn = np.where(np.abs(tt[j - 1] - epoch) <= np.abs(tt[j] - epoch), j - 1, j)
        dt = np.abs(tt[jn] - epoch)
        last_ts = -1
        n_done = 0
        with vision.FaceLandmarker.create_from_options(opts) as lm:
            for i, rgb in enumerate(iter_frames(v, len(pts))):
                n_done += 1
                ts = max(int(round(rel[i])), last_ts + 1)
                last_ts = ts
                H, W = rgb.shape[:2]
                res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), ts)
                r = {"participant": pid, "setup": info["setup"], "task": task, "video": fn,
                     "frame": i, "pts_raw_ms": pts[i], "t_rel_ms": float(rel[i]), "epoch_ms": float(epoch[i]),
                     "img_w": W, "img_h": H}
                r.update(features_from_result(res, W, H))
                ok = dt[i] <= TOBII_MATCH_MS and tob["tvalid"].values[jn[i]] == 1
                r["tobii_x"] = float(tob["tx"].values[jn[i]]) if ok else np.nan
                r["tobii_y"] = float(tob["ty"].values[jn[i]]) if ok else np.nan
                r["tobii_dt_ms"] = float(dt[i])
                rows.append(r)
        # raw Tobii for this task's interval (for fixation detection)
        seg = tob[(tob.t_ms >= epoch[0] - 500) & (tob.t_ms <= epoch[-1] + 500)].copy()
        seg.insert(0, "video", fn)
        seg.insert(0, "task", task)
        seg.insert(0, "participant", pid)
        tob_keep.append(seg)
        if n_done != len(pts):
            print(f"  {pid} {task}: WARNING decoded {n_done} frames but container lists {len(pts)}", flush=True)
        fps = (len(pts) - 1) / max((rel[-1] - rel[0]) / 1000, 1e-6)
        gap = float(np.max(np.diff(rel))) if len(rel) > 1 else 0.0
        print(f"  {pid} {task}: {n_done} frames, {fps:.1f} fps, "
              f"{(rel[-1]-rel[0])/1000:.0f} s, longest frame gap {gap:.0f} ms, {time.time()-t0:.0f} s", flush=True)


NEEDED = re.compile(r"(-study-(dot_test|dot_test_final|fitts_law)\.webm|\.json|/P_\d+\.txt)$")


def zip_participants(zf) -> dict:
    """participant id -> list of zip members that E1b needs (read from the zip index only)."""
    groups = {}
    for zi in zf.infolist():
        name = zi.filename
        if zi.is_dir() or name.startswith("__MACOSX") or "/._" in name:
            continue
        parts = name.split("/")
        pid = next((q for q in parts[:-1] if re.fullmatch(r"P_\d+", q)), None)
        if pid is None:
            continue
        g = groups.setdefault(pid, {"need": [], "instr": None})
        if name.endswith("dot_test_instructions.webm"):
            g["instr"] = os.path.basename(name)      # only its NAME is needed (log timestamp)
        elif NEEDED.search("/" + name):
            g["need"].append(zi)
    return groups


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--data", help="folder that contains the P_* participant folders")
    src.add_argument("--zip", help="the EOTT zip; participants are unpacked one at a time and deleted after use")
    ap.add_argument("--chars", required=True, help="participant_characteristics.csv")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="eott_features")
    ap.add_argument("--tmp", default="/tmp/eott_one", help="scratch folder for --zip mode")
    ap.add_argument("--participants", nargs="*")
    ap.add_argument("--max-seconds", type=float, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    chars = read_characteristics(a.chars)
    key = lambda pid: int(re.sub(r"\D", "", pid) or 0)

    if a.data:
        pdirs = sorted((d for d in glob.glob(os.path.join(a.data, "P_*")) if os.path.isdir(d)),
                       key=lambda d: key(os.path.basename(d)))
        if a.participants:
            pdirs = [d for d in pdirs if os.path.basename(d) in a.participants]
        if not pdirs:
            sys.exit(f"no P_* folders under {a.data}")
        print(f"{len(pdirs)} participant folders; {len(chars)} in characteristics file", flush=True)
        for d in pdirs:
            pid = os.path.basename(d)
            if not a.max_seconds and os.path.exists(os.path.join(a.out, f"{pid}.done")):
                print(f"{pid}: done, skipping")
                continue
            try:
                process_participant(d, chars, a.model, a.out, a.max_seconds)
            except Exception as e:                       # keep going; report at the end
                print(f"{pid}: FAILED {type(e).__name__}: {e}", flush=True)
        return

    import shutil
    import zipfile
    with zipfile.ZipFile(a.zip) as zf:
        groups = zip_participants(zf)
        pids = sorted(groups, key=key)
        if a.participants:
            pids = [p for p in pids if p in a.participants]
        if not pids:
            sys.exit(f"no P_* participant folders inside {a.zip}")
        print(f"{len(pids)} participants in the zip; {len(chars)} in characteristics file", flush=True)
        for pid in pids:
            if not a.max_seconds and os.path.exists(os.path.join(a.out, f"{pid}.done")):
                print(f"{pid}: done, skipping")
                continue
            g = groups[pid]
            pdir = os.path.join(a.tmp, pid)
            shutil.rmtree(a.tmp, ignore_errors=True)
            os.makedirs(pdir)
            try:
                mb = sum(zi.file_size for zi in g["need"]) / 1e6
                for zi in g["need"]:
                    with zf.open(zi) as fsrc, open(os.path.join(pdir, os.path.basename(zi.filename)), "wb") as fdst:
                        shutil.copyfileobj(fsrc, fdst, 16 * 1024 * 1024)
                if g["instr"]:
                    open(os.path.join(pdir, g["instr"]), "wb").close()     # empty stand-in; only the name is read
                print(f"{pid}: unpacked {len(g['need'])} files, {mb:.0f} MB", flush=True)
                process_participant(pdir, chars, a.model, a.out, a.max_seconds)
            except Exception as e:
                print(f"{pid}: FAILED {type(e).__name__}: {e}", flush=True)
            finally:
                shutil.rmtree(a.tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
