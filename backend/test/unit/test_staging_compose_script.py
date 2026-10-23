import copy
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

COMPLIANT = {
    "services": {
        "web": {
            "user": "101:101",
            "read_only": True,
            "privileged": False,
            "security_opt": ["no-new-privileges:true"],
            "cap_drop": ["ALL"],
            "mem_limit": "134217728",
            "cpus": 0.5,
            "pids_limit": 50,
            "networks": {"nexus-net": None},
            "ports": [{"host_ip": "100.119.147.8", "target": 8080, "published": "8081"}],
        }
    },
    "networks": {"nexus-net": {}},
}


def _script():
    spec = importlib.util.spec_from_file_location(
        "check_staging_compose", REPO_ROOT / "scripts" / "check_staging_compose.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _with(**changes):
    config = copy.deepcopy(COMPLIANT)
    config["services"]["web"].update(changes)
    return config


def test_should_accept_a_configuration_that_meets_the_contract():
    assert _script().violations(COMPLIANT) == []


@pytest.mark.parametrize(
    ("changes", "rule"),
    [
        ({"user": "0:0"}, "rule 1"),
        ({"user": ""}, "rule 1"),
        ({"read_only": False}, "rule 2"),
        ({"privileged": True}, "rule 3"),
        ({"security_opt": []}, "rule 3"),
        ({"cap_drop": []}, "rule 4"),
        ({"cap_add": ["NET_ADMIN"]}, "rule 4"),
        ({"mem_limit": None}, "rule 5"),
        ({"pids_limit": None}, "rule 5"),
        ({"networks": None}, "rule 6"),
        ({"network_mode": "host"}, "rule 6"),
        ({"ports": [{"host_ip": "0.0.0.0", "published": "8081"}]}, "rule 6"),
        ({"ports": [{"published": "8081"}]}, "rule 6"),
        ({"volumes": [{"type": "bind", "source": "/etc"}]}, "rule 7"),
        ({"environment": {"A": "b"}}, "environment"),
        ({"secrets": [{"source": "x"}]}, "secret"),
    ],
)
def test_should_report_the_rule_when_the_configuration_breaks_it(changes, rule):
    assert any(rule in v for v in _script().violations(_with(**changes)))


def test_should_report_unexpected_services_and_top_level_volumes():
    config = copy.deepcopy(COMPLIANT)
    config["services"]["db"] = copy.deepcopy(config["services"]["web"])
    config["volumes"] = {"pgdata": {}}
    found = _script().violations(config)
    assert any("services must be exactly" in v for v in found)
    assert any("top-level" in v for v in found)


def test_should_serve_only_files_and_health_and_proxy_nothing():
    conf = (REPO_ROOT / "deploy" / "nginx-static.conf").read_text(encoding="utf-8")
    assert "location = /health" in conf
    assert "try_files $uri $uri/ =404;" in conf
    assert "proxy_pass" not in conf
    assert "listen 8080;" in conf
    assert "pid /tmp/nginx.pid;" in conf


def test_should_build_the_static_page_from_a_target_that_keeps_the_mvp_as_default():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    stages = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]
    assert any(line.endswith("AS static") for line in stages)
    assert stages[-1].startswith("FROM python:"), "the default target (last stage) must stay the MVP image"
