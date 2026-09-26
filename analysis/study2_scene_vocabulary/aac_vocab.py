"""
E2: the AAC-relevant vocabulary and the text-to-LVIS matcher. Fixed before any
E2 result was seen.

AAC_VOCAB lists everyday objects that a person with severe motor impairment at
home or in a care setting might ask for, use or talk about: drink and food,
personal care and medical items, comfort and bedding, devices, furniture, and
pets. The entries are LVIS category names. Entries that the LVIS version in use
does not contain are reported and dropped, never silently remapped.
"""
from __future__ import annotations

import re

AAC_VOCAB = [
    # drink and food
    "bottle", "water_bottle", "cup", "mug", "glass_(drink_container)", "wineglass", "kettle", "teapot",
    "coffee_maker", "milk", "orange_juice", "banana", "apple", "orange_(fruit)", "bread", "sandwich",
    "cake", "cookie", "doughnut", "pizza", "bowl", "plate", "spoon", "fork", "knife", "straw_(for_drinking)",
    "napkin",
    # personal care and medical
    "toothbrush", "toothpaste", "hairbrush", "comb", "towel", "hand_towel", "soap", "toilet_tissue",
    "tissue_paper", "medicine", "pill", "spectacles", "wheelchair", "crutch", "walking_stick",
    "toilet", "sink", "bathtub", "shower_head",
    # comfort, bedding, clothing
    "bed", "pillow", "cushion", "blanket", "quilt", "bedspread", "slipper_(footwear)", "sock", "shoe",
    "jacket", "sweater", "hat",
    # environment and devices
    "lamp", "table_lamp", "fan", "heater", "air_conditioner", "curtain", "clock", "wall_clock",
    "alarm_clock", "television_set", "remote_control", "radio_receiver", "cellular_telephone",
    "telephone", "laptop_computer", "book", "newspaper", "magazine", "pen", "notebook", "headset",
    "earphone",
    # furniture
    "chair", "armchair", "recliner", "sofa", "table", "dining_table", "coffee_table", "desk",
    "refrigerator", "microwave_oven", "stove", "trash_can",
    # other
    "dog", "cat", "vase", "painting", "mirror", "flower_arrangement",
]

ROOM_INDICATORS = [          # priority order: the first matching room wins
    ("bathroom", ["toilet", "bathtub", "shower_curtain", "shower_head"]),
    ("bedroom", ["bed", "bunk_bed"]),
    ("kitchen", ["refrigerator", "stove", "microwave_oven", "oven", "kitchen_sink", "dishwasher"]),
    ("living room", ["sofa", "armchair", "television_set", "coffee_table"]),
    ("dining", ["dining_table"]),
]

STOP = {"a", "an", "the", "some", "of", "with", "on", "in", "and", "or", "for", "to", "at", "by"}
CUT = {"of", "for", "on", "with", "in", "at", "from", "near"}   # 'glass of water' -> 'glass'

# Everyday words -> LVIS names, fixed before any output was seen. Applied to every
# method alike. A target missing from the LVIS release in use is skipped.
ALIASES = {
    "fridge": "refrigerator", "laptop": "laptop_computer", "microwave": "microwave_oven",
    "tv": "television_set", "television": "television_set", "telly": "television_set",
    "remote": "remote_control", "tv remote": "remote_control",
    "phone": "cellular_telephone", "cell phone": "cellular_telephone", "cellphone": "cellular_telephone",
    "mobile phone": "cellular_telephone", "mobile": "cellular_telephone", "smartphone": "cellular_telephone",
    "wine glass": "wineglass", "glasses": "spectacles", "eyeglasses": "spectacles",
    "couch": "sofa", "settee": "sofa", "bin": "trash_can", "dustbin": "trash_can", "garbage can": "trash_can",
    "toilet paper": "toilet_tissue", "tissues": "tissue_paper", "tissue": "tissue_paper",
    "water glass": "glass_(drink_container)", "drinking glass": "glass_(drink_container)",
    "mouse": "mouse_(computer_equipment)", "computer mouse": "mouse_(computer_equipment)",
    "tap": "faucet", "duvet": "quilt", "comforter": "quilt", "bedsheet": "sheet_(bedding)",
    "potted plant": "flowerpot", "plant pot": "flowerpot", "teddy": "teddy_bear",
}

