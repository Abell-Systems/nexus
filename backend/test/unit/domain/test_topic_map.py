import pytest

from domain.models.topic_map import CodeRule, SubArea, TopicDefinition


def _area(key: str, *codes: CodeRule) -> SubArea:
    return SubArea(key=key, name=f"n{key}", description="d", reviewed=False, codes=codes)


def _topic(*areas: SubArea) -> TopicDefinition:
    return TopicDefinition(
        key="t", name="T", noun="t", joined="tt", subareas=areas, neighbour_names=(), own_subclasses=frozenset({"H01M"})
    )


def _rule(group: str | None) -> CodeRule:
    return CodeRule(subclass="H01M", main_group=group, introduced=None, removed=None, verified=True)


def test_shouldRejectADefinitionWhenACodeBelongsToTwoSubareas() -> None:
    with pytest.raises(ValueError, match="H01M"):
        _topic(_area("a", _rule("10")), _area("b", _rule("10")))


def test_shouldRejectADefinitionWhenThereIsNoSubarea() -> None:
    with pytest.raises(ValueError):
        _topic()


def test_shouldRejectASubareaWhenItsNameIsEmpty() -> None:
    with pytest.raises(ValueError):
        SubArea(key="a", name=" ", description="d", reviewed=False, codes=(_rule("10"),))
