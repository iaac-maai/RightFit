"""Draft MAF comments, one sentence per flag or unclear, filled from templates (spec section 8).

Values come only from the check results. A language model may rephrase these sentences, never add values.
"""

DOC_NAMES = {
    "ro": {"data_sheet": "fișa tehnică", "eu_declaration_of_conformity": "declarația de conformitate UE",
           "declaration_of_performance": "declarația de performanță", "product_certificate": "certificatul de produs",
           "other_certificate": "un alt certificat", "selection_report": "raportul de selecție"},
    "en": {"data_sheet": "data sheet", "eu_declaration_of_conformity": "EU declaration of conformity",
           "declaration_of_performance": "declaration of performance", "product_certificate": "product certificate",
           "other_certificate": "another certificate", "selection_report": "selection report"},
}

TEMPLATES = {
    "D1.missing": {
        "ro": "Lipsește {doc} pentru {item}; vă rugăm atașați documentul.",
        "en": "The {doc} for {item} is missing; please attach it."},
    "D2.no_match": {
        "ro": "Declarația de conformitate atașată pentru {covers} nu corespunde niciunui produs din MAF; "
              "vă rugăm atașați declarațiile pentru {items}.",
        "en": "The declaration of conformity attached for {covers} matches no product in the MAF; "
              "please attach the declarations for {items}."},
    "D2.extra": {
        "ro": "Declarația de conformitate atașată pentru {covers} nu corespunde niciunui produs din MAF; "
              "vă rugăm verificați atașamentul.",
        "en": "The declaration of conformity attached for {covers} matches no product in the MAF; "
              "please check the attachment."},
    "D3.expired": {
        "ro": "Documentul {file} a expirat la {date}; vă rugăm transmiteți versiunea în vigoare.",
        "en": "{file} expired on {date}; please send the current version."},
    "D3.renew": {
        "ro": "Documentul {file} este valabil până la {date}, înainte de livrare; vă rugăm transmiteți la livrare "
              "versiunea reînnoită.",
        "en": "{file} is valid until {date}, before delivery; please send the renewed version at delivery."},
    "D4.not_found": {
        "ro": "Atașamentul „{label}” din formular nu se regăsește în pachet; vă rugăm atașați-l.",
        "en": "The attachment '{label}' listed in the form is not in the package; please attach it."},
    "D4.type": {
        "ro": "Atașamentul „{label}” ({file}) este de fapt {doc}; vă rugăm atașați documentul anunțat.",
        "en": "The attachment '{label}' ({file}) is in fact {doc}; please attach the document announced."},
    "V1.below": {
        "ro": "Punctul de funcționare din fișa tehnică pentru {item} nu atinge cerința din MAF: {got}.",
        "en": "The duty point in the data sheet for {item} does not reach the MAF requirement: {got}."},
    "V1.missing": {
        "ro": "Vă rugăm indicați în fișa tehnică punctul de funcționare pentru {item}.",
        "en": "Please show the duty point for {item} in the data sheet."},
    "V2.below": {
        "ro": "Presiunea maximă de lucru pentru {item} ({got}) este sub cea cerută ({req}).",
        "en": "The maximum working pressure of {item} ({got}) is below the required {req}."},
    "V2.missing": {
        "ro": "Vă rugăm indicați presiunea maximă de lucru pentru {item}.",
        "en": "Please state the maximum working pressure of {item}."},
    "E1.hrs": {
        "ro": "Randamentul recuperatorului de căldură pentru {item} ({got} %) este sub minimul de {req} % din "
              "Regulamentul (UE) 1253/2014.",
        "en": "The heat recovery efficiency of {item} ({got} %) is below the {req} % minimum of "
              "Regulation (EU) 1253/2014."},
    "E1.sfp": {
        "ro": "SFPint pentru {item} ({got}) depășește SFPint_limit ({req}).",
        "en": "SFPint of {item} ({got}) exceeds SFPint_limit ({req})."},
    "E1.filter": {
        "ro": "Vă rugăm confirmați semnalizarea colmatării filtrelor pentru {item}.",
        "en": "Please confirm the filter warning for {item}."},
    "E1.missing": {
        "ro": "Vă rugăm indicați {what} pentru {item}.",
        "en": "Please state the {what} of {item}."},
    "C.CL-01": {
        "ro": "Fișa tehnică pentru {item} nu indică modelul exact; vă rugăm marcați modelul ofertat.",
        "en": "The data sheet for {item} does not show the exact model; please mark the model offered."},
    "C.CL-03": {
        "ro": "Vă rugăm precizați în MAF unde se folosește {item}.",
        "en": "Please state in the MAF where {item} is used."},
    "C.CL-04": {
        "ro": "Vă rugăm confirmați că sunt transmise toate componentele poziției din BOQ pentru {item}, inclusiv "
              "accesoriile.",
        "en": "Please confirm that every component of the BOQ line for {item} is submitted, accessories included."},
    "C.CL-08": {
        "ro": "Vă rugăm confirmați că pentru {item} comunicația cu BMS este inclusă în livrare, nu opțională.",
        "en": "Please confirm that BMS communication for {item} is included in the supply, not optional."},
    "C.CL-09": {
        "ro": "Vă rugăm precizați tabloul de comandă pentru {item} sau confirmați că nu este necesar.",
        "en": "Please state the control panel for {item}, or confirm that none is needed."},
    "C.CL-12": {
        "ro": "Vă rugăm completați datele electrice pentru {item}: {missing}.",
        "en": "Please complete the electrical data for {item}: {missing}."},
}


def comment(r, lang="ro"):
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
        params["doc"] = DOC_NAMES[lang].get(params["doc_type"], params["doc_type"])
    return template[lang].format(**params)
