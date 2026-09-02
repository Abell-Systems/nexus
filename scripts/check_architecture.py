#!/usr/bin/env python3
"""Deterministic Architecture Checker for Nexus 2.0 Clean Architecture.

Enforces:
1. Canonical directory structure:
   - backend/src/main/{domain,application,infrastructure}
   - backend/test/{unit,integration,e2e}
   - frontend/src/main/{domain,application,infrastructure}
   - frontend/test/{unit,integration,e2e}
2. Forbidden legacy directories (nexus, backend/patent_agent, backend/tests, interfaces).
3. No production code outside src/main/.
4. Strict unidirectional layer imports (AST inspection):
   - domain cannot import application, infrastructure, or heavy external frameworks (FastAPI, Google ADK).
   - application cannot import infrastructure or Google ADK.
"""

import ast
import os
from pathlib import Path
import sys

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

    # Check backend/test folders
    backend_test = backend_dir / "test"
    if backend_test.exists():
        allowed_test = {"unit", "integration", "e2e", "fixtures", "__init__.py", "__pycache__"}
        for item in backend_test.iterdir():
            if item.name.startswith("."):
                continue
            if item.name not in allowed_test:
                errors.append(f"FAIL: invalid folder in backend/test: {item.name}")


def check_frontend_files(errors: list[str]) -> None:
    frontend_dir = REPO_ROOT / "frontend"
    if not frontend_dir.exists():
        return

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


def check_layer_dependencies(errors: list[str]) -> None:
    backend_main = REPO_ROOT / "backend" / "src" / "main"
    if not backend_main.exists():
        return

    for py_file in backend_main.rglob("*.py"):
        rel_path = py_file.relative_to(backend_main)
        parts = rel_path.parts
        if not parts:
            continue

        layer = parts[0]
        if layer not in ("domain", "application", "infrastructure"):
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

            # Domain Layer Invariants
            if layer == "domain":
                if mod.startswith("application") or mod.startswith(".application"):
                    errors.append(
                        f"FAIL: forbidden dependency: {rel_file}:{lineno} (domain imports application: {mod})"
                    )
                if mod.startswith("infrastructure") or mod.startswith(".infrastructure"):
                    errors.append(
                        f"FAIL: forbidden dependency: {rel_file}:{lineno} (domain imports infrastructure: {mod})"
                    )
                if any(mod.startswith(fw) for fw in ("fastapi", "google.adk", "duckdb", "pyarrow")):
                    errors.append(
                        f"FAIL: forbidden dependency: {rel_file}:{lineno} (domain imports framework: {mod})"
                    )

            # Application Layer Invariants
            if layer == "application":
                if mod.startswith("infrastructure") or mod.startswith(".infrastructure"):
                    errors.append(
                        f"FAIL: forbidden dependency: {rel_file}:{lineno} (application imports infrastructure: {mod})"
                    )
                if mod.startswith("google.adk") or mod.startswith("fastapi"):
                    errors.append(
                        f"FAIL: forbidden dependency: {rel_file}:{lineno} (application imports framework: {mod})"
                    )


def main() -> int:
    errors: list[str] = []

    check_forbidden_directories(errors)
    check_backend_files(errors)
    check_frontend_files(errors)
    check_layer_dependencies(errors)

    if errors:
        print("\n" + "=" * 70, file=sys.stderr)
        print("ARCHITECTURE QUALITY GATE VIOLATIONS:", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        return 1

    print("Architecture check: PASS (Clean Architecture 3-Tier Layer Invariants Validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
