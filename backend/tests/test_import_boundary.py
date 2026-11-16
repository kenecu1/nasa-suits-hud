"""Acceptance 7: only suits/tss and suits/sim may touch TSS wire code.

Everything else reads TssSnapshot (through suits.tss.source / client / recorder), so a TSS
protocol change stays inside the adapter.
"""

import ast
from pathlib import Path

from suits.paths import REPO_ROOT

FORBIDDEN = {"suits.tss.codec", "suits.tss.subscription", "suits.tss.legacy"}
SUITS = REPO_ROOT / "backend" / "suits"
ALLOWED_DIRS = (SUITS / "tss", SUITS / "sim")
CHECKED = [*SUITS.rglob("*.py"), *(REPO_ROOT / "scripts").rglob("*.py")]


BACKEND = REPO_ROOT / "backend"


def _absolute(node: ast.ImportFrom, path: Path, root: Path) -> str | None:
    """The absolute module a "from" import names, resolving "." and ".." from the file's place
    under root (backend/ for real files). None if it cannot be resolved."""
    if node.level == 0:
        return node.module
    if not path.is_relative_to(root):
        return None
    package = list(path.relative_to(root).with_suffix("").parts[:-1])  # the file's package
    up = node.level - 1
    if up > len(package):
        return None
    base = package[: len(package) - up]
    return ".".join([*base, *([node.module] if node.module else [])])


def imported_modules(path: Path, root: Path = BACKEND) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _absolute(node, path, root)
            if not module:
                continue
            found.add(module)
            # "from suits.tss import codec" imports the module suits.tss.codec
            found.update(f"{module}.{alias.name}" for alias in node.names)
    return found


def violations(paths: list[Path], root: Path = BACKEND) -> list[str]:
    bad = []
    for path in paths:
        if any(path.is_relative_to(d) for d in ALLOWED_DIRS):
            continue
        for module in sorted(imported_modules(path, root) & FORBIDDEN):
            bad.append(f"{path.name} imports {module}")
    return bad


def test_nothing_outside_tss_and_sim_imports_wire_modules():
    assert len(CHECKED) > 5, "too few files found: wrong path?"
    assert violations(CHECKED) == []


def test_the_check_catches_each_import_style(tmp_path):
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from suits.tss import codec\n"
        "import suits.tss.legacy\n"
        "from suits.tss.subscription import Subscription\n",
        encoding="utf-8",
    )

    assert violations([offender]) == [
        "offender.py imports suits.tss.codec",
        "offender.py imports suits.tss.legacy",
        "offender.py imports suits.tss.subscription",
    ]


def test_the_check_catches_relative_imports(tmp_path):
    # a fake package tree, so "." and ".." resolve the way they would inside backend/
    core = tmp_path / "suits" / "core"
    core.mkdir(parents=True)
    top = tmp_path / "suits" / "offender_top.py"
    top.write_text("from .tss import codec\n", encoding="utf-8")
    deep = core / "offender_deep.py"
    deep.write_text(
        "from ..tss.codec import decode\nfrom .. import tss\nfrom ..tss import legacy\n",
        encoding="utf-8",
    )

    assert violations([top, deep], root=tmp_path) == [
        "offender_top.py imports suits.tss.codec",
        "offender_deep.py imports suits.tss.codec",
        "offender_deep.py imports suits.tss.legacy",
    ]


def test_tss_and_sim_are_allowed():
    allowed = [SUITS / "tss" / "client.py", SUITS / "sim" / "fake_tss.py"]

    assert violations(allowed) == []


def tss_names() -> set[str]:
    """Every TSS telemetry name: data/ranges.json lists them all."""
    from suits.core.levels import load_ranges

    ranges = load_ranges()
    return set(ranges["ranges"]) | set(ranges["unranged"])


def string_constants(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def test_no_tss_field_name_is_written_outside_tss_and_sim():
    names = tss_names()
    bad = [
        f"{path.name}: {sorted(string_constants(path) & names)}"
        for path in CHECKED
        if not any(path.is_relative_to(d) for d in ALLOWED_DIRS) and string_constants(path) & names
    ]

    assert bad == []
