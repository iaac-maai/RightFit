"""Draft MAF status from the check results (spec section 7). Written rules, not a model; the reviewer decides."""

LABELS = {"A": "Approved", "B": "Approved as noted", "C": "Revise and resubmit"}


def draft_status(results, key="result", accepted=()):
    """Return (letter, reasons). key='would_be' gives the status once the extracted values are confirmed.

    C: a blocking result flags (no data sheet naming the model, or a blocking checklist item missing).
    B: no C, but at least one flag or unclear, or an AI suggestion the reviewer added to the answer.
    A: everything pass or info.
    accepted: titles of the AI suggestions the reviewer added; they are the reviewer's notes now.
    """
    blocking = [r for r in results if r["blocking"] and r[key] == "flag"]
    if blocking:
        return "C", [f"{r['check']}: {r['reason']}" for r in blocking]
    open_ = [f"{r['check']}: {r['reason']}" for r in results if r[key] in ("flag", "unclear")]
    open_ += [f"AI suggestion added to the answer: {title}" for title in accepted]
    if open_:
        return "B", open_
    return "A", ["every check is pass or info"]
