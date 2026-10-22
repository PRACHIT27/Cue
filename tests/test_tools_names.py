import pytest

from cue.tools.names import names_match, normalise_name


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Prateek Kuhad", "prateek kuhad"),
        ("PRATEEK KUHAD", "prateek kuhad"),
        ("  Prateek   Kuhad  ", "prateek kuhad"),
        ("Beyoncé", "beyonce"),
        ("Sigur Rós", "sigur ros"),
        ("Shankar-Ehsaan-Loy", "shankar ehsaan loy"),
        ("A.R. Rahman", "a r rahman"),
        ("Simon & Garfunkel", "simon and garfunkel"),
        ("The Local Train", "local train"),
        ("Thea Gilmore", "thea gilmore"),
        ("", ""),
    ],
)
def test_normalise_name(raw, expected):
    assert normalise_name(raw) == expected


@pytest.mark.parametrize(
    "a, b",
    [
        ("Prateek Kuhad", "prateek  kuhad"),
        ("The Local Train", "Local Train"),
        ("Simon and Garfunkel", "Simon & Garfunkel"),
        ("Beyonce", "Beyoncé"),
    ],
)
def test_same_artist_matches(a, b):
    assert names_match(a, b)


@pytest.mark.parametrize(
    "a, b",
    [
        ("Aditi Ramesh", "Ramesh"),
        ("Anirudh", "Anirudh Ravichander"),
        ("Shaan", "Shaan, Sunidhi Chauhan"),
        ("Sanjeeta Bhattacharya", "Debashish Bhattacharya"),
    ],
)
def test_different_artists_do_not_match(a, b):
    assert not names_match(a, b)
