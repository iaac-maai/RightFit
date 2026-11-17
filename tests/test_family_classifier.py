"""The non-AI baseline of the family classifier: fixed family words on the name of a form row."""
from model.family_classifier import FAMILY_WORDS, family_words
from model.family_rows import families


def test_every_family_but_other_has_words():
    assert set(FAMILY_WORDS) == set(families()) - {"other"}


def test_a_name_gives_its_family():
    assert family_words("Clapetă antifoc EI120, 24V") == "fire_damper"
    assert family_words("Izolație elastomerică cu barieră de vapori") == "elastomeric_insulation"
    assert family_words("Radiator din oțel tip 22") == "radiator"
    assert family_words("Centrală de detecție incendiu") == "fire_detection_panel"
    assert family_words("Centrală tratare aer 9000 m³/h") == "ahu"
    assert family_words("Grup de pompare apă menajeră") == "pump"
    assert family_words("Difuzor de plafon 6W/100V, EN 54") == "voice_alarm_loudspeaker"
    assert family_words("Cablu NHXH 3x1,5") == "cable"
    assert family_words("Sursă de alimentare 24V, EN-54") == "fire_alarm_power_supply"
    assert family_words("Consolă microfon evacuare vocală") == "voice_alarm_control"
    assert family_words("Dispozitiv de semnalizare optică, flash alb") == "visual_alarm_device"


def test_when_two_families_are_named_the_first_wins():
    assert family_words("Unitate exterioară pentru kit DX") == "outdoor_unit"
    assert family_words("Kit DX pentru unitate exterioară") == "dx_kit"


def test_accessories_and_other_supplies_are_other():
    assert family_words("Pat de cabluri metalic") == "other"            # a cable's name starts with the word
    assert family_words("Alimentator 24V consolă microfon") == "other"  # no fire or voice alarm named
    assert family_words("Racord pompieri") == "other"                   # fire brigade, not a pump
    assert family_words("Robinet sferă PN25") == "other"
