"""The labels of the second batch come from fixed rules on file names and forms, and the split never leaks a document."""
from model.batch2 import label_files, split, stated_type


def test_a_name_states_one_type():
    assert stated_type("Fisa tehnica pompa.pdf") == "data_sheet"
    assert stated_type("16. F.T. Panou.pdf") == "data_sheet"
    assert stated_type("DoP_produs_ro.pdf") == "declaration"
    assert stated_type("Declaratie conformitate.pdf") == "declaration"
    assert stated_type("CE KP100.pdf") == "declaration"
    assert stated_type("Certificat de conformitate X100.pdf") == "certificate"
    assert stated_type("Aviz si agrement rezervoare.pdf") == "certificate"
    assert stated_type("MANUAL INSTALARE.pdf") == "manual"


def test_a_name_with_no_type_or_two_types_states_none():
    assert stated_type("4099854102578_ro.pdf") is None
    assert stated_type("Certificate+Declaratii in EN.pdf") is None
    # DC in the middle of a name is direct current or a code, not a declaration of conformity
    assert stated_type("Cablu DC solar.pdf") is None


def test_the_form_labels_a_silent_file_only_when_its_page_count_is_unique():
    attached = [("Fisa tehnica", 14), ("DOP- Declaratie de performanta", 3)]
    files = [("Product.pdf", 14), ("DoP.pdf", 3)]
    assert label_files(files, attached) == {"Product.pdf": ("data_sheet", "form"), "DoP.pdf": ("declaration", "name")}
    # two silent files of 3 pages, and one form line of 3 pages: no way to tell which one it means
    assert label_files([("a.pdf", 3), ("b.pdf", 3)], [("Certificat", 3)]) == {}


def test_a_name_and_a_form_that_disagree_give_no_label():
    assert label_files([("Fisa tehnica.pdf", 2)], [("Declaratie", 2)]) == {}


def row(code, sha, discipline="plumbing"):
    return {"code": code, "sha": sha, "discipline": discipline}


def test_maf_codes_that_share_a_file_stay_on_one_side():
    rows = [row(f"IS {n}", f"file{n}") for n in range(8)] + [row("IS 0", "shared"), row("IS 7", "shared")]
    sides = split(rows)
    assert sides["IS 0"] == sides["IS 7"]


def test_a_quarter_of_each_discipline_goes_to_the_test_and_the_split_repeats():
    rows = [row(f"IS {n}", f"a{n}") for n in range(8)] + [row(f"ICS {n}", f"b{n}", "low current") for n in range(12)]
    sides = split(rows)
    assert sum(sides[f"IS {n}"][0] == "test" for n in range(8)) == 2
    assert sum(sides[f"ICS {n}"][0] == "test" for n in range(12)) == 3
    assert split(rows) == sides


def test_a_discipline_with_one_maf_stays_in_training():
    assert split([row("IT 1", "x", "heating")])["IT 1"][0] == "train"