# Lenient scoring: an item also counts as correct if a category in the same group is present.
LENIENT_GROUPS = [
    {"table", "dining_table", "coffee_table", "kitchen_table", "desk"},
    {"clock", "wall_clock", "alarm_clock"},
    {"lamp", "table_lamp"},
    {"towel", "hand_towel", "bath_towel", "dishtowel", "paper_towel"},
    {"blanket", "quilt", "bedspread"},
    {"cup", "mug"},
    {"glass_(drink_container)", "wineglass"},
    {"telephone", "cellular_telephone"},
    {"bottle", "water_bottle", "beer_bottle", "wine_bottle"},
    {"pillow", "cushion"},
]


def canon(name: str) -> str:
    """LVIS name -> plain words: 'glass_(drink_container)' -> 'glass', 'television_set' -> 'television set'."""
    name = re.sub(r"_?\(.*?\)", "", name)
    return name.replace("_", " ").strip().lower()


def _singular_candidates(w: str) -> list[str]:
    out = []
    for suf, rep in (("ies", "y"), ("ves", "f"), ("ves", "fe"), ("oes", "o"), ("ches", "ch"),
                     ("shes", "sh"), ("sses", "ss"), ("xes", "x"), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            out.append(w[: -len(suf)] + rep)
    return out


class Matcher:
    """Maps free text ('Two white pillows') to one LVIS category id, or None.

    Tries, in order: the whole phrase, the phrase singularised, then shorter
    trailing phrases (so 'wooden coffee table' -> 'coffee table' -> 'table'),
    always by exact equality with a canonicalised name or synonym."""

    def __init__(self, categories: list[dict]):
        self.id2name = {c["id"]: c["name"] for c in categories}
        by_name = {c["name"]: c["id"] for c in categories}
        self.lookup: dict[str, int] = {}
        self.clashes: dict[str, list[str]] = {}
        for c in sorted(categories, key=lambda c: c["id"]):
            for s in [c["name"]] + list(c.get("synonyms", [])):
                k = canon(s)
                if k in self.lookup and self.lookup[k] != c["id"]:
                    self.clashes.setdefault(k, [self.id2name[self.lookup[k]]]).append(c["name"])
                self.lookup.setdefault(k, c["id"])          # first (lowest id) wins on a clash
        own = {}                                            # a category's own name beats others' synonyms
        for c in sorted(categories, key=lambda c: c["id"]):
            own.setdefault(canon(c["name"]), c["id"])       # name-vs-name clash: lowest id
        self.lookup.update(own)
        self.aliases_used = {}
        for k, target in ALIASES.items():
            if target in by_name:
                self.lookup[k] = by_name[target]
                self.aliases_used[k] = target
        self.group = {}
        for g in LENIENT_GROUPS:
            ids = {by_name[n] for n in g if n in by_name}
            for i in ids:
                self.group[i] = ids
        self.head = {cid: canon(n).split()[-1] for cid, n in self.id2name.items()}

    def match(self, text: str):
        t = re.sub(r"[^a-z\s-]", " ", text.lower()).replace("-", " ")
        raw = t.split()
        whole = " ".join(w for w in raw if w not in {"a", "an", "the"})
        if whole in self.lookup:                         # 'chest of drawers' as a whole name
            return self.lookup[whole]
        for j, w in enumerate(raw):                      # 'glass of water' -> 'glass'
            if w in CUT and j > 0:
                raw = raw[:j]
                break
        words = [w for w in raw if w not in STOP]
        if not words:
            return None
        for i in range(len(words)):                      # longest trailing phrase first
            phrase = words[i:]
            cands = [" ".join(phrase)] + [" ".join(phrase[:-1] + [w]) for w in _singular_candidates(phrase[-1])]
            for cand in cands:
                if cand in self.lookup:
                    return self.lookup[cand]
        return None

    def resolve_vocab(self, names: list[str]):
        ids, missing = [], []
        by_name = {v: k for k, v in self.id2name.items()}
        for n in names:
            cid = by_name.get(n)                               # exact LVIS names only
            if cid is None:
                missing.append(n)
            elif cid not in ids:
                ids.append(cid)
        return ids, missing
