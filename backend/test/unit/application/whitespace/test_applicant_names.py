from pathlib import Path
from random import Random

import pytest

from application.whitespace.applicant_names import Rule, canonical_name, load_rules, normalise

RULES_FILE = Path(__file__).parents[5] / "config" / "topics" / "applicant_rules.json"
MADRID = "Universidad Politécnica de Madrid"


def _rule(pattern: str, canonical: str) -> Rule:
    return Rule(pattern, canonical, "r", "2026-10-29")


def test_shouldNormaliseCaseAccentsPunctuationAndSpaces():
    assert normalise("  Universidad Politécnica,  de   Madrid. ") == "UNIVERSIDAD POLITECNICA DE MADRID"
    assert normalise("UNIVERSIDAD POLIT�CNICA DE MADRID") == "UNIVERSIDAD POLIT CNICA DE MADRID"


def test_shouldNotMergeAPoliteciaOfValenciaIntoMadrid():
    rules = load_rules(RULES_FILE)
    for name in ("UNIVERSIDAD POLITECNICA DE VALENCIA", "UNIVERSIDAD POLITECNICA DE CATALUNYA"):
        canonical, original = canonical_name(name, rules)
        assert canonical != MADRID
        assert canonical == normalise(name).title()
        assert original == name
    assert canonical_name("UNIVERSIDAD POLITECNICA DE MADRID", rules)[0] == MADRID
    assert canonical_name("UNIVERSIDAD POLIT�CNICA DE MADRID", rules)[0] == MADRID


def test_shouldMergeSpellingVariantsOfTheSameCompany():
    rules = load_rules(RULES_FILE)
    assert canonical_name("Abengoa Solar, S.A.", rules)[0] == "Abengoa Solar"
    assert canonical_name("ABENGOA SOLAR NEW TECHNOLOGIES SA", rules)[0] == "Abengoa Solar"
    assert canonical_name("HUNAN BRUNP RECYCLING CO", rules)[0] == "Brunp Recycling (grupo)"
    assert canonical_name("GUANGDONG BRUNP RECYCLING TECHNOLOGY", rules)[0] == "Brunp Recycling (grupo)"


def test_shouldKeepTheOriginalNameForTraceability():
    original = "Robert Bosch GmbH"
    assert canonical_name(original, load_rules(RULES_FILE)) == ("Bosch", original)


def test_shouldKeepAnUnresolvedNameSeparate():
    assert canonical_name("Acme  Widgets, S.L.", load_rules(RULES_FILE)) == ("Acme Widgets S L", "Acme  Widgets, S.L.")


def test_shouldNotMatchABareSubstringOrAnInWordPrefix():
    rules = load_rules(RULES_FILE)
    for name in ("THE ROBERT BOSCH FOUNDATION", "ROBERT BOSCHEN GMBH", "XTRINA SOLAR", "TRINA SOLARIS"):
        assert canonical_name(name, rules)[0] == normalise(name).title()


def test_shouldRaiseWhenTwoRulesMatchTheSameNameWithDifferentCanonicals():
    rules = (_rule("ACME", "Acme"), _rule("ACME WIDGETS", "Widgets"))
    with pytest.raises(ValueError):
        canonical_name("Acme Widgets SL", rules)


def test_shouldAcceptTwoMatchingRulesThatAgreeAndIgnoreRuleOrder():
    rules = (_rule("ACME", "Acme"), _rule("ACME WIDGETS", "Acme"))
    assert canonical_name("Acme Widgets SL", rules)[0] == "Acme"
    loaded = list(load_rules(RULES_FILE))
    for order in (loaded[::-1], Random(0).sample(loaded, len(loaded))):
        assert canonical_name("Robert Bosch GmbH", order)[0] == "Bosch"


def test_shouldSeedRulesWithAReasonAndDateAndNoEmptyPattern():
    rules = load_rules(RULES_FILE)
    assert len(rules) >= 12 and all(r.reason and r.date == "2026-10-29" and normalise(r.pattern) for r in rules)
