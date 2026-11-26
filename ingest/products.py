"""Product lines for the knowledge graph (spec/features/knowledge_graph.md, MAF-36): what kind of product a form row,
a register row or a BOQ line describes, the parts that say which product line it belongs to, and its sizes.

Plain rules, no AI; each one is tested in tests/test_products.py. What makes two descriptions the same product line
was set by Luca on 26 Nov 2026, kind by kind (IDENTITY below). A part a text does not give stays None, so two lines
that differ only by an unknown part are a near match, shown as a question, never a match.
"""
import re
import unicodedata

SCOPE = ("cable", "pipe", "valve", "boiler")   # the kinds in the graph so far; pumps stay out (Luca, 26 Nov 2026)

# The parts that make a product line, by kind; the sizes are its range, not part of it
IDENTITY = {
    "pipe": ("producer", "material", "pressure", "standard", "use"),
    "cable": ("producer", "designation", "fire", "cpr", "standard"),
    "valve": ("producer", "type", "connection", "pressure", "use"),
    "boiler": ("producer", "series", "fuel"),
}

# The part that must be known, and equal, on both sides before two texts can be linked at all: without it, a cable
# of an unknown type would "almost match" every cable
MAIN = {"pipe": "material", "cable": "designation", "valve": "type", "boiler": "series"}

# The kind of a description; the order matters: insulation "for pipes" is insulation, a conduit "tub" is not a pipe
KINDS = [
    ("insulation", r"\bizola|\binsulat|\belastomer"),
    ("conduit", r"\btub(uri)? (de )?protectie|\btub(uri)? (flexibil|rigid|gofrat)|\bcopex|\bconduit|\bsarma de tragere"),
    ("tray", r"\bjgheab|\bpat(uri)? de cablu|\bcable tray|\bscar(a|i) de cablu"),
    ("valve", r"\brobinet|\bvan(a|e|ei)\b|\bclapet\w* (de retinere|de sens)|\bvalve"),
    ("damper", r"\bclapet|\bjaluzel"),   # a clapeta is an air damper, unless it says it holds water back
    ("boiler", r"\bcazan|\bcentral(a|e) termic"),
    ("cable", r"\bcablu|\bcabluri\b|\bcable\b"),
    ("pipe", r"\bteav|\btevi\b|\btub(uri)?\b|\bconduct(a|e)\b|\bpipe"),
    ("fitting", r"\bfiting|\bracord"),
]

CABLES = [   # type designations, most specific first
    (r"\bje-?h\s*\(?\s*st\s*\)?\s*h\b|\bjeh\s*\(?\s*st\s*\)?", "JE-H(St)H"), (r"\bj-?h\s*\(?\s*st\s*\)?\s*h\b", "J-H(St)H"),
    (r"\bn2xch\b", "N2XCH"), (r"\bn2xh\b", "N2XH"), (r"\bnhxh\b", "NHXH"), (r"\bcyy-?f\b", "CYY-F"), (r"\bcyaby\b", "CYABY"),
    (r"\bcyy\b", "CYY"), (r"\bnyy\b", "NYY"), (r"\bnym\b", "NYM"), (r"\bliycy\b", "LiYCY"), (r"\bliyy\b", "LiYY"),
    (r"\b(s/ftp|f/ftp|sf/utp|s/utp|f/utp|sftp|fftp|ftp|utp)\b", None),   # data cables: the screen, with the category
]
MATERIALS = [   # pipe materials, most specific first
    (r"\bpex-?al-?pex\b|\bmultistrat", "PE-X/Al/PE-X"), (r"\bpe-?al-?pe\b", "PE/Al/PE"), (r"\bpp-?rct\b", "PP-RCT"),
    (r"\bpp-?r\b|\bppr\b", "PP-R"), (r"\bpp-?ht\b", "PP-HT"), (r"\bpe-?x[ab]?\b", "PE-X"), (r"\bpe-?hd\b|\bpehd\b|\bpe\s?100\b|\bpe\s?80\b", "PE"),
    (r"\bpvc", "PVC"), (r"\bcupru\b|\bcopper\b", "copper"), (r"\botel zincat\b|\bzincat|\bzn\b", "galvanised steel"),
    (r"\binox\b|\bstainless", "stainless steel"), (r"\bfonta\b|\bcast iron", "cast iron"), (r"\botel\b|\bsteel\b|\bteava neagra\b|\btevi negre\b", "steel"),
    (r"\bpolipropilen|\bpp\b", "PP"),
]
VALVES = [
    (r"\bsfer", "ball"), (r"\bsertar", "gate"), (r"\bretinere|\bde sens\b|\bnereturn", "check"), (r"\bechilibr|\bbalans", "balancing"),
    (r"\bfluture", "butterfly"), (r"\b3 cai\b|\btrei cai\b", "3-way"), (r"\b2 cai\b|\bdoua cai\b", "2-way"), (r"\btermostat", "thermostatic"),
    (r"\bsiguranta\b", "safety"), (r"\bgolire\b", "drain"), (r"\bsectionare\b", "isolating"), (r"\breglaj\b|\breglare\b", "regulating"),
]
CONNECTIONS = [(r"\bolandez", "union"), (r"\bflans", "flange"), (r"\bfilet", "thread"), (r"\bpresare\b|\bpress\b", "press"),
               (r"\blipire\b", "solder")]
