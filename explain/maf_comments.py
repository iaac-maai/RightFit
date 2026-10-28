"""Draft MAF comments, one sentence per flag or unclear, filled from templates (spec section 8).

Values come only from the check results. A language model may rephrase these sentences, never add values.
"""

DOC_NAMES = {"data_sheet": "data sheet", "eu_declaration_of_conformity": "EU declaration of conformity",
             "declaration_of_performance": "declaration of performance", "product_certificate": "product certificate",
             "other_certificate": "another certificate", "selection_report": "selection report"}

TEMPLATES = {
    "D1.missing": "The {doc} for {item} is missing; please attach it.",
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
    "E1.hrs": "The heat recovery efficiency of {item} ({got} %) is below the {req} % minimum of "
              "Regulation (EU) 1253/2014.",
    "E1.sfp": "SFPint of {item} ({got}) exceeds SFPint_limit ({req}).",
    "E1.filter": "Please confirm the filter warning for {item}.",
    "E1.missing": "Please state the {what} of {item}.",
    "C.CL-01": "The data sheet for {item} does not show the exact model; please mark the model offered.",
    "C.CL-03": "Please state in the MAF where {item} is used.",
    "C.CL-04": "Please confirm that every component of the BOQ line for {item} is submitted, accessories included.",
    "C.CL-08": "Please confirm that BMS communication for {item} is included in the supply, not optional.",
    "C.CL-09": "Please add the control panel for {item}.",
    "C.CL-09.float": "Please add the float switch (or a control panel) for {item}.",
    "C.CL-12": "Please complete the electrical data for {item}: {missing}.",
}


def comment(r):
    """The draft comment for one check result, or None when it needs none.

    A result that is unclear only because nobody verified its values yet is commented as what it would be:
    the reviewer verifies before sending, and a would-be pass needs no comment.
    """
    verdict = r["would_be"] if r["result"] == "unclear" else r["result"]
    template = TEMPLATES.get(r["code"])
    if verdict not in ("flag", "unclear") or not template:
        return None
    params = dict(r["params"])
    if "doc_type" in params:
        params["doc"] = DOC_NAMES.get(params["doc_type"], params["doc_type"])
    return template.format(**params)
