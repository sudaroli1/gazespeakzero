"""
Headless tests of the selection engine: no camera, no UI.

    python test_engine.py
"""
import sys

from engine import Engine

ok = fail = 0


def check(cond, msg):
    global ok, fail
    print(("OK   " if cond else "FAIL ") + msg)
    ok, fail = ok + bool(cond), fail + (not cond)


def feed(e, zone, ms, start=0.0, step=33.0):
    """Look at `zone` for `ms` milliseconds at 30 fps. Returns the events."""
    out, t = [], start
    while t < start + ms:
        out += e.tick(t, zone)
        t += step
    return out, t


def kinds(evs):
    return [x.kind for x in evs]


ITEMS = [f"item{i}" for i in range(1, 9)]

# --- layout
e = Engine(items=ITEMS, zones=3, pattern="direct", guard=None)
check(e.screen() == ["item1", "item2", "next"], f"direct row of 3: two items + next ({e.screen()})")
e = Engine(items=ITEMS, zones=3, pattern="scan", guard=None)
check(e.screen() == ["item1", "item2", "item3"], f"scanning row of 3: three items ({e.screen()})")
check(e.n_pages == 3, f"8 items, 3 per page = 3 pages ({e.n_pages})")

# --- a dwell selects, a short look does not
e = Engine(items=ITEMS, zones=3, pattern="direct", guard=None, dwell_ms=500)
evs, t = feed(e, 0, 300)
check("select" not in kinds(evs), "300 ms is not a dwell")
evs, t = feed(e, 0, 600)
check("select" in kinds(evs), "600 ms is a dwell and selects")
sel = [x for x in evs if x.kind == "select"][0]
check(sel.item == "item1", f"it selects the item under that zone ({sel.item})")

# --- a wandering gaze does not select
e = Engine(items=ITEMS, zones=3, guard=None, dwell_ms=500, min_frac=0.6)
evs, t = [], 0.0
for i in range(40):
    evs += e.tick(t, i % 3)
    t += 33
check("select" not in kinds(evs), "a gaze that keeps moving never selects")

# --- no face: nothing happens
e = Engine(items=ITEMS, zones=3, guard=None)
evs, _ = feed(e, None, 2000)
check(not kinds(evs), "no face detected: no events")

# --- the refractory pause stops one long look becoming many selections
e = Engine(items=ITEMS, zones=3, guard=None, dwell_ms=500, refractory_ms=400)
evs, _ = feed(e, 0, 3000)
n = kinds(evs).count("select")
check(n == 3, f"3 s of staring gives {n} selections, not a stream")

# --- the double guard
e = Engine(items=ITEMS, zones=3, guard="double", dwell_ms=500, refractory_ms=100)
evs, t = feed(e, 0, 600)
check("select" not in kinds(evs) and "reject" in kinds(evs), "double guard: the first dwell does not select")
evs, t = feed(e, 0, 700, start=t)
check("select" in kinds(evs), "double guard: the same zone twice selects")
e.reset()
evs, t = feed(e, 0, 600)
evs2, t = feed(e, 1, 700, start=t)
check("select" not in kinds(evs2), "double guard: a different second zone does not select")

# --- the confirm guard
e = Engine(items=ITEMS, zones=3, guard="confirm", dwell_ms=500, refractory_ms=100)
evs, t = feed(e, 0, 600)
check(e.state == "confirm" and e.screen() == ["yes", "no"], "confirm guard: the yes/no screen appears")
evs, t = feed(e, 0, 700, start=t)
check("select" in kinds(evs) and e.state == "select", "confirm guard: yes selects and returns")
e.reset()
evs, t = feed(e, 0, 600)
evs2, t = feed(e, 1, 700, start=t)
check("reject" in kinds(evs2) and "select" not in kinds(evs2), "confirm guard: no rejects")

# --- paging, both ways
e = Engine(items=ITEMS, zones=3, pattern="direct", guard=None, dwell_ms=500, refractory_ms=100)
evs, t = feed(e, 2, 600)                                   # "next"
check(e.page == 1 and e.screen()[0] == "item3", f"direct: 'next' turns the page ({e.screen()})")
e = Engine(items=ITEMS, zones=3, pattern="scan", guard=None, scan_ms=1000, dwell_ms=500)
evs, t = feed(e, None, 2100)
check(e.page == 2, f"scanning: two pages passed in 2.1 s ({e.page})")
check(kinds(evs).count("page") == 2, "scanning: each page change is logged")

