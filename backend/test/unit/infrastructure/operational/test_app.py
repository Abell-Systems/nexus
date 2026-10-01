import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from infrastructure.mvp_entrypoint import parse_args
from infrastructure.operational.app import create_mvp_app

SRC_MAIN = Path(__file__).resolve().parents[5] / "backend" / "src" / "main"


@pytest.fixture
def static_dir(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    return tmp_path


class MvpAppTest:
    def test_should_serve_matches_and_report_ready_when_artifacts_verify(self, operational_dir, selection):
        client = TestClient(create_mvp_app(operational_dir, selection=selection))
        assert client.get("/health").json() == {"ready": True}
        assert client.get("/api/matches", params={"demand_id": "D-1"}).status_code == 200

    @pytest.mark.parametrize("method,path", [
        ("POST", "/run"), ("POST", "/api/analyze"), ("GET", "/docs"), ("GET", "/openapi.json"), ("GET", "/list-apps"),
    ])
    def test_should_not_expose_the_legacy_agent_surface_when_serving(self, operational_dir, selection, method, path):
        client = TestClient(create_mvp_app(operational_dir, selection=selection))
        assert client.request(method, path).status_code in (404, 405)

    def test_should_abort_startup_when_the_artifacts_directory_is_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            create_mvp_app(tmp_path / "missing")

    def test_should_serve_the_spa_and_its_assets_when_a_static_directory_is_given(self, operational_dir, static_dir, selection):
        client = TestClient(create_mvp_app(operational_dir, static_dir, selection))
        assert client.get("/").text == "<html>spa</html>"
        assert client.get("/matches").text == "<html>spa</html>"
        assert client.get("/assets/app.js").text == "console.log(1)"

    def test_should_answer_404_instead_of_the_spa_when_an_unknown_api_route_is_requested(self, operational_dir, static_dir, selection):
        client = TestClient(create_mvp_app(operational_dir, static_dir, selection))
        assert client.get("/api/nope").status_code == 404

    @pytest.mark.parametrize("path", ["/docs", "/openapi.json", "/list-apps", "/run"])
    def test_should_answer_404_instead_of_the_spa_when_a_legacy_path_is_requested_with_a_static_directory(
        self, operational_dir, static_dir, selection, path
    ):
        client = TestClient(create_mvp_app(operational_dir, static_dir, selection))
        assert client.get(path).status_code == 404

    def test_should_not_serve_files_outside_the_static_directory_when_the_path_escapes_it(self, operational_dir, static_dir, selection):
        client = TestClient(create_mvp_app(operational_dir, static_dir, selection))
        assert client.get("/..%2Fsecret").status_code == 404

    def test_should_not_serve_the_spa_when_no_static_directory_is_given(self, operational_dir, selection):
        assert TestClient(create_mvp_app(operational_dir, selection=selection)).get("/").status_code == 404

    def test_should_start_without_environment_and_without_importing_the_legacy_agent(self, operational_dir, selection):
        code = (
            f"import sys; sys.path.insert(0, {str(SRC_MAIN)!r})\n"
            "from pathlib import Path\n"
            "from infrastructure.operational.app import create_mvp_app\n"
            f"create_mvp_app(Path({str(operational_dir)!r}), selection=Path({str(selection)!r}))\n"
            "legacy = [m for m in sys.modules if m == 'infrastructure.api' or m.startswith(('google.adk', 'agents'))]\n"
            "assert not legacy, legacy\n"
        )
        result = subprocess.run([sys.executable, "-c", code], env={}, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


class EntrypointArgsTest:
    def test_should_require_the_artifacts_directory(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_should_default_to_loopback_without_a_static_directory(self):
        args = parse_args(["--artifacts", "/srv/nexus/data"])
        assert (args.artifacts, args.static, args.host, args.port) == (Path("/srv/nexus/data"), None, "127.0.0.1", 8080)
