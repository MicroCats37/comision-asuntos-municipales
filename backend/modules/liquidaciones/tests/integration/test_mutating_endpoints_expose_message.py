"""
Contract test: every mutating endpoint must expose a top-level `message`.

Contrato de referencia
----------------------
`contract/next-app-architecture-contract.md` §11 exige que el envelope de
éxito exponga `message: string` en el primer nivel. El frontend consume ese
campo (ver `frontend/src/errors/success-message.ts`), por lo que un endpoint
mutante sin mensaje deja al usuario sin feedback.

Qué verifica
-------------
Se analiza el código fuente de los controllers (análisis estático con `ast`):
todo endpoint que muta estado (POST / PATCH / PUT / DELETE) debe llamar a
`success_response(...)` con un `message` no vacío.

Excepciones (silenciosas por diseño)
------------------------------------
- `/auth/login/*`: el login no emite mensaje de éxito (AS-7 del Explore).
- Rutas `cotizar` / `cotizar-edicion`: son previews, no mutan estado.
"""
import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[4]
MODULES_ROOT = BACKEND_ROOT / "modules"

MUTATING_METHODS = {"post", "patch", "put", "delete"}

EXCLUDED_PATH_FRAGMENTS = ("cotizar", "/auth/login")


def _controller_files():
    return sorted(MODULES_ROOT.glob("*/presentation/controllers/**/*.py"))


def _api_controller_prefix(tree: ast.Module) -> str:
    """Return the prefix declared by the module level `@api_controller("...")`."""
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "api_controller":
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    value = decorator.args[0].value
                    if isinstance(value, str):
                        return value
    return ""


def _route_path(decorator: ast.expr) -> str | None:
    """Return the HTTP path of a `@route.<mutating>("...")` decorator."""
    if not isinstance(decorator, ast.Call):
        return None

    func = decorator.func
    if not isinstance(func, ast.Attribute) or func.attr not in MUTATING_METHODS:
        return None

    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value

    return None


def _has_non_empty_message(call: ast.Call) -> bool:
    """True when `success_response(...)` carries a non-empty message."""
    for keyword in call.keywords:
        if keyword.arg == "message":
            value = keyword.value
            return (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and bool(value.value.strip())
            )

    if len(call.args) >= 2:
        value = call.args[1]
        return (
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and bool(value.value.strip())
        )

    return False


def _mutating_endpoints_without_message():
    """Collect (file, path) of mutating endpoints without a top-level message."""
    violations = []
    scanned = []

    for path in _controller_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        prefix = _api_controller_prefix(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            routes = [
                route
                for route in (
                    _route_path(decorator) for decorator in node.decorator_list
                )
                if route is not None
            ]
            if not routes:
                continue

            full_paths = [f"{prefix}{route}" for route in routes]
            if any(
                fragment in full_path
                for full_path in full_paths
                for fragment in EXCLUDED_PATH_FRAGMENTS
            ):
                continue

            scanned.append((path, full_paths))

            success_calls = [
                child
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "success_response"
            ]

            if not success_calls:
                violations.append((path, full_paths, "sin success_response()"))
            elif not any(_has_non_empty_message(call) for call in success_calls):
                violations.append(
                    (path, full_paths, "success_response() sin message no vacío")
                )

    return violations, scanned


def test_mutating_endpoints_expose_a_top_level_message():
    """
    GIVEN: todos los controllers de la API CAM
    WHEN: se revisan los endpoints que mutan estado
    THEN: cada uno expone un `message` de primer nivel no vacío
    """
    violations, scanned = _mutating_endpoints_without_message()

    # Guarda contra falsos positivos: si el escaneo no encuentra endpoints, el
    # test no debe pasar en verde por vacío.
    assert len(scanned) >= 40, (
        f"Se esperaban al menos 40 endpoints mutantes, se escanearon {len(scanned)}. "
        "Revisar el glob de controllers."
    )

    if violations:
        details = "\n".join(
            f"  - {path.relative_to(BACKEND_ROOT)} :: {paths} → {reason}"
            for path, paths, reason in violations
        )
        pytest.fail(
            "Endpoints mutantes sin `message` de primer nivel "
            "(contract/next-app-architecture-contract.md §11):\n" + details
        )