FUELS = [(r"\bgaz|\bgas\b", "gas"), (r"\bpelet", "pellet"), (r"\bmotorin|\boil\b", "oil"), (r"\belectric", "electric"),
         (r"\blemn|\bwood\b", "wood")]
DRINKING = r"\bpotabil|\bapa rece\b|\bapa calda menajer|\bacm\b|\balimentare cu apa\b|\bdrinking"
NOT_DRINKING = r"\bnepotabil|\bcanalizar|\bpluvial|\bincalzir|\bdrenaj|\bincendiu\b|\bhidrant|\bsprinkler|\bracire\b"
NOT_PRODUCER = r"\b(sau|or)\s+(similar|echivalent|equivalent)\b.*|\b(s\.?r\.?l|s\.?a|gmbh|s\.?p\.?a|ltd|inc|ag)\b\.?"


def plain(text):
    """Lower case, no diacritics, single spaces; ș written with a cedilla or a comma both become s."""
    text = re.sub(r"[ØøФфΦφ]", " dia ", str(text or ""))   # the diameter sign, written several ways, kept as a word
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(text.lower().replace("×", "x").split())


def first(rules, text):
    return next((name for rx, name in rules if re.search(rx, text)), None)


def kind_of(text):
    """The kind of product a description is, or None."""
    t = plain(text)
    return first([(rx, k) for k, rx in KINDS], t)


def producer_of(text):
    """A producer as written, without "or similar" and the company form; None when nothing is left."""
    name = re.sub(NOT_PRODUCER, "", plain(text)).strip(" ,.;-/")
    return name or None


def _num(s):
    return s.replace(",", ".")


def cable_parts(t):
    designation = first(CABLES, t)
    if designation is None:   # a data cable: its screen and category
        screen = re.search(r"\b(s/ftp|f/ftp|sf/utp|s/utp|f/utp|sftp|fftp|ftp|utp)\b", t)
        category = re.search(r"\bcat\.?\s*(5e|6a|6|7a|7|8)\b", t)
        if screen or category:
            designation = " ".join(x for x in (screen.group(1).upper() if screen else None,
                                               f"cat {category.group(1)}" if category else None) if x)
    fire = [f"E{m}" for m in re.findall(r"\be\s?(30|60|90)\b", t)] + [f"PH{m}" for m in re.findall(r"\bph\s?(30|60|90|120)\b", t)]
    fire += ["FE180"] if re.search(r"\bfe\s?180\b", t) else []
    cpr = re.search(r"\b(aca|b1ca|b2ca|cca|dca|eca|fca)\b(?:[\s,-]*(s1a|s1b|s1|s2|s3))?(?:[\s,-]*(d0|d1|d2))?(?:[\s,-]*(a1|a2|a3))?", t)
    cpr_class = None
    if cpr:
        cls = cpr.group(1)[0].upper() + cpr.group(1)[1:]
        cpr_class = cls + (f"-{cpr.group(2)}" if cpr.group(2) else "") + "".join(f",{g}" for g in cpr.groups()[2:] if g)
    pairs = re.findall(r"\b(\d{1,3})\s*x\s*(\d{1,2})\s*x\s*(\d+(?:[.,]\d+)?)", t)
    rest = re.sub(r"\b\d{1,3}\s*x\s*\d{1,2}\s*x\s*\d+(?:[.,]\d+)?", " ", t)
    cores = re.findall(r"\b(\d{1,3})\s*x\s*(\d+(?:[.,]\d+)?)\s*(?:mmp|mm2|mm\^2|mm\b|\b)", rest)
    sizes = [f"{a}x{b}x{_num(c)}" for a, b, c in pairs] + [f"{a}x{_num(b)}" for a, b in cores]
    sizes += [f"{n} AWG" for n in re.findall(r"\b(\d{2})\s*awg\b", t)]
    return {"designation": designation, "fire": " ".join(dict.fromkeys(fire)) or None, "cpr": cpr_class, "sizes": sizes}


