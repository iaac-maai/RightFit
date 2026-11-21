"""RightFit's MCP server: what an agent sees and gets back, through the same client code an agent uses."""
import json
import sys
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters

from app.mcp_server import MODEL, RAW, server
from app.review_server import boq_links, review
from checks.maf.rules import load
from ingest import rule_watch
from model.page_classifier import CLASSES
from model.train_pages import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ["classify_pages", "compare_revisions", "list_packages", "list_rules", "review_package", "watch_rules"]


def call(tool, **args):
    """Call one tool in memory and return (is_error, text)."""
    async def go():
        async with Client(server) as client:
            r = await client.call_tool(tool, args)
            return r.is_error, r.content[0].text
    return anyio.run(go)


def test_the_agent_sees_six_tools_and_all_of_them_only_read():
    async def go():
        async with Client(server) as client:
            return (await client.list_tools()).tools
    tools = anyio.run(go)
    assert sorted(t.name for t in tools) == TOOLS
    assert all(t.annotations.read_only_hint for t in tools)


def test_review_package_gives_the_review_page_answer():
    error, text = call("review_package", package="P02")
    got = json.loads(text)
    pkg = json.loads((ROOT / "data/maf/extracted/P02.json").read_text())
    page = review(pkg, boq=boq_links(pkg, read=False))   # the tool, like the page, uses the BOQ lines already read
    assert not error
    assert got["draft_answer"]["letter"] == page["status"]["letter"] == "B"
    assert got["answer_text"] == page["answer"]["text"]
    assert len(got["problems"]) == page["counts"]["problems"] and len(got["questions"]) == page["counts"]["questions"]


def test_the_review_stays_short_enough_for_an_agent():
    # Agents warn on tool answers above about 10,000 tokens; P01 has the most results.
    error, text = call("review_package", package="P01")
    assert not error and len(text) < 40_000


def test_names_from_the_agent_cannot_reach_other_files():
    for bad in ("../P01", "P01.json", "/etc/passwd", "P99"):
        error, text = call("review_package", package=bad)
        assert error and "No readings" in text
    assert call("classify_pages", package="../data")[0]


def test_a_wrong_location_or_date_is_refused():
    assert call("review_package", package="P01", location="FR")[0]
    assert call("review_package", package="P01", review_date="12.11.2026")[0]


def test_rules_for_romania_leave_out_spain():
    error, text = call("list_rules", location="RO")
    rules = json.loads(text)["rules"]
    assert not error and rules and {r["jurisdiction"] for r in rules} <= {"EU", "RO", "ANY"}
    # A repealed rule says until when it applied, so an agent does not cite it for a later review.
    assert next(r for r in rules if r["rule_id"] == "RO-L10-11-3")["valid_to"] == "2026-08-24"


def test_watch_rules_answers_for_every_legal_rule_and_changes_none(monkeypatch):
    def offline(act):
        raise OSError("offline")
    monkeypatch.setattr(rule_watch, "ask", offline)   # no network in tests
    table = ROOT / "data/maf/rules.csv"
    before = table.read_bytes()
    error, text = call("watch_rules")
    got = json.loads(text)["rules"]
    assert not error
    assert [r["rule_id"] for r in got] == [r["rule_id"] for r in load("rules.csv") if r["status"] not in rule_watch.NOT_LAW]
    assert {r["result"] for r in got} == {"not_checked"}   # with no answer, nothing is called unchanged
    assert table.read_bytes() == before


@pytest.mark.skipif(not (RAW / "P02").is_dir() or not (RAW / "P10").is_dir(),
                    reason="the packages stay on Luca's laptop")
def test_compare_revisions_finds_revision_3_of_p02_and_lists_every_file():
    error, text = call("compare_revisions", package="P02")
    got = json.loads(text)
    assert not error and (got["form"], got["revision"], got["previous_package"], got["previous_revision"]) == ("IV 004", 4, "P10", 3)
    statuses = {a["status"] for a in got["attachments"]}
    assert statuses <= {"unchanged", "changed", "new", "removed"} and "unchanged" in statuses
    assert call("compare_revisions", package="../P02")[0]          # a name from the agent cannot leave data/raw


def test_classify_pages_loads_the_model_train_pages_writes():
    # Version 2, not version 1 (page_classifier.joblib). The server keeps its own copy of the path because importing
    # model.train_pages loads scikit-learn, which takes seconds, and an agent gives up on a server that is slow to start.
    assert MODEL == MODEL_PATH


@pytest.mark.skipif(not (RAW / "P01").is_dir() or not MODEL.exists(),
                    reason="the packages and the model stay on Luca's laptop")
def test_classify_pages_labels_every_page_of_p01():
    error, text = call("classify_pages", package="P01")
    got = json.loads(text)
    assert not error and got["pages"] and not got["not_read"]
    assert all(p["classifier"] in CLASSES and p["keywords"] in CLASSES for p in got["pages"])


def test_an_agent_can_start_the_server_the_way_mcp_json_says():
    # Over standard input and output, as a real agent runs it: nothing but MCP messages may reach stdout.
    entry = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["rightfit"]
    params = StdioServerParameters(command=sys.executable, args=entry["args"], cwd=ROOT)   # the Python running the tests

    async def go():
        async with Client(params) as client:
            return sorted(t.name for t in (await client.list_tools()).tools)
    assert anyio.run(go) == TOOLS
