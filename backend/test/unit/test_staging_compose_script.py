import copy
import importlib.util
import re
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
            "ports": [{"host_ip": "100.119.147.8", "target": 8080, "published": "8081", "protocol": "tcp"}],
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
        ({"ports": [{"host_ip": "0.0.0.0", "published": "8081", "target": 8080, "protocol": "tcp"}]}, "rule 6"),
        ({"ports": [{"published": "8081", "target": 8080, "protocol": "tcp"}]}, "rule 6"),
        ({"ports": [{"host_ip": "127.0.0.1", "published": "8081", "target": 8080, "protocol": "tcp"}]}, "must bind to"),
        ({"ports": []}, "exactly one published port"),
        (
            {"ports": [{"host_ip": "100.119.147.8", "published": "8082", "target": 8080, "protocol": "tcp"}]},
            "must be 8081 to 8080/tcp",
        ),
        (
            {"ports": [{"host_ip": "100.119.147.8", "published": "8081", "target": 80, "protocol": "tcp"}]},
            "must be 8081 to 8080/tcp",
        ),
        (
            {"ports": [{"host_ip": "100.119.147.8", "published": "8081", "target": 8080, "protocol": "udp"}]},
            "must be 8081 to 8080/tcp",
        ),
        (
            {
                "ports": [
                    COMPLIANT["services"]["web"]["ports"][0],
                    {"host_ip": "100.119.147.8", "published": "9000", "target": 9000, "protocol": "tcp"},
                ]
            },
            "exactly one published port",
        ),
        ({"volumes": [{"type": "bind", "source": "/etc"}]}, "rule 7"),
        ({"environment": {"A": "b"}}, "environment"),
        ({"secrets": [{"source": "x"}]}, "secret"),
    ],
)
def test_should_report_the_rule_when_the_configuration_breaks_it(changes, rule):
    assert any(rule in v for v in _script().violations(_with(**changes)))


def test_should_allow_the_local_address_only_when_asked_for_a_local_run():
    local = _with(ports=[{"host_ip": "127.0.0.1", "published": "8081", "target": 8080, "protocol": "tcp"}])
    assert _script().violations(local, local=True) == []
    assert _script().violations(local) != []
    all_interfaces = _with(ports=[{"host_ip": "0.0.0.0", "published": "8081", "target": 8080, "protocol": "tcp"}])
    assert _script().violations(all_interfaces, local=True) != []


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


def test_should_pin_the_nginx_image_to_a_supported_version_and_a_digest():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    static = next(line for line in dockerfile.splitlines() if line.endswith("AS static"))
    assert re.search(r"nginx-unprivileged:\d+\.\d+\.\d+-alpine\d+\.\d+@sha256:[0-9a-f]{64} AS static$", static), static
    assert "nginx-unprivileged:1.27" not in dockerfile, "nginx 1.27 reached its end of life in June 2025"


def test_shouldNotServeTheUnobservedPairsDataFromTheStaticImageUntilTheViewIsExposed():
    conf = (REPO_ROOT / "deploy" / "nginx-static.conf").read_text(encoding="utf-8")
    block = re.search(r"location = /data/oepm-unobserved-pairs-results\.json \{\s*return 404;\s*\}", conf)
    assert block, "the vertical 3 data must answer 404 in the static staging until its exposure conditions are met"
    assert conf.index(block.group(0)) < conf.index("location / {"), "the exact-match block must precede the catch-all"


def test_shouldNotServeTheTopicMapDataFromTheStaticImageUntilD4IsRecorded():
    conf = (REPO_ROOT / "deploy" / "nginx-static.conf").read_text(encoding="utf-8")
    block = re.search(r"location \^~ /data/topic-map- \{\s*return 404;\s*\}", conf)
    assert block, "every topic-map-<topic>.json must answer 404 in the static staging until D4 and the exposure are recorded"
    # ^~ is a prefix: it closes topic-map-batteries.json and any other topic, and nothing outside the prefix
    # (topic-map.json or other-topic-map-x.json stay served as ordinary files).
    assert conf.index(block.group(0)) < conf.index("location / {"), "the block must precede the catch-all"
