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


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            # "from suits.tss import codec" imports the module suits.tss.codec
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def violations(paths: list[Path]) -> list[str]:
    bad = []
    for path in paths:
        if any(path.is_relative_to(d) for d in ALLOWED_DIRS):
            continue
        for module in sorted(imported_modules(path) & FORBIDDEN):
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
