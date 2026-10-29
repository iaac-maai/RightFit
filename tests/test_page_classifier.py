"""The page classifier: the keyword baseline and a model trained on toy pages."""
from model.page_classifier import build_model, keyword_baseline, normalize, predict

DECLARATION = "EU declaration of conformity. We, Grundfos, declare under our sole responsibility that the products " \
              "comply with the Machinery Directive 2006/42/EC and the Low Voltage Directive 2014/35/EU."
DATA_SHEET = "Nr. Produs: 99478794. Debitul curent calculat: 38.13 m³/h. Înălţimea de pompare: 15.11 m. " \
             "Putere nominală P2: 3 kW. Tensiune nominală: 3 x 380-415 V. Metodă de pornire: DOL."
MANUAL = "Installation and operating instructions. Before installation, read this document. Install the pump " \
         "on a level surface and connect the pipes. Switch off the power supply before any work on the pump."


def test_normalize_removes_diacritics_and_case():
    assert normalize("Declaraţie  de CONFORMITATE") == "declaratie de conformitate"


def test_keyword_baseline_reads_the_page_type_from_words():
    assert keyword_baseline(DECLARATION) == "declaration"
    assert keyword_baseline(DATA_SHEET) == "data_sheet"
    assert keyword_baseline(MANUAL) == "manual"
    assert keyword_baseline("") == "other"  # a scan without text, or a blank page


def test_a_model_trained_from_scratch_learns_page_types():
    pages = [DECLARATION, DATA_SHEET, MANUAL] * 4
    labels = ["declaration", "data_sheet", "manual"] * 4
    model = build_model().fit(pages, labels)
    unseen = ["Wir erklären in alleiniger Verantwortung, dass die Produkte der Maschinenrichtlinie 2006/42/EG "
              "und der Niederspannungsrichtlinie 2014/35/EU entsprechen. We declare the products comply.",
              "Nr. Produs: 96001975. Debitul curent calculat: 3.39 l/s. Putere nominală P2: 1.2 kW. "
              "Tensiune nominală: 3 x 400 V."]
    assert predict(model, unseen) == ["declaration", "data_sheet"]
    assert predict(model, [""]) == ["other"]
