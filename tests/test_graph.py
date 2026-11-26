"""The knowledge graph built from a made-up register (ingest/graph.py). No real company, project or person name."""
import openpyxl

from ingest.graph import Graph, add_register


def _register(path, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["MAF No.", "Rev.", "Equipment or material description", "BRAND", "Status", "Comments"])
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_the_register_gives_forms_answers_and_one_product_line_but_never_its_comments(tmp_path):
    path = tmp_path / "register.xlsx"
    _register(path, [
        [12, 0, "Teava PP-R PN20 SR EN ISO 15874-2 apa rece, diametrul 20, 25", "Tubex", "B", "J. Doe asks for the DoP"],
        [None, 1, "Teava PP-R PN20 SR EN ISO 15874-2 apa rece, diametrul 32", "Tubex S.R.L.", "A", ""],
        [13, 0, "Pompa de drenaj", "Pumpex", "A", ""],   # a pump: outside the graph
    ])
    g = Graph()
    add_register(g, path)
    r = g.result()
    forms = {n["label"]: n["answer"] for n in r["nodes"] if n["type"] == "form"}
    assert forms == {"MAF 12 rev 0": "B", "MAF without number, rev 1": "A"}
    lines = [n for n in r["nodes"] if n["type"] == "product_line"]
    assert len(lines) == 1 and lines[0]["sizes"] == ["20", "25", "32"]   # one product line, the range of both forms
    assert r["summary"]["product_lines"]["pipe"] == 1 and r["summary"]["came_back"] == 0
    assert "Doe" not in str(r)   # the comments column is never read
