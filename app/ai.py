"""The AI the application asks, through the Claude command line on this laptop. Every answer is labelled AI output.

Two uses: turning a rule the consultant types in words into a row (they save it or not), and listing what a BOQ
line asks for (cached, and only an input to the checks, which stay deterministic).
"""
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

PROMPTS = Path(__file__).resolve().parents[1] / "ingest" / "prompts"
MODEL = "haiku"   # short structured answers; a bigger model only if these turn out wrong
NO_TOOLS = "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,NotebookEdit,Task,Agent"
TEXT = {"type": "string"}
RULE = {"type": "object", "required": ["family", "application", "kind", "field", "operator", "value", "unit", "effect", "text"],
        "properties": {"family": TEXT, "application": TEXT, "field": TEXT, "value": TEXT, "unit": TEXT, "text": TEXT,
                       "kind": {"enum": ["brand", "value", "document", "included", "reminder"]},
                       "operator": {"enum": ["", ">=", "<=", "="]}, "effect": {"enum": ["B", "C", "info"]}}}
ASKS = {"type": "object", "required": ["requirements"], "properties": {"requirements": {"type": "array", "items": {
    "type": "object", "required": ["text", "kind", "field", "operator", "value", "unit", "quote"],
    "properties": {"text": TEXT, "field": TEXT, "value": TEXT, "unit": TEXT, "quote": TEXT,
                   "kind": {"enum": ["brand", "value", "included", "reminder"]}, "operator": {"enum": ["", ">=", "<=", "="]}}}}}}


def ask(prompt_file, text, schema, context=""):
    """One structured answer from Claude, with no tools and no memory. Raises RuntimeError when it can't answer."""
    claude = shutil.which("claude") or str(Path.home() / ".local/bin/claude")
    if not Path(claude).exists():
        raise RuntimeError("The AI is not set up on this laptop (no Claude command line); fill in the rule by hand.")
    system = (PROMPTS / prompt_file).read_text() + (f"\n\n{context}" if context else "")
    with tempfile.TemporaryDirectory() as cwd:   # an empty folder, so no project instructions are read
        run = subprocess.run([claude, "-p", "--model", MODEL, "--output-format", "json", "--json-schema", json.dumps(schema),
                              "--no-session-persistence", "--strict-mcp-config", "--disallowedTools", NO_TOOLS,
                              "--system-prompt", system], input=text, capture_output=True, text=True, timeout=120, cwd=cwd)
    try:
        answer = json.loads(run.stdout)
    except ValueError:
        raise RuntimeError("The AI did not answer; try again or fill in the rule by hand.") from None
    if answer.get("is_error") or not answer.get("structured_output"):
        raise RuntimeError("The AI could not answer; try again or fill in the rule by hand.")
    return answer["structured_output"], next(iter(answer.get("modelUsage") or {}), MODEL)


def rule_from_words(words, families, readings, doc_types):
    context = (f"Families: {', '.join(families)}.\nReadings: {', '.join(readings)}.\n"
               f"Document types: {', '.join(doc_types)}.")
    rule, model = ask("rule_from_words.md", words, RULE, context)
    return {**rule, "source": f"typed by the consultant, turned into a rule by AI ({model})"}


def boq_requirements(texts, readings, cache_file, read=True):
    """What each BOQ line asks for, by line text: from the cache or, when read is True, from the AI (in parallel,
    then cached). A line not read yet is missing from the answer."""
    from concurrent.futures import ThreadPoolExecutor
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    key = lambda s: hashlib.sha1(s.encode()).hexdigest()  # noqa: E731
    todo = [s for s in dict.fromkeys(texts) if key(s) not in cache] if read else []
    if todo:
        context = f"Readings: {', '.join(readings)}."
        with ThreadPoolExecutor(4) as pool:
            answers = list(pool.map(lambda s: ask("boq_requirements.md", s, ASKS, context), todo))
        for s, (asks, model) in zip(todo, answers):
            cache[key(s)] = {"requirements": asks["requirements"], "read_by": model, "read_on": date.today().isoformat()}
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return {s: cache[key(s)] for s in texts if key(s) in cache}
