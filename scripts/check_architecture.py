#!/usr/bin/env python3
"""Deterministic Architecture Checker for Nexus 2.0 Clean Architecture.

Enforces:
1. Canonical directory structure:
   - backend/src/main/{domain,application,infrastructure}
   - backend/test/{unit,integration,e2e}
   - frontend/src/main/{domain,application,infrastructure,components,App.tsx,main.tsx,index.css}
   - frontend/test/{unit,integration,e2e}
2. Forbidden legacy directories (nexus, backend/patent_agent, backend/tests, interfaces, root tests).
3. No production code outside src/main/.
4. Strict unidirectional layer imports:
   - Backend (Python AST):
     - domain cannot import application, infrastructure, or heavy external frameworks (FastAPI, Google ADK, DuckDB, PyArrow).
     - application cannot import infrastructure or Google ADK.
   - Frontend (TypeScript / JavaScript imports):
     - domain (models/types) cannot import application, infrastructure, components, or React.
     - infrastructure (API client) cannot import application or presentation components.
     - application (hooks/state) cannot import presentation components.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_forbidden_directories(errors: list[str]) -> None:
    forbidden_dirs = [
        REPO_ROOT / "backend" / "patent_agent",
        REPO_ROOT / "backend" / "tests",
        REPO_ROOT / "nexus",
        REPO_ROOT / "interfaces",
        REPO_ROOT / "tests",
        REPO_ROOT / "src",
    ]
    for d in forbidden_dirs:
        if d.exists() and d.is_dir():
            rel = d.relative_to(REPO_ROOT)
            errors.append(f"FAIL: forbidden directory exists: {rel}/")


def check_backend_files(errors: list[str]) -> None:
    backend_dir = REPO_ROOT / "backend"
    if not backend_dir.exists():
        errors.append("FAIL: backend/ directory missing")
        return

    allowed_root_entries = {
        "src",
        "test",
        "static",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-adk.txt",
        "Dockerfile",
        "__pycache__",
        ".pytest_cache",
    }
    for item in backend_dir.iterdir():
        if item.name.startswith("."):
            continue
        if item.name not in allowed_root_entries:
            errors.append(f"FAIL: unexpected file/directory in backend root: backend/{item.name}")

    # Check backend/src
    backend_src = backend_dir / "src"
    if backend_src.exists():
        for item in backend_src.iterdir():
            if item.name != "main" and not item.name.startswith("."):
                errors.append(f"FAIL: production file outside backend/src/main: backend/src/{item.name}")

    # Check backend/src/main layer folders
    backend_main = backend_dir / "src" / "main"
    if backend_main.exists():
        allowed_main = {"domain", "application", "infrastructure", "main.py", "__pycache__"}
        for item in backend_main.iterdir():
            if item.name.startswith("."):
                continue
            if item.name not in allowed_main:
                errors.append(f"FAIL: invalid layer in backend/src/main: {item.name}")

    backend_test = backend_dir / "test"
    if backend_test.exists():
        allowed_test = {"unit", "integration", "e2e", "providers", "fixtures", "__init__.py", "__pycache__"}
        for item in backend_test.iterdir():
            if item.name.startswith("."):
                continue
            if item.name not in allowed_test:
                errors.append(f"FAIL: invalid folder in backend/test: {item.name}")


def check_frontend_files(errors: list[str]) -> None:
    frontend_dir = REPO_ROOT / "frontend"
    if not frontend_dir.exists():
        return

    allowed_root_entries = {
        "src",
        "test",
        "public",
        "node_modules",
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "tsconfig.app.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "index.html",
        "README.md",
        "dist",
        "coverage",
        ".env",
        ".env.example",
    }
    for item in frontend_dir.iterdir():
        if item.name.startswith("."):
            continue
        if item.name not in allowed_root_entries:
            errors.append(f"FAIL: unexpected file/directory in frontend root: frontend/{item.name}")

    frontend_src = frontend_dir / "src"
    if frontend_src.exists():
        for item in frontend_src.iterdir():
            if item.name != "main" and not item.name.startswith("."):
                errors.append(f"FAIL: production file outside frontend/src/main: frontend/src/{item.name}")

    frontend_main = frontend_src / "main"
    if frontend_main.exists():
        allowed_layers = {
            "domain",
            "application",
            "infrastructure",
            "components",
            "App.tsx",
            "main.tsx",
            "index.css",
            "__pycache__",
        }
        for item in frontend_main.iterdir():
            if item.name.startswith("."):
                continue
            if item.name not in allowed_layers:
                errors.append(f"FAIL: invalid entry in frontend/src/main: {item.name}")

    frontend_test = frontend_dir / "test"
    if frontend_test.exists():
        allowed_test = {"unit", "integration", "e2e", "__pycache__"}
        for item in frontend_test.iterdir():
            if item.name.startswith("."):
                continue
            if item.name not in allowed_test:
                errors.append(f"FAIL: invalid folder in frontend/test: {item.name}")


class LayerImportVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, current_layer: str):
        self.file_path = file_path
        self.current_layer = current_layer
        self.imported_modules: list[tuple[str, int]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imported_modules.append((alias.name, node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        self.imported_modules.append((mod, node.lineno))
        self.generic_visit(node)


def check_backend_layer_dependencies(errors: list[str]) -> None:
    """Checks Python AST-level invariants not expressible via standard import graph.

    Inter-layer and cross-subsystem module contracts (domain vs application vs infrastructure,
    evaluation decoupling, adapter boundary) are declared and enforced by Import Linter in
    .importlinter via check_import_linter_contracts().

    This visitor specifically enforces framework-isolation invariants:
    - domain must never import external heavy frameworks (fastapi, google.adk, duckdb, pyarrow, google.cloud).
    - application must never import delivery/agent frameworks (google.adk, fastapi).
    """
    backend_main = REPO_ROOT / "backend" / "src" / "main"
    if not backend_main.exists():
        return

    for py_file in backend_main.rglob("*.py"):
        rel_path = py_file.relative_to(backend_main)
        parts = rel_path.parts
        if not parts:
            continue

        layer = parts[0]
        if layer not in ("domain", "application"):
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as e:
            errors.append(f"FAIL: syntax error parsing {py_file}: {e}")
            continue

        visitor = LayerImportVisitor(py_file, layer)
        visitor.visit(tree)

        for mod, lineno in visitor.imported_modules:
            rel_file = py_file.relative_to(REPO_ROOT)

            # Framework Isolation in Domain
            if layer == "domain" and any(
                mod.startswith(fw) for fw in ("fastapi", "google.adk", "duckdb", "pyarrow", "google.cloud")
            ):
                errors.append(
                    f"FAIL: forbidden framework dependency in domain: {rel_file}:{lineno} (imports: {mod})"
                )

            # Framework Isolation in Application
            if layer == "application" and any(mod.startswith(fw) for fw in ("google.adk", "fastapi")):
                errors.append(
                    f"FAIL: forbidden framework dependency in application: {rel_file}:{lineno} (imports: {mod})"
                )


TS_IMPORT_PATTERN = re.compile(
    r'''(?:import\s+(?:type\s+)?(?:(?:[\w*\s{},]+)\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))''',
    re.MULTILINE,
)


def check_frontend_layer_dependencies(errors: list[str]) -> None:
    frontend_main = REPO_ROOT / "frontend" / "src" / "main"
    if not frontend_main.exists():
        return

    for ts_file in frontend_main.rglob("*"):
        if ts_file.suffix not in (".ts", ".tsx"):
            continue

        rel_path = ts_file.relative_to(frontend_main)
        parts = rel_path.parts
        if not parts:
            continue

        layer = parts[0]
        content = ts_file.read_text(encoding="utf-8")
        rel_file = ts_file.relative_to(REPO_ROOT)

        for match in TS_IMPORT_PATTERN.finditer(content):
            import_target = match.group(1) or match.group(2) or ""

            # 1. Frontend Domain Layer Invariants: pure models/types, zero dependencies on application, infrastructure, components, react
            if layer == "domain" and any(k in import_target for k in ("application", "infrastructure", "components", "react")):
                errors.append(
                    f"FAIL: forbidden dependency: {rel_file} (frontend domain imports: {import_target})"
                )

            # 2. Frontend Infrastructure Layer Invariants: API fetch client, zero dependencies on application or presentation components
            if layer == "infrastructure" and any(k in import_target for k in ("application", "components")):
                errors.append(
                    f"FAIL: forbidden dependency: {rel_file} (frontend infrastructure imports: {import_target})"
                )

            # 3. Frontend Application Layer Invariants: application hooks/orchestration, zero dependencies on presentation components
            if layer == "application" and "components" in import_target:
                errors.append(
                    f"FAIL: forbidden dependency: {rel_file} (frontend application imports: {import_target})"
                )


def check_monorepo_boundaries(errors: list[str], repo_root: Path = REPO_ROOT) -> None:
    """Enforces ADR 0024 monorepo boundary invariants:

    1. nexus/frontend must NEVER import from nexus-status (neither via relative paths nor package/alias).
    2. nexus-status/frontend must NEVER import from frontend or backend (neither via relative paths nor package/alias).
    3. Neither application may use relative imports that escape its own application root.
    4. nexus-status workspace structural integrity.
    """
    nexus_status_dir = repo_root / "nexus-status"
    if not nexus_status_dir.exists():
        return

    # 1. Check nexus-status workspace root structure
    allowed_status_root = {"frontend", "README.md"}
    for item in nexus_status_dir.iterdir():
        if item.name.startswith("."):
            continue
        if item.name not in allowed_status_root:
            errors.append(
                f"FAIL: unexpected entry in nexus-status workspace root: nexus-status/{item.name} "
                f"(expected: {sorted(allowed_status_root)})"
            )

    frontend_dir = repo_root / "frontend"
    status_frontend_dir = nexus_status_dir / "frontend"
    backend_dir = repo_root / "backend"

    status_src = status_frontend_dir / "src"
    frontend_src = frontend_dir / "src"

    forbidden_pkg_in_status = {
        "frontend",
        "backend",
        "patent-innovation-agent-frontend",
        "@frontend",
        "@backend",
    }

    forbidden_pkg_in_frontend = {
        "nexus-status",
        "nexus-status-frontend",
        "@nexus-status",
    }

    # 2. Check imports in frontend/src
    if frontend_src.exists():
        for f in frontend_src.rglob("*"):
            if f.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            content = f.read_text(encoding="utf-8")
            for match in TS_IMPORT_PATTERN.finditer(content):
                target = (match.group(1) or match.group(2) or "").strip()
                rel_file = f.relative_to(repo_root)

                if target.startswith("."):
                    resolved = (f.parent / target).resolve()
                    parts = Path(target).parts
                    if resolved == nexus_status_dir or resolved.is_relative_to(nexus_status_dir) or any(p == "nexus-status" for p in parts):
                        errors.append(
                            f"FAIL: forbidden cross-workspace import in {rel_file}: {target} "
                            "(frontend cannot import nexus-status, ADR 0024)"
                        )
                    elif not resolved.is_relative_to(frontend_dir):
                        errors.append(
                            f"FAIL: relative import escapes frontend workspace in {rel_file}: {target} "
                            "(ADR 0024)"
                        )
                else:
                    pkg = Path(target).parts[0] if target else ""
                    if pkg in forbidden_pkg_in_frontend or pkg.startswith("@nexus-status"):
                        errors.append(
                            f"FAIL: forbidden cross-workspace import in {rel_file}: {target} "
                            "(frontend cannot import nexus-status, ADR 0024)"
                        )

    # 3. Check imports in nexus-status/frontend/src
    if status_src.exists():
        for f in status_src.rglob("*"):
            if f.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            content = f.read_text(encoding="utf-8")
            for match in TS_IMPORT_PATTERN.finditer(content):
                target = (match.group(1) or match.group(2) or "").strip()
                rel_file = f.relative_to(repo_root)

                if target.startswith("."):
                    resolved = (f.parent / target).resolve()
                    parts = Path(target).parts
                    if resolved == frontend_dir or resolved.is_relative_to(frontend_dir):
                        errors.append(
                            f"FAIL: forbidden cross-workspace import in {rel_file}: {target} "
                            "(nexus-status cannot import frontend, ADR 0024)"
                        )
                    elif resolved == backend_dir or resolved.is_relative_to(backend_dir):
                        errors.append(
                            f"FAIL: forbidden cross-workspace import in {rel_file}: {target} "
                            "(nexus-status cannot import backend, ADR 0024)"
                        )
                    elif any(p in ("frontend", "backend") for p in parts):
                        errors.append(
                            f"FAIL: forbidden cross-workspace import in {rel_file}: {target} "
                            "(nexus-status cannot import core backend/frontend, ADR 0024)"
                        )
                    elif not resolved.is_relative_to(status_frontend_dir):
                        errors.append(
                            f"FAIL: relative import escapes nexus-status workspace in {rel_file}: {target} "
                            "(ADR 0024)"
                        )
                else:
                    pkg = Path(target).parts[0] if target else ""
                    if pkg in forbidden_pkg_in_status or pkg.startswith(("@frontend", "@backend")):
                        errors.append(
                            f"FAIL: forbidden cross-workspace import in {rel_file}: {target} "
                            "(nexus-status cannot import core backend/frontend, ADR 0024)"
                        )


def check_javascript_typescript_workspace_scope(errors: list[str], repo_root: Path = REPO_ROOT) -> None:
    """Enforces that all JavaScript and TypeScript source files in the repository
    reside strictly within approved frontend client workspaces (ADR 0021 & ADR 0024).

    Nexus core backend is strictly Python (backend/src/main).
    Client presentation code is restricted to:
      - frontend/ (Nexus client SPA)
      - nexus-status/frontend/ (Scientific Verification Dashboard SPA)

    If any JS/TS source code is introduced outside these client SPA workspaces
    (e.g., in backend/, root, or new backend services), this check fails fast.
    This guarantees that Sonar's Jasmin bypass (sonar.jasmin.internal.disabled=true),
    which is scoped for pure browser SPAs without server taint sources, cannot
    accidentally leave server-side JS/TS uninspected without explicit architectural review.
    """
    allowed_workspace_roots = [
        repo_root / "frontend",
        repo_root / "nexus-status" / "frontend",
    ]
    ignored_dir_names = {
        "node_modules",
        "dist",
        "coverage",
        "__pycache__",
        "venv",
        ".venv",
    }
    js_ts_extensions = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

    # Compiled static web assets served by backend FastAPI (backend/static/assets/*.js)
    # are generated build artifacts, not source code.
    allowed_static_dir = repo_root / "backend" / "static"

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in js_ts_extensions:
            continue
        # Skip hidden/dot directories (.git, .venv, .scannerwork, etc.) and vendor/build artifacts
        if any(part.startswith(".") or part in ignored_dir_names for part in path.parts[:-1]):
            continue
        if path.is_relative_to(allowed_static_dir):
            continue
        if not any(path.is_relative_to(root) for root in allowed_workspace_roots):
            rel_file = path.relative_to(repo_root)
            errors.append(
                f"FAIL: JS/TS file found outside approved client frontend workspaces: {rel_file}. "
                "Nexus architecture restricts JS/TS strictly to client browser SPAs (frontend/, nexus-status/frontend/). "
                "Any server-side or auxiliary JS/TS introduces potential security surface and requires "
                "explicit architectural review and Sonar taint analysis re-evaluation (ADR 0021)."
            )


def check_import_linter_contracts(errors: list[str]) -> None:
    """Runs import-linter to verify declared architectural contracts in .importlinter."""
    config_file = REPO_ROOT / ".importlinter"
    if not config_file.exists():
        errors.append("FAIL: .importlinter configuration file is missing at repository root.")
        return

    backend_src_main = str(REPO_ROOT / "backend" / "src" / "main")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_src_main}:{existing_pythonpath}" if existing_pythonpath else backend_src_main

    try:
        proc = subprocess.run(
            ["lint-imports", "--no-logo"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            output = (proc.stdout + "\n" + proc.stderr).strip()
            errors.append(f"FAIL: import-linter contract violation:\n{output}")
    except FileNotFoundError:
        errors.append("FAIL: 'lint-imports' command not found. Ensure 'import-linter' is installed in requirements-dev.txt.")


def main() -> int:
    errors: list[str] = []

    check_forbidden_directories(errors)
    check_backend_files(errors)
    check_frontend_files(errors)
    check_backend_layer_dependencies(errors)
    check_frontend_layer_dependencies(errors)
    check_monorepo_boundaries(errors)
    check_javascript_typescript_workspace_scope(errors)
    check_import_linter_contracts(errors)

    if errors:
        print("\n" + "=" * 70, file=sys.stderr)
        print("ARCHITECTURE QUALITY GATE VIOLATIONS:", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        return 1

    print("Architecture check: PASS (Clean Architecture 3-Tier Layer Invariants & Import Linter Contracts Validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
