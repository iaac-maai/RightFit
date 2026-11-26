"""The knowledge graph (spec/features/knowledge_graph.md, MAF-36): the product lines of the kinds in SCOPE, the forms
that submitted them and the answers they got, the documents that came with them, and the BOQ lines they cover.

Built on the laptop with no AI and no cost, from the forms of the project in use (ingest/maf_form.py), the register
of the previous project (its description, brand and status columns only: no comments, no names), the BOQ lines
(ingest/boq.py, never the prices) and a fingerprint of every file. web/scripts/import_project.py sends it online,
where admins who are members of the project see it drawn on the Inside RightFit page.
"""
import hashlib
import re
from pathlib import Path

from ingest.boq import read_boq
from ingest.maf_form import read_form
from ingest.products import IDENTITY, SCOPE, covers, describe, plain, same_line

FORM_FILE = re.compile(r"\.xlsx?$", re.I)
DOC_KINDS = [   # what a file is, from its name only: a hint for the drawing, never used by a check
    (r"declarati|\bdop\b|declaration|\bdc\b", "declaration"), (r"agrement|\baviz|\bat\b", "technical approval"),
    (r"certificat|certificate|\bvde\b", "certificate"), (r"fisa|datasheet|data sheet|catalog|\btds\b|tehnic", "data sheet"),
    (r"manual|instructiun", "manual"),
]


def fingerprint(path):
    """The first 16 characters of the file's SHA-256: the same file in two packages has the same one."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()[:16]


def doc_kind(name):
    t = plain(name)
    return next((k for rx, k in DOC_KINDS if re.search(rx, t)), "other")


class Graph:
    def __init__(self):
        self.nodes, self.edges, self.lines = {}, [], {}   # lines: product line id -> what is known about it

    def node(self, nid, **attrs):
        self.nodes.setdefault(nid, {"id": nid, **attrs})
        return nid

    def line(self, info):
        """The product line a description belongs to; the same key is one line, its sizes are the union of all."""
        nid = f"line:{info['key']}"
        known = self.lines.setdefault(nid, {**{p: info.get(p) for p in ("kind", *IDENTITY[info["kind"]])}, "sizes": set()})
        known["sizes"] |= set(info["sizes"])
        self.node(nid, type="product_line", kind=info["kind"], label=info["label"],
                  parts={p: info.get(p) for p in IDENTITY[info["kind"]]})
        return nid

    def edge(self, a, b, kind, **attrs):
        self.edges.append({"from": a, "to": b, "type": kind, **attrs})

    def result(self):
        for nid, known in self.lines.items():
            self.nodes[nid]["sizes"] = sorted(known["sizes"], key=_size_order)
        lines = [n for n in self.nodes.values() if n["type"] == "product_line"]
        projects = {nid: {self.nodes[e["from"]]["project"] for e in self.edges if e["to"] == nid and e["type"] == "submits"}
                    for nid in self.lines}
        for n in lines:
            n["projects"] = sorted(projects[n["id"]])
        summary = {
            "product_lines": {k: sum(1 for n in lines if n["kind"] == k) for k in SCOPE},
            "forms": sum(1 for n in self.nodes.values() if n["type"] == "form"),
            "documents": sum(1 for n in self.nodes.values() if n["type"] == "document"),
            "boq_lines": sum(1 for n in self.nodes.values() if n["type"] == "boq_line"),
            "came_back": sum(1 for n in lines if len(n["projects"]) > 1),
            "near": sum(1 for e in self.edges if e["type"] == "near"),
        }
        return {"nodes": list(self.nodes.values()), "edges": self.edges, "summary": summary}


def _size_order(size):
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", size)]
    return (len(numbers), numbers)


def add_forms(g, originals, project="this project"):
    """Every package folder of the project: its form's product rows of the kinds in SCOPE, and its files."""
    for folder in sorted(p for p in Path(originals).glob("P*") if p.is_dir() and re.fullmatch(r"P\d+", p.name)):
        form_file = next((f for f in sorted(folder.iterdir()) if FORM_FILE.search(f.name) and not f.name.startswith("~$")), None)
        if form_file is None:
            continue
        try:
            form = read_form(form_file)
        except Exception:   # a form this reader cannot open yet (P07: its date is a number) is left out, not guessed
            continue
        lines = []
        for item in form.get("items_raw", []):
            info = describe(f"{item.get('name', '')} {item.get('model', '')}", item.get("brand"))
            if info["kind"] in SCOPE:
                lines.append((g.line(info), info["sizes"]))
        if not lines:
            continue
        fid = g.node(f"form:{project}:{folder.name}", type="form", project=project, package=folder.name,
                     label=f"{form['form_no']} rev {form['revision']}")
        for lid, sizes in lines:
            g.edge(fid, lid, "submits", sizes=sizes)
        for f in sorted(folder.iterdir()):
            if f.is_file() and not f.name.startswith(".") and f != form_file:
                did = g.node(f"doc:{fingerprint(f)}", type="document", label=f.name, kind=doc_kind(f.name))
                g.edge(did, fid, "in")
                for lid, _ in lines:
                    g.edge(did, lid, "supports")


