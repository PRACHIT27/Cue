import json
from dataclasses import dataclass
from datetime import date

import pytest

from cue.run import _jsonable, parser


def test_parser_reads_both_modes():
    a = parser().parse_args(["artist", "Fake Artist", "--brief", "rain scene", "--sounds-like", "A, B", "--emails"])
    assert (a.mode, a.name, a.brief, a.sounds_like, a.emails) == ("artist", "Fake Artist", "rain scene", "A, B", True)
    s = parser().parse_args(["supervisor", "Fake Show", "--type", "movie", "--trace"])
    assert (s.mode, s.production_type, s.trace) == ("supervisor", "movie", True)


def test_parser_rejects_unknown_modes_and_types():
    with pytest.raises(SystemExit):
        parser().parse_args(["sideways", "x"])
    with pytest.raises(SystemExit):
        parser().parse_args(["supervisor", "x", "--type", "opera"])


@dataclass(frozen=True)
class Inner:
    when: date
    tags: tuple


@dataclass(frozen=True)
class Outer:
    inner: Inner
    extra: dict


def test_results_export_as_plain_json():
    value = _jsonable(Outer(Inner(date(2026, 7, 31), ("a", "b")), {"x": (1, 2)}))
    assert json.loads(json.dumps(value)) == {"inner": {"when": "2026-07-31", "tags": ["a", "b"]}, "extra": {"x": [1, 2]}}
