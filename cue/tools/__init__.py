from cue.tools.compare import compare
from cue.tools.context import current_client, use_client
from cue.tools.entities import get_entities
from cue.tools.find_entity import find_entity
from cue.tools.insights import insights
from cue.tools.lookups import find_audiences, find_tags, get_audience_types, get_tag_types
from cue.tools.names import names_match, normalise_name
from cue.tools.trending import trend_score, trending

__all__ = [
    "compare",
    "current_client",
    "find_audiences",
    "find_entity",
    "find_tags",
    "get_audience_types",
    "get_entities",
    "get_tag_types",
    "insights",
    "names_match",
    "normalise_name",
    "trend_score",
    "trending",
    "use_client",
]
