"""Build captured-tss.jsonl: a recording made from real captured bytes, not from a live run.

Binary packets are the captures in docs/notes/tss-packet-format.md; legacy replies use the
telemetry, status and error sections of the first lines of legacy-sample.jsonl (a real TSS run).
It also contains one packet with a bad checksum and one bad JSON reply, so replay covers the
bad_data path. Kept until a real 60 s recording replaces it as the main replay fixture.

Run from the repo root:  .venv/Scripts/python backend/tests/fixtures/build_captured_recording.py
"""

import json
from pathlib import Path

from suits.tss import codec
from suits.tss.recorder import Datagram

HERE = Path(__file__).parent
OUT = HERE / "captured-tss.jsonl"
T0 = 1794700000.0

SUBSCRIBE_DCU = bytes.fromhex("6af55d2c000d000f00010001ec")
ACK_OK = bytes.fromhex("6af55d33000c000f000400f6")
DCU_ZEROS = bytes.fromhex("6af55d34001100010003000000000000e5")
UIA = bytes.fromhex("6af55d340017000200030000000000000000a0536a354c")


def legacy_reply(section: dict) -> bytes:
    return json.dumps(section, indent="\t").encode("utf-8")  # the TSS pretty-prints with tabs


def main() -> None:
    sample = [json.loads(line)["eva"] for line in
              (HERE / "legacy-sample.jsonl").read_text(encoding="utf-8").splitlines()[:6]]
    rows: list[Datagram] = []

    def add(dt: float, direction: str, channel: str, data: bytes) -> None:
        rows.append(Datagram(T0 + dt, direction, channel, data))

    add(0.00, "out", "sub", SUBSCRIBE_DCU)
    add(0.01, "in", "sub", ACK_OK)
    add(0.02, "out", "sub", codec.build_subscribe(0x6AF55D2C, codec.Device.UIA))
    add(0.03, "in", "sub", ACK_OK)

    dcu_oxy_pri = codec.build_telemetry(0x6AF55D37, codec.Device.DCU,
                                        codec.encode_dcu(codec.DcuFlags(0, 1, 0, 0, 0, 0)))
    for second, eva in enumerate(sample):
        base = 0.1 + second
        for offset, (command, section) in enumerate([(1, "telemetry"), (2, "status"), (4, "error")]):
            channel = f"legacy/{command}"
            add(base + 0.001 * offset, "out", channel, codec.build_legacy_get(0x6AF55D2C, command))
            reply = legacy_reply(eva[section])
            if second == 4 and command == 1:
                reply = reply[: len(reply) // 2]  # truncated JSON
            add(base + 0.02 + 0.001 * offset, "in", channel, reply)
        add(base + 0.5, "in", "sub", DCU_ZEROS if second < 3 else dcu_oxy_pri)
        add(base + 0.51, "in", "sub", UIA)
        if second == 2:
            add(base + 0.6, "in", "sub", DCU_ZEROS[:-1] + bytes([DCU_ZEROS[-1] ^ 0xFF]))

    OUT.write_text("".join(r.to_json() + "\n" for r in rows), encoding="utf-8", newline="\n")
    print(f"wrote {len(rows)} datagrams to {OUT}")


if __name__ == "__main__":
    main()