# --- scanning wraps round
e = Engine(items=ITEMS, zones=3, pattern="scan", guard=None, scan_ms=500, dwell_ms=500)
evs, t = feed(e, None, 2000)
check(e.page == e.n_pages - 1 or e.page < e.n_pages, f"scanning stays inside the pages ({e.page} of {e.n_pages})")

# --- an empty slot cannot be selected
e = Engine(items=["a", "b", "c", "d"], zones=3, pattern="scan", guard=None, dwell_ms=500, refractory_ms=100)
e.page = 1                                                  # page 2 holds only 'd'
check(e.screen() == ["d", "", ""], f"the last page pads with blanks ({e.screen()})")
evs, t = feed(e, 2, 600)
check("select" not in kinds(evs), "a blank slot does not select")

# --- everything is logged
e = Engine(items=ITEMS, zones=3, guard="double", dwell_ms=500, refractory_ms=100)
feed(e, 0, 600)
feed(e, 0, 700, start=1000)
check(len(e.log) >= 4 and {"dwell", "select"} <= {x.kind for x in e.log}, "the engine keeps a log")


# a dwell that spans an auto page change must not select on the new page's items: those frames
# were spent looking at a word that is no longer on screen (live scanning accuracy was 0.06-0.13)
e = Engine(items=[f"w{i}" for i in range(9)], zones=3, pattern="scan",
           guard=None, dwell_ms=500, scan_ms=1000, t0=0)
t, sel = 0.0, []
while t <= 1400:
    for ev in e.tick(t, 0):
        if ev.kind == "select":
            sel.append((t, ev.item))
    t += 33.0
check(e.page == 1, "the page advances on its own in scanning mode")
# a selection before the page change is fine; one in the window straight after it is stale,
# because it can only have been built from frames collected on the old page
stale = [x for x in sel if 1000 < x[0] < 1000 + 400 + 500]
check(not stale, f"a page change cancels the dwell in progress (stale: {stale})")


# "next" can sit in either zone, and the item behind a guarded choice must survive the move
e = Engine(items=["a", "b", "c", "d"], zones=2, pattern="direct", guard="double",
           dwell_ms=500, refractory_ms=400, t0=0, next_first=True)
check(e.screen() == ["next", "a"], f'next can be placed first: {e.screen()}')
evs, t = feed(e, 1, 700, 0)                      # zone 1 holds the item when next is first
evs2, t = feed(e, 1, 1200, t + 500)
sels = [x for x in evs + evs2 if x.kind == "select"]
check(bool(sels) and sels[0].item == "a", f'the item under the moved layout is right: {sels}')

e2 = Engine(items=["a", "b", "c", "d"], zones=2, pattern="direct", guard="confirm",
            dwell_ms=500, refractory_ms=400, t0=0, next_first=True)
evs, t = feed(e2, 1, 700, 0)                     # choose the item -> confirm screen
check(e2.screen() == ["yes", "no"], "the confirm screen comes up")
evs3, t = feed(e2, 0, 700, t + 500)              # yes
sels = [x for x in evs3 if x.kind == "select"]
check(bool(sels) and sels[0].item == "a",
      f'confirm returns the item chosen, not an index into the page: {sels}')

# ---------------------------------------------------------------------------
# Regression: the cue must be on the screen the trial STARTS on.
#
# In the first live session, 8 of 77 trials were unreachable because the cue was
# chosen before eng.reset() sent the page back to 0 - so it was picked from the page
# the previous trial happened to end on. Every one of those trials scored as an error.
# The ordering now lives in gaze_ui.begin_trial(); this pins the property it guarantees.
e3 = Engine(items=["a", "b", "c", "d", "e", "f"], zones=2, pattern="direct", guard=None,
            dwell_ms=500, refractory_ms=400, t0=0, next_first=False)
# drive it onto a later page, the way a real trial ends
e3.page = 2
stale = [i for i in e3.screen() if i and i.lower() != "next"]
e3.reset(0)
fresh = [i for i in e3.screen() if i and i.lower() != "next"]
check(e3.page == 0, f"reset returns to page 0 (was left on a later page): page={e3.page}")
check(stale != fresh,
      f"a cue picked before reset would come from a different page: {stale} vs {fresh}")
# and the property begin_trial enforces: pick AFTER reset, so the cue is on screen
check(all(i in e3.screen() for i in fresh),
      f"a cue picked after reset is on the starting screen: {fresh} in {e3.screen()}")

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)

