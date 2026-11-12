"""Draft MAF comments, one sentence per flag or unclear, filled from templates (spec section 8).

Values come only from the check results. A language model may rephrase these sentences, never add values.
"""

DOC_NAMES = {"data_sheet": "data sheet", "eu_declaration_of_conformity": "EU declaration of conformity",
             "declaration_of_performance": "declaration of performance", "product_certificate": "product certificate",
             "other_certificate": "another certificate", "selection_report": "selection report",
             "drinking_water_approval": "approval for contact with drinking water"}

TEMPLATES = {
    "D1.missing": "The {doc} for {item} is missing; please attach it.",
    "D1.published": "The {doc} for {item} is missing; the manufacturer publishes it in {where} ({url}), "
                    "please attach it.",
    "D2.no_match": "The declaration of conformity attached for {covers} matches no product in the MAF; "
                   "please attach the declarations for {items}.",
    "D2.extra": "The declaration of conformity attached for {covers} matches no product in the MAF; "
                "please check the attachment.",
    "D3.expired": "{file} expired on {date}; please send the current version.",
    "D3.renew": "{file} is valid until {date}, before delivery; please send the renewed version at delivery.",
    "D4.not_found": "The attachment '{label}' listed in the form is not in the package; please attach it.",
    "D4.type": "The attachment '{label}' ({file}) is in fact {doc}; please attach the document announced.",
    "V1.below": "The duty point in the data sheet for {item} does not reach the MAF requirement: {got}.",
    "V1.missing": "Please show the duty point for {item} in the data sheet.",
    "V2.below": "The maximum working pressure of {item} ({got}) is below the required {req}.",
    "V2.missing": "Please state the maximum working pressure of {item}.",
    "V3.outside": "The liquid temperature range of {item} ({got}) does not reach the {req} required.",
    "V3.missing": "Please state the liquid temperature range of {item}.",
    "H1.missing": "Please attach the document that approves {item} for contact with drinking water.",
    "E1.hrs": "The heat recovery efficiency of {item} ({got} %) is below the {req} % minimum of "
              "Regulation (EU) 1253/2014.",
    "E1.sfp": "SFPint of {item} ({got}) exceeds SFPint_limit ({req}).",
    "E1.filter": "Please confirm the filter warning for {item}.",
    "E1.missing": "Please state the {what} of {item}.",
    "C.CL-01": "The data sheet for {item} does not show the exact model; please mark the model offered.",
    "C.CL-03": "Please state in the MAF where {item} is used.",
    "C.CL-04": "Please confirm that every component of the BOQ line for {item} is submitted, accessories included.",
    "C.CL-08": "Please confirm that BMS communication for {item} is included in the supply, not optional.",
    "C.CL-12": "Please complete the electrical data for {item}: {missing}.",
    "P.rule": "The consultant asks for {item}: {text}.",
    "Q.rule": "The {where} asks for {item}: {text}; please show it in the submittal.",
    "Q.none": "Please give the BOQ position that {item} answers.",
}

# A short heading for each comment, so a list of findings can be read at a glance.
TITLES = {
    "D1.missing": "No {doc}", "D1.published": "No {doc}",
    "D2.no_match": "Declaration names other products", "D2.extra": "Declaration names other products",
    "D3.expired": "Certificate has expired", "D3.renew": "Certificate runs out before delivery",
    "D4.not_found": "Listed attachment is missing", "D4.type": "Attachment is not what the form says",
    "V1.below": "Duty point not reached", "V1.missing": "Duty point not shown",
    "V2.below": "Working pressure too low", "V2.missing": "Working pressure not stated",
    "V3.outside": "Liquid temperature outside the project range", "V3.missing": "Liquid temperature range not stated",
    "H1.missing": "No approval for drinking water",
    "E1.hrs": "Heat recovery below the minimum", "E1.sfp": "SFPint above the limit",
    "E1.filter": "Filter warning not confirmed", "E1.missing": "{What} not stated",
    "C.CL-01": "Exact model not marked on the data sheet", "C.CL-03": "Where it is used is not stated",
    "C.CL-04": "BOQ components not confirmed", "C.CL-08": "BMS not shown as included",
    "P.rule": "Consultant's rule: {text}",
    "Q.rule": "BOQ asks: {text}", "Q.none": "No BOQ line found", "Q.unread": "BOQ line not read yet",
    "C.CL-12": "{Missing} not stated",
}


def readable(params):
    """The values of a check result in the words a sentence needs: 'starting_method' becomes 'starting method'."""
    out = dict(params)
    if "doc_type" in out:
        out["doc"] = DOC_NAMES.get(out["doc_type"], out["doc_type"])
    if "missing" in out:
        out["missing"] = out["missing"].replace("_", " ")
        out["Missing"] = out["missing"].capitalize()
    if "what" in out:
        out["What"] = str(out["what"]).capitalize()
    return out


def open_verdict(r):
    """True when a result needs a comment: a result unclear only because nobody verified it counts as what it would be."""
    return (r["would_be"] if r["result"] == "unclear" else r["result"]) in ("flag", "unclear")


def title(r):
    """The short heading of one check result, or None when it has no comment to head."""
    template = TITLES.get(r["code"])
    return template.format(**readable(r["params"])) if template and open_verdict(r) else None


def comment(r):
    """The draft comment for one check result, or None when it needs none.

    A result that is unclear only because nobody verified its values yet is commented as what it would be:
    the reviewer verifies before sending, and a would-be pass needs no comment.
    """
    template = TEMPLATES.get(r["code"])
    if not open_verdict(r) or not template:
        return None
    return template.format(**readable(r["params"]))
