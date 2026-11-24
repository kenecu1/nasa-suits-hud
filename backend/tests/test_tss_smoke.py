"""scripts/tss_smoke.py against the fake TSS. The real TSS run is manual (acceptance 16)."""

import asyncio
import importlib.util

import pytest

from suits.contract import LinkStatus
from suits.paths import REPO_ROOT
from suits.sim.fake_tss import FakeTss
from suits.tss import codec
from suits.tss.client import TssAddress, TssClient
from suits.tss.recorder import Recorder, read_recording
from suits.tss.source import TssSource
from tests.helpers import wait_until

_spec = importlib.util.spec_from_file_location("tss_smoke", REPO_ROOT / "scripts" / "tss_smoke.py")
assert _spec is not None and _spec.loader is not None
tss_smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tss_smoke)


def address_of(fake: FakeTss) -> TssAddress:
    return TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port)


async def test_smoke_prints_decoded_dcu_uia_and_telemetry_and_exits_0(capsys):
    async with FakeTss() as fake:
        code = await tss_smoke.smoke(address_of(fake), seconds=2.5, every_s=0.5)

    out = capsys.readouterr().out
    assert code == 0, out
    assert "link: ok" in out
    assert "DCU: " in out and "oxy=PRI" in out
    assert "UIA: " in out and "eva_power=" in out
    assert f"oxy_pri_storage={fake.state['telemetry']['oxy_pri_storage']}" in out
    assert "OK: DCU, UIA and telemetry decoded, link ok." in out
    assert "Not received yet" not in out


async def test_smoke_passes_while_the_slow_sections_are_still_on_their_way(capsys):
    # The real TSS serves about one legacy request per 1.2 s, so status and faults take
    # about 7 s. A 5 s run must not fail on a healthy link (seen against the real TSS).
    async with FakeTss(legacy_service_s=1.0) as fake:
        code = await tss_smoke.smoke(address_of(fake), seconds=2.6, every_s=0.5)

    out = capsys.readouterr().out
    assert code == 0, out
    assert "OK: DCU, UIA and telemetry decoded, link stale." in out
    assert "Not received yet: status, faults" in out


async def test_smoke_fails_and_names_an_expected_telemetry_name_that_is_missing(capsys):
    # decision A in docs/briefs/M2.md: a renamed TSS field must make the smoke test fail
    async with FakeTss() as fake:
        fake.state["telemetry"]["primary_oxygen"] = fake.state["telemetry"].pop("oxy_pri_storage")
        code = await tss_smoke.smoke(address_of(fake), seconds=2.5, every_s=0.5)

    out = capsys.readouterr().out
    assert code == 1, out
    assert "FAILED: link is bad_data" in out
    assert "telemetry names oxy_pri_storage" in out
    assert "RENAMED" in out


async def test_smoke_fails_when_required_data_stops_arriving(capsys):
    async with FakeTss() as fake:
        task = asyncio.ensure_future(tss_smoke.smoke(address_of(fake), seconds=4.5, every_s=0.5))
        await asyncio.sleep(1.0)
        fake.silent = True  # everything arrived once, then the TSS went quiet
        code = await task

    out = capsys.readouterr().out
    assert code == 1, out
    assert "FAILED: link is unreachable" in out
    assert "missing DCU, UIA" in out


async def test_a_required_section_that_went_old_is_reported_with_its_age():
    # Telemetry stopped while DCU and UIA still arrive: the link is "stale", which alone is
    # not a failure (see the slow-sections test), so the age check has to catch it.
    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(source, address_of(fake))
        client.start()
        try:
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=5)
            healthy = source.snapshot()
        finally:
            await client.stop()

    assert tss_smoke.missing(healthy) == []
    old = healthy.model_copy(update={"ages": {**healthy.ages, "telemetry": 9.0}})
    assert tss_smoke.missing(old) == ["telemetry (last seen 9.0 s ago)"]
    never = healthy.model_copy(update={"dcu": None})
    assert tss_smoke.missing(never) == ["DCU"]


async def test_smoke_fails_and_says_why_when_the_ip_is_not_assigned(capsys):
    async with FakeTss() as fake:
        fake.ack_result = codec.AckResult.UNASSIGNED
        code = await tss_smoke.smoke(address_of(fake), seconds=1.5, every_s=0.5)

    out = capsys.readouterr().out
    assert code == 1
    assert "FAILED: link is unassigned" in out
    assert "missing DCU, UIA" in out
    assert "not assigned to a team" in out


async def test_smoke_fails_when_nothing_answers(capsys):
    async with FakeTss() as fake:
        fake.silent = True
        code = await tss_smoke.smoke(address_of(fake), seconds=1.0, every_s=0.5)

    out = capsys.readouterr().out
    assert code == 1
    assert "FAILED: link is unreachable" in out
    assert "missing DCU, UIA, telemetry" in out


async def test_smoke_can_record_raw_datagrams(tmp_path, capsys):
    recorder = Recorder(tmp_path / "rec.jsonl")
    async with FakeTss() as fake:
        try:
            await tss_smoke.smoke(address_of(fake), seconds=1.5, every_s=0.5, recorder=recorder)
        finally:
            recorder.close()

    capsys.readouterr()
    datagrams = list(read_recording(tmp_path / "rec.jsonl"))
    assert {d.dir for d in datagrams} == {"in", "out"}
    assert recorder.count == len(datagrams) > 0


def test_a_new_recording_never_appends_to_an_existing_file(tmp_path):
    first = tss_smoke.recording_path(tmp_path)
    assert first.name == f"real-tss-{tss_smoke.pinned_commit()}.jsonl"
    first.write_text("{}\n", encoding="utf-8")

    second = tss_smoke.recording_path(tmp_path)
    assert second != first
    assert second.name.startswith(first.stem + "-") and not second.exists()


def test_main_needs_a_host(monkeypatch, capsys):
    monkeypatch.delenv("TSS_HOST", raising=False)
    with pytest.raises(SystemExit) as stopped:
        tss_smoke.main([])
    assert stopped.value.code == 2
    assert "TSS_HOST" in capsys.readouterr().err


def test_main_refuses_a_run_of_no_length(capsys):
    with pytest.raises(SystemExit) as stopped:
        tss_smoke.main(["--host", "127.0.0.1", "--seconds", "0"])
    assert stopped.value.code == 2
    assert "--seconds" in capsys.readouterr().err


def test_every_link_status_except_ok_has_a_hint():
    assert set(tss_smoke.HINTS) == set(LinkStatus) - {LinkStatus.OK}
