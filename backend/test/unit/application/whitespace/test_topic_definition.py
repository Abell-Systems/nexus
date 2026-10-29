from pathlib import Path

from application.whitespace.topic_definition import definition_id, load_definition, unreviewed_names

TOPICS = Path(__file__).parents[5] / "config" / "topics"


def _write(path: Path, area_name: str, reviewed: bool = False) -> Path:
    area = (
        f'{{"key":"a","name":"{area_name}","description":"d","reviewed":{str(reviewed).lower()},'
        '"codes":[{"subclass":"H01M","main_group":"10","introduced":null,"removed":null,"verified":true}]}'
    )
    path.write_text(
        '{"key":"t","name":"T","noun":"t","joined":"tt","own_subclasses":["H01M"],'
        f'"subareas":[{area}],"neighbour_names":[{{"subclass":"C01B","name":"Vecino","reviewed":false}}]}}',
        encoding="utf-8",
    )
    return path


def test_shouldChangeTheDefinitionIdWhenAPlainNameChanges(tmp_path: Path) -> None:
    a = load_definition(_write(tmp_path / "a.json", "Uno"))
    b = load_definition(_write(tmp_path / "b.json", "Dos"))
    assert definition_id(a) != definition_id(b)
    assert definition_id(a) == definition_id(load_definition(tmp_path / "a.json"))


def test_shouldListUnreviewedNamesWhenAFlagIsFalse(tmp_path: Path) -> None:
    assert unreviewed_names(load_definition(_write(tmp_path / "a.json", "Uno"))) == ["Uno", "Vecino"]
    assert unreviewed_names(load_definition(_write(tmp_path / "b.json", "Uno", reviewed=True))) == ["Vecino"]


def test_shouldLoadBothCommittedDefinitions() -> None:
    bat = load_definition(TOPICS / "baterias.json")
    sol = load_definition(TOPICS / "solar.json")
    assert [a.key for a in bat.subareas] == ["10", "4", "2+50", "8", "6", "12", "16"]
    assert [a.key for a in sol.subareas] == ["pv", "systems", "thermal"]
    assert len(bat.neighbour_names) == len(sol.neighbour_names) == 31
    assert unreviewed_names(bat) and unreviewed_names(sol)