def add_register(g, path, project="earlier project"):
    """The register of the previous project: description, brand and status of each form. The comments and the
    parties' columns are never read, so no name gets in."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(max_row=2000, values_only=True))   # the sheet claims 300,000 rows, most empty
    hi = next(i for i, r in enumerate(rows) if sum(1 for c in r if c) >= 5)
    head = [str(c).strip().lower() if c else "" for c in rows[hi]]
    col = {name: head.index(name) for name in ("maf no.", "rev.", "equipment or material description", "brand", "status")}
    for n, r in enumerate(rows[hi + 1:], hi + 2):
        if not r or not r[col["equipment or material description"]]:
            continue
        info = describe(str(r[col["equipment or material description"]]), str(r[col["brand"]] or ""))
        if info["kind"] not in SCOPE:
            continue
        status = str(r[col["status"]] or "").strip().upper()[:1] or None
        no, rev = r[col["maf no."]], r[col["rev."]]
        fid = g.node(f"form:{project}:{no if no is not None else f'row {n}'}:{rev}", type="form", project=project,
                     label=f"MAF {no} rev {rev}" if no is not None else f"MAF without number, rev {rev}",
                     answer=status if status in ("A", "B", "C") else None)
        g.edge(fid, g.line(info), "submits", sizes=info["sizes"])


def add_boq(g, boq_files):
    """The BOQ lines of the kinds in SCOPE that say enough to be matched, each linked to the product lines that cover
    it ("covers") or might ("near")."""
    for n, path in enumerate(boq_files, 1):
        for ln in read_boq(path):
            asked = describe(str(ln["text"]), str(ln["producer"] or ""))
            if asked["kind"] not in SCOPE or not any(asked.get(p) for p in IDENTITY[asked["kind"]] if p != "producer"):
                continue
            bid = g.node(f"boq:{n}:{ln['sheet']}:{ln['row']}", type="boq_line", kind=asked["kind"], sheet=ln["sheet"],
                         row=ln["row"], sizes=asked["sizes"], label=" ".join(str(ln["text"]).split())[:90])
            for lid, known in g.lines.items():
                hit = covers(known, asked)
                if hit:
                    g.edge(lid, bid, hit)


def add_near(g):
    """Product lines that might be one, a known part missing on one side: a question for a person, never a merge."""
    ids = sorted(g.lines)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if same_line(g.lines[a], g.lines[b]) == "near":
                g.edge(a, b, "near")


def build(originals, register=None, boq_files=()):
    g = Graph()
    add_forms(g, originals)
    if register and Path(register).exists():
        add_register(g, register)
    add_near(g)
    add_boq(g, boq_files)
    return g.result()