def diameters(t):
    """The diameters a pipe or valve text gives: a list after "diametru", DN, Ø, or the outer diameter of "20x2.8 mm"."""
    found = []
    listed = re.search(r"\bdiametr\w*\s*:?\s*([\d\s,;./-]+)", t)
    if listed:
        found += [int(n) for n in re.findall(r"\d{1,4}", listed.group(1))]
    found += [int(n) for n in re.findall(r"\b(?:dn|dia)\s*(\d{1,4})", t)]
    found += [int(n) for n in re.findall(r"\b(\d{2,3})\s*x\s*\d+(?:[.,]\d+)?\s*mm\b", t)]
    return [f"{n}" for n in sorted(set(n for n in found if 6 <= n <= 1200))]


def standard_of(t):
    hit = re.search(r"\b(?:sr\s+)?(?:en\s*(?:iso\s*)?|iso\s*|din\s*)\d{3,5}(?:[-:]\d+)*", t)
    return " ".join(hit.group(0).upper().split()) if hit else None


def use_of(t):
    drinking, not_drinking = re.search(DRINKING, t), re.search(NOT_DRINKING, t)
    return "drinking water" if drinking and not not_drinking else "not drinking water" if not_drinking and not drinking else None


def describe(text, producer=None):
    """What a description says about its product line: kind, the identity parts of that kind, its sizes, a key and a
    label. A text whose kind is outside SCOPE comes back with only its kind."""
    t = plain(text)
    kind = kind_of(t)
    out = {"kind": kind, "producer": producer_of(producer) if producer else None, "sizes": []}
    if kind == "cable":
        out.update(cable_parts(t))
        out["standard"] = standard_of(t)
    elif kind == "pipe":
        # PE written alone is the material only in capitals: in lower case "pe" is the Romanian "on"
        material = first(MATERIALS, t) or ("PE" if re.search(r"\bPE\b", str(text)) else None)
        out.update(material=material, pressure=_pn(t), standard=standard_of(t), use=use_of(t), sizes=diameters(t))
    elif kind == "valve":
        out.update(type=first(VALVES, t), connection=first(CONNECTIONS, t), pressure=_pn(t), use=use_of(t), sizes=diameters(t))
    elif kind == "boiler":
        out.update(series=_series(t), fuel=first(FUELS, t),
                   sizes=[f"{_num(p)} kW" for p in re.findall(r"\b(\d+(?:[.,]\d+)?)\s*kw\b", t)])
    if kind in IDENTITY:
        out["key"] = key_of(out)
        out["label"] = label_of(out)
    return out


def _pn(t):
    hit = re.search(r"\bpn\s?(\d+(?:[.,]\d+)?)\b", t)
    return f"PN{_num(hit.group(1))}" if hit else None


def _series(t):
    """A boiler's series: the words of its model name, as "vitodens 200-w"; None when the text names no model."""
    hit = re.search(r"\b([a-z]{4,}(?:\s?[a-z]{2,})?\s\d{2,4}(?:-[a-z]{1,2})?)\b", t)
    return hit.group(1) if hit else None


def key_of(line):
    """The product line's identity as one text: unknown parts are "?"."""
    return "|".join([line["kind"], *(str(line.get(p) or "?") for p in IDENTITY[line["kind"]])])


def label_of(line):
    parts = [line.get(p) for p in IDENTITY[line["kind"]] if p != "producer"]
    name = " ".join(str(p) for p in parts if p) or line["kind"]
    return f"{name} · {line['producer']}" if line.get("producer") else name


def same_line(a, b):
    """"same" when every identity part is known on both and equal, "near" when the known ones agree and some part is
    unknown, None when a known part differs or the kinds differ."""
    if a.get("kind") != b.get("kind") or a.get("kind") not in IDENTITY:
        return None
    main = MAIN[a["kind"]]
    if not a.get(main) or not b.get(main):
        return None
    unknown = False
    for part in IDENTITY[a["kind"]]:
        x, y = a.get(part), b.get(part)
        if x is None or y is None:
            unknown = True
        elif str(x).lower() != str(y).lower():
            return None
    return "near" if unknown else "same"


def covers(line, asked):
    """Whether a product line covers what a BOQ line asks for: the same kind, the same identity parts where both
    are known (the producer aside: a BOQ names one "or similar"), and the size within the line's range. "covers",
    "near" when a part or the size is unknown on one side, None when something differs."""
    if line.get("kind") != asked.get("kind") or line.get("kind") not in IDENTITY:
        return None
    main = MAIN[line["kind"]]
    if not line.get(main) or not asked.get(main):
        return None
    unknown = False
    for part in IDENTITY[line["kind"]]:
        if part == "producer":
            continue
        x, y = line.get(part), asked.get(part)
        if x is None or y is None:
            unknown = unknown or y is not None or x is not None
        elif str(x).lower() != str(y).lower():
            return None
    if asked.get("sizes") and line.get("sizes"):
        if not set(asked["sizes"]) <= set(line["sizes"]):
            return None
    elif asked.get("sizes") or line.get("sizes"):
        unknown = True
    return "near" if unknown else "covers"
