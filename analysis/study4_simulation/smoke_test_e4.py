"""
E4 smoke test: checks the simulator against cases that can be worked out by hand.

    python smoke_test_e4.py
"""
import sys

import numpy as np

from e4_sim import Interface, simulate, wolpaw_bits

ok = fail = 0


def check(cond, msg):
    global ok, fail
    print(("OK   " if cond else "FAIL ") + msg)
    ok, fail = ok + bool(cond), fail + (not cond)


PERFECT = {2: 1.0, 3: 1.0, 4: 1.0, 9: 1.0}
rng = np.random.default_rng(0)
S = 0.8       # seconds per selection
C = 3.0       # seconds per scan step


def one(f, rank, fixed=50, acc=PERFECT, answered=1.0, n_vocab=96):
    return simulate(f, rank, fixed, acc, answered, rng, n_vocab, S, C)


row3 = Interface("row3", 3, "direct", None, "scene")
row3d = Interface("row3d", 3, "direct", "double", "scene")
row3c = Interface("row3c", 3, "direct", "confirm", "scene")
scan3 = Interface("scan3", 3, "scan", None, "scene")
scan3d = Interface("scan3d", 3, "scan", "double", "scene")
halv = Interface("halv", 2, "halving", None, "fixed")

# --- perfect gaze: the counts are deterministic
s, sec, w, ab = one(row3, 1)
check((s, w, ab) == (1, False, False) and abs(sec - S) < 1e-9, f"row of 3, item first: 1 selection ({s})")
s, _, w, _ = one(row3, 3)
check(s == 2 and not w, f"row of 3, item 3 = page 2: 2 selections ({s})")     # 2 items per page + 'next'
s, _, w, _ = one(row3, 5)
check(s == 3 and not w, f"row of 3, item 5 = page 3: 3 selections ({s})")
s, _, w, _ = one(row3d, 1)
check(s == 2 and not w, f"double guard doubles the final selection ({s})")
s, _, w, _ = one(row3c, 1)
check(s == 2 and not w, f"confirm adds one selection ({s})")
s, _, w, _ = one(halv, 1)
check(s == 7 and not w, f"halving 96 items: ceil(log2 96) = 7 selections ({s})")

# --- scanning: selections are few, the time is the waiting
s, sec, w, _ = one(scan3, 1)
check(s == 1 and abs(sec - S) < 1e-9, f"scan, item on the first page: no waiting ({sec:.1f}s)")
s, sec, w, _ = one(scan3, 7)
check(s == 1 and abs(sec - (2 * C + S)) < 1e-9, f"scan, item 7 = third page: 2 scan steps ({sec:.1f}s)")

# --- the scene list not containing the item costs the fallback
s, sec, w, _ = one(row3, 999, fixed=1)
check(s == 1 + 6 and not w, f"scene miss: pages through 12 items (6 pages), then the vocabulary ({s})")
s, sec, w, _ = one(scan3, 999, fixed=1)
check(s == 1 and abs(sec - (4 * C + S)) < 1e-9, f"scan scene miss: one cycle of 4 pages, then fallback ({sec:.1f}s)")

# --- unanswered dwells cost extra selections, never a wrong message
s, _, w, _ = one(row3, 1, answered=0.5)
check(s >= 1 and not w, f"unanswered dwells only add cost ({s} selections)")

# --- accuracy drives the error rate, monotonically
prev = -1
for p in (0.5, 0.7, 0.9, 1.0):
    acc = dict(PERFECT)
    acc[3] = p
    wrong = np.mean([one(row3, 1, acc=acc)[2] for _ in range(3000)])
    check(wrong >= -1e-9 and (prev < 0 or wrong <= prev + 0.02), f"accuracy {p}: wrong-message rate {wrong:.3f}")
    prev = wrong
acc = dict(PERFECT)
acc[3] = 0.7
w_plain = np.mean([one(row3, 1, acc=acc)[2] for _ in range(3000)])
w_guard = np.mean([one(row3d, 1, acc=acc)[2] for _ in range(3000)])
check(w_guard < w_plain, f"the double guard lowers the error rate ({w_guard:.3f} < {w_plain:.3f})")
s_plain = np.mean([one(row3, 1, acc=acc)[0] for _ in range(3000)])
s_guard = np.mean([one(row3d, 1, acc=acc)[0] for _ in range(3000)])
check(s_guard > s_plain, f"and costs selections ({s_guard:.1f} > {s_plain:.1f})")

# --- Wolpaw bits behave
check(abs(wolpaw_bits(1.0, 2) - 1.0) < 1e-6, "Wolpaw: perfect binary choice = 1 bit")
check(abs(wolpaw_bits(0.5, 2)) < 1e-6, "Wolpaw: chance binary choice = 0 bits")
check(abs(wolpaw_bits(1.0, 8) - 3.0) < 1e-6, "Wolpaw: perfect 8-way choice = 3 bits")

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
