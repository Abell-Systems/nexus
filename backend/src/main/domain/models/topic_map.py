"""Definition of a technology topic: plain names, descriptions and the IPC code rules behind them (topic map, spec section 6)."""

from pydantic import BaseModel, ConfigDict, model_validator


class CodeRule(BaseModel):
    """An IPC subclass, or one main group of it. ``main_group=None`` means the whole subclass."""

    model_config = ConfigDict(frozen=True)

    subclass: str
    main_group: str | None
    introduced: str | None
    removed: str | None
    verified: bool


class SubArea(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    description: str
    reviewed: bool
    codes: tuple[CodeRule, ...]

    @model_validator(mode="after")
    def _names_not_empty(self) -> "SubArea":
        if not self.name.strip() or not self.description.strip():
            raise ValueError(f"sub-area {self.key}: name and description must not be empty")
        return self


class NeighbourName(BaseModel):
    model_config = ConfigDict(frozen=True)

    subclass: str
    name: str
    reviewed: bool
    note: str | None = None

    @model_validator(mode="after")
    def _name_not_empty(self) -> "NeighbourName":
        if not self.name.strip():
            raise ValueError(f"neighbour {self.subclass}: name must not be empty")
        return self


class TopicDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    noun: str
    joined: str
    subareas: tuple[SubArea, ...]
    neighbour_names: tuple[NeighbourName, ...]
    own_subclasses: frozenset[str]

    @model_validator(mode="after")
    def _consistent(self) -> "TopicDefinition":
        if not self.subareas:
            raise ValueError("a topic needs at least one sub-area")
        if not (self.name.strip() and self.noun.strip() and self.joined.strip()):
            raise ValueError("topic name, noun and joined must not be empty")
        owner: dict[tuple[str, str | None], str] = {}
        for area in self.subareas:
            for rule in area.codes:
                code = (rule.subclass, rule.main_group)
                if code in owner:
                    raise ValueError(f"code {rule.subclass} {rule.main_group} is in sub-areas {owner[code]} and {area.key}")
                owner[code] = area.key
        return self
