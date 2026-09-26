"""
The selection engine: gaze zone in, selections out. No camera, no UI, no drawing here, so
it can be tested headless (`test_engine.py`) and reused by the study app and the analysis.

Feed it (timestamp_ms, zone) where zone is 0..k-1 or None when no face / no confident zone.
It implements exactly the designs E4 simulated:

  pattern "direct"  pages of (k-1) items plus a "next" zone, the user drives the paging
  pattern "scan"    the page advances by itself every scan_ms; all k zones are items
  guard  None       the first dwell selects
  guard  "double"   the item is accepted only if the next dwell lands on the same zone
  guard  "confirm"  a yes/no screen follows (2 zones: left = yes, right = no)

A dwell is `dwell_ms` of the same zone, with at least `min_frac` of the frames in that
window agreeing, and a refractory pause after each decision so one long look is one action.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Event:
    kind: str                 # "dwell" | "select" | "reject" | "page" | "confirm_yes" | "confirm_no"
    t_ms: float
    zone: int | None = None
    item: str | None = None
    page: int = 0
    detail: str = ""


@dataclass
class Engine:
    items: list                      # the full ranked list the interface is paging through
    zones: int = 3
    pattern: str = "direct"          # "direct" | "scan"
    guard: str | None = "double"     # None | "double" | "confirm"
    dwell_ms: int = 500
    min_frac: float = 0.6
    refractory_ms: int = 400
    scan_ms: int = 3000
    next_first: bool = False         # put "next" in the FIRST zone instead of the last, so that
                                     # cued items are not always on the same side of the screen
    t0: float = 0.0

    page: int = 0
    pending: int | None = None       # the zone waiting for its second dwell / confirm
    state: str = "select"            # "select" | "confirm"
    _buf: list = field(default_factory=list)      # (t_ms, zone) inside the current window
    pending_item: str | None = None              # the label behind `pending`, so the layout can move
    _locked_until: float = 0.0
    _last_page_t: float = 0.0
    log: list = field(default_factory=list)

    def __post_init__(self):
        self._last_page_t = self.t0

    # ---------------------------------------------------------------- layout
    @property
    def items_per_page(self) -> int:
        return self.zones if self.pattern == "scan" else self.zones - 1

    @property
    def n_pages(self) -> int:
        n = self.items_per_page
        return max(1, -(-len(self.items) // n))

    def screen(self) -> list:
        """What is shown now: the items on this page, then 'next' for the direct pattern,
        or ['yes', 'no'] while confirming."""
        if self.state == "confirm":
            return ["yes", "no"]
        n = self.items_per_page
        page_items = self.items[self.page * n:(self.page + 1) * n]
        page_items = page_items + [""] * (n - len(page_items))
        if self.pattern == "scan":
            return page_items
        return (["next"] + page_items) if self.next_first else (page_items + ["next"])

    # ---------------------------------------------------------------- input
    def tick(self, t_ms: float, zone: int | None) -> list[Event]:
        """One frame. Returns the events it produced (usually none)."""
        out = []
        if self.pattern == "scan" and self.state == "select" and t_ms - self._last_page_t >= self.scan_ms:
            self.page = (self.page + 1) % self.n_pages
            self._last_page_t = t_ms
            self.pending = None                       # a page change cancels a half-made choice
            # ...and so does it cancel a dwell in progress: the content under the eyes changed,
            # so the frames collected so far were spent looking at a word that is no longer
            # there. Without this, a dwell that began on the target completes against whatever
            # replaced it - live scanning accuracy was 0.06-0.13 because of exactly this.
            self._buf.clear()
            self._locked_until = t_ms + self.refractory_ms
            out.append(Event("page", t_ms, page=self.page, detail="auto"))
        if t_ms < self._locked_until:
            self._buf.clear()
            return out
        self._buf.append((t_ms, zone))
        cut = t_ms - self.dwell_ms
        if self._buf[0][0] > cut:
            return out                                 # we have not been watching for a full dwell yet
        self._buf = [(t, z) for t, z in self._buf if t >= cut - 2 * self.dwell_ms]
        win = [(t, z) for t, z in self._buf if t >= cut]
        zones = [z for _, z in win if z is not None]
        if not zones:
            return out
        top = max(set(zones), key=zones.count)
        if zones.count(top) / max(1, len(win)) < self.min_frac:
            return out
        out.extend(self._decide(t_ms, top))
        self._buf.clear()
        self._locked_until = t_ms + self.refractory_ms
        return out

    # ---------------------------------------------------------------- decisions
    def _decide(self, t_ms: float, zone: int) -> list[Event]:
        out = [Event("dwell", t_ms, zone=zone, page=self.page)]
        screen = self.screen()
        label = screen[zone] if zone < len(screen) else ""

        if self.state == "confirm":
            self.state = "select"
            if zone == 0:                              # yes
                item = self.pending_item
                self.pending = self.pending_item = None
                out.append(Event("confirm_yes", t_ms, zone=zone, item=item, page=self.page))
                out.append(Event("select", t_ms, zone=zone, item=item, page=self.page, detail="confirm"))
            else:
                self.pending = self.pending_item = None
                out.append(Event("confirm_no", t_ms, zone=zone, page=self.page))
                out.append(Event("reject", t_ms, zone=zone, page=self.page, detail="confirm"))
            self.log.extend(out)
            return out

        if self.pattern == "direct" and label == "next":
            self.page = (self.page + 1) % self.n_pages
            self.pending = None
            out.append(Event("page", t_ms, page=self.page, detail="user"))
            self.log.extend(out)
            return out

        if label == "":                                # an empty slot on the last page
            self.log.extend(out)
            return out

        if self.guard == "double":
            if self.pending is None or self.pending != zone:
                self.pending, self.pending_item = zone, label
                out.append(Event("reject", t_ms, zone=zone, item=label, page=self.page,
                                 detail="first of two" if self.pending == zone else "disagreed"))
            else:
                self.pending = self.pending_item = None
                out.append(Event("select", t_ms, zone=zone, item=label, page=self.page, detail="double"))
        elif self.guard == "confirm":
            self.pending, self.pending_item = zone, label
            self.state = "confirm"
            out.append(Event("reject", t_ms, zone=zone, item=label, page=self.page, detail="awaiting confirm"))
        else:
            out.append(Event("select", t_ms, zone=zone, item=label, page=self.page, detail="none"))
        self.log.extend(out)
        return out

    def reset(self, t_ms: float = 0.0):
        self.page, self.pending, self.state = 0, None, "select"
        self._buf.clear()
        self._locked_until = 0.0
        self._last_page_t = t_ms
