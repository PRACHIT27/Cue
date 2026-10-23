import pytest

from cue.guards import Known, clean_text, guard_brief_items, guard_pitch_items, ground_text, strip_placement_claims
from cue.records import BriefItem, FitScore, PitchItem
from cue.tools.records import EntityRef

KNOWN = Known({"S-1": "Fake Show", "S-2": "Other Fake Show", "A-1": "Fake Artist"})


def ref(entity_id, name="Draft Name"):
    return EntityRef(entity_id, name, "urn:entity:tv_show", 0.5)


def fit(entity_id):
    return FitScore(f"A-1:{entity_id}", 0.8, "ok", {})


def test_placeholders_become_real_names():
    text, drops = ground_text("Your fans love {{S-1}}. It suits your sound.", KNOWN)
    assert text == "Your fans love Fake Show. It suits your sound." and drops == []


def test_unknown_placeholder_drops_only_that_sentence():
    text, drops = ground_text("Your fans love {{S-1}}. They also love {{S-404}}. Pitch soon.", KNOWN)
    assert text == "Your fans love Fake Show. Pitch soon."
    assert drops[0].guard == "grounding" and "S-404" in drops[0].reason


@pytest.mark.parametrize("title", ['*Monsoon Diaries*', '"Monsoon Diaries"', "“Monsoon Diaries”"])
def test_made_up_quoted_title_drops_the_sentence(title):
    text, drops = ground_text(f"Consider {title} for this. Fans love {{{{S-1}}}}.", KNOWN)
    assert text == "Fans love Fake Show." and "Monsoon Diaries" in drops[0].reason


def test_known_quoted_title_and_the_artist_are_allowed():
    text, drops = ground_text('Fans of *fake show* and "Fake Artist" agree.', KNOWN, artist_name="Fake Artist")
    assert drops == [] and "fake show" in text


def test_line_breaks_survive():
    text, _ = ground_text("Hi there.\nYour fans love {{S-1}}.\n\nBest, Fake Artist", KNOWN)
    assert text == "Hi there.\nYour fans love Fake Show.\n\nBest, Fake Artist"


@pytest.mark.parametrize(
    "claim",
    [
        "My song was featured in Fake Show.",
        "Our track has been used in two films.",
        "My music was placed on a Netflix series.",
        "The single was licensed to a big brand.",
        "My track appeared in a trailer.",
        "This song soundtracked a campaign.",
        "I have several past placements.",
        "As heard on Fake Show, my single is rising.",
    ],
)
def test_placement_claims_are_removed(claim):
    text, drops = strip_placement_claims(f"Hello. {claim} Thanks.")
    assert text == "Hello. Thanks." and drops[0].guard == "claim"


@pytest.mark.parametrize(
    "wish",
    [
        "I'd love my song to be featured in Season 3.",
        "My music could fit the monsoon scenes.",
        "Happy to license two tracks for the show.",
        "Your viewers over-index on music like mine.",
        "The show scored highly with my listeners.",
    ],
)
def test_honest_pitch_lines_are_kept(wish):
    text, drops = strip_placement_claims(wish)
    assert text == wish and drops == []


def test_clean_text_runs_both_guards():
    text, drops = clean_text("Fans love {{S-1}}. My song was featured in it. Try *Made Up*.", KNOWN)
    assert text == "Fans love Fake Show."
    assert sorted(d.guard for d in drops) == ["claim", "grounding"]


def test_pitch_item_with_unknown_candidate_is_dropped():
    items = [
        PitchItem(ref("S-1"), fit("S-1"), "Fans love {{S-1}}.", "Pitch for {{S-1}}", "Hi, {{S-1}} fans love my music."),
        PitchItem(ref("S-999", "Invented Show"), fit("S-999"), "r", "s", "b"),
    ]
    kept, drops = guard_pitch_items(items, KNOWN, "Fake Artist")
    assert [i.candidate.id for i in kept] == ["S-1"]
    assert kept[0].candidate.name == "Fake Show"
    assert kept[0].email_body == "Hi, Fake Show fans love my music."
    assert drops[0].reason.startswith("candidate S-999")


def test_pitch_item_with_nothing_safe_left_is_dropped():
    items = [PitchItem(ref("S-1"), fit("S-1"), "ok", "subject", "My song was featured in {{S-1}}.")]
    kept, drops = guard_pitch_items(items, KNOWN)
    assert kept == [] and drops[-1].reason == "nothing safe left in the email"


def test_brief_items_are_grounded():
    items = [BriefItem(ref("S-2"), fit("S-2"), "Viewers of {{S-2}} love this sound."), BriefItem(ref("S-7"), fit("S-7"), "x")]
    kept, drops = guard_brief_items(items, KNOWN)
    assert [i.reason for i in kept] == ["Viewers of Other Fake Show love this sound."] and len(drops) == 1
