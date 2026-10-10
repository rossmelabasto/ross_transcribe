import pytest

from ross_transcribe import i18n


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"LANG": "es_BO.UTF-8"}, "es"),
        ({"LANG": "en_US.UTF-8"}, "en"),
        ({"LANG": "en_US.UTF-8", "LC_ALL": "es_ES.UTF-8"}, "es"),
        ({"LANG": "es_BO.UTF-8", "TRANSCRIBE_UI_LANG": "en"}, "en"),
        ({}, "en"),
    ],
)
def test_detect(env, expected):
    assert i18n.detect(env) == expected


def test_both_languages_have_the_same_keys():
    assert set(i18n.STRINGS["en"]) == set(i18n.STRINGS["es"])


def test_t_formats_and_switches():
    i18n.set_lang("es")
    assert i18n.t("found_n", n=3) == "3 archivos encontrados"
    i18n.set_lang("en")
    assert i18n.t("found_n", n=3) == "3 files found"
    i18n.set_lang("xx")
    assert i18n.get_lang() == "en"
