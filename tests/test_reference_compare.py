from eval.reference_answers.compare import compare, reference_letter


def test_reference_letter_reads_the_status_line():
    assert reference_letter("- Status Luca would give: Approved (A).") == "A"
    assert reference_letter("no status here") is None


def test_compare_runs_on_both_reference_packages():
    for package in ("P01", "P02"):
        row = compare(package)
        assert row["reference"] in "ABC" and row["draft"] in "ABC"
        assert row["values"]["verified"] > 0
