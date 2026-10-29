"""Loading a topic definition file and identifying it by content."""

from pathlib import Path

from application.whitespace.unobserved_pairs import configuration_id
from domain.models.topic_map import TopicDefinition


def load_definition(path: Path) -> TopicDefinition:
    return TopicDefinition.model_validate_json(path.read_text(encoding="utf-8"))


def definition_id(definition: TopicDefinition) -> str:
    """SHA-256 of the canonical JSON: any change to a name, description or code rule changes it."""
    dumped = definition.model_dump(mode="json")
    dumped["own_subclasses"] = sorted(dumped["own_subclasses"])  # a set dumps in hash-seed order
    return configuration_id(dumped)


def unreviewed_names(definition: TopicDefinition) -> list[str]:
    names = [a.name for a in definition.subareas if not a.reviewed]
    return names + [n.name for n in definition.neighbour_names if not n.reviewed]
