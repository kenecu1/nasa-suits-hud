"""Acceptance 10: `npm run contract -- --check` fails when contract.gen.ts is out of date.

Runs the real script (scripts/contract.mjs) on copies of the generated file, so the committed
file is never touched. Needs Node, which `npm run setup` already requires.
"""

import shutil
import subprocess

from suits.paths import REPO_ROOT

GENERATED = REPO_ROOT / "client" / "src" / "contract.gen.ts"
SCRIPT = REPO_ROOT / "scripts" / "contract.mjs"
NODE = shutil.which("node") or "node"  # required: a missing node fails these tests


def check(path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [NODE, str(SCRIPT), "--check", "--out", str(path)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )


def test_committed_file_is_up_to_date():
    result = check(GENERATED)

    assert result.returncode == 0, result.stderr


def test_an_out_of_date_file_fails_the_check(tmp_path):
    stale = tmp_path / "contract.gen.ts"
    text = GENERATED.read_text(encoding="utf-8")
    stale.write_text(text.replace("  seq: number;\n", "  seq: string;\n"), encoding="utf-8")
    assert stale.read_text(encoding="utf-8") != text  # the edit really happened

    result = check(stale)

    assert result.returncode == 1
    assert "out of date" in result.stderr


def test_a_missing_file_fails_the_check(tmp_path):
    result = check(tmp_path / "nothing.ts")

    assert result.returncode == 1
    assert "missing" in result.stderr


def test_line_endings_alone_are_not_drift(tmp_path):
    crlf = tmp_path / "contract.gen.ts"
    crlf.write_bytes(GENERATED.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))

    assert check(crlf).returncode == 0
