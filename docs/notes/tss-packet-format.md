New TSS packets (UDP 14141, both directions) are: 10-byte big-endian header, data, 1-byte XOR checksum; real captured packets are below for test fixtures.

Source: `src/network.c`, `src/groups.c`, `src/data.c` at commit 6293795, plus a live run.

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | Unix timestamp, uint32 |
| 4 | 2 | total length (header + data + checksum), uint16 |
| 6 | 2 | device ID, uint16 |
| 8 | 2 | message code, uint16 |
| 10 | n | data |
| 10+n | 1 | checksum = XOR of every byte before it |

The server drops a packet if it is shorter than 11 bytes, if the length field differs from the datagram size, if the checksum is wrong, or if the device ID we send is not 15.

- Device IDs: 1 DCU, 2 UIA, 3 SPM, 4 SSU, 5 CTS, 6 XRF, 15 team device (always use 15 when sending).
- Codes: 1 Subscribe (data = uint16 device ID), 2 Unsubscribe (no data), 3 Telemetry (server to us; header device ID = the source device), 4 Ack (1 byte: 0 ok, 1 team not assigned, 2 bad device or length).
- Floats are IEEE-754 float32 big-endian.
- Push rate 1 Hz, one packet per subscribed device.
- Replies go to the source IP and port of our last packet: receive on the socket we send from.
- DCU and UIA subscriptions are persistent. SPM/SSU/CTS/XRF share one slot: a new one replaces the old. Unsubscribe clears only that slot.
- No keepalive. Re-send Subscribe until an Ack arrives (UDP can drop it).

**Captured packets (hex):**

| What | Bytes |
|---|---|
| Subscribe to DCU (we send) | `6af55d2c000d000f00010001ec` |
| Ack ok | `6af55d33000c000f000400f6` |
| DCU telemetry, all six flags 0 | `6af55d34001100010003000000000000e5` |
| UIA telemetry (6 valid + 6 garbage bytes) | `6af55d340017000200030000000000000000a0536a354c` |
| SSU telemetry, idle (both drill temps −25.0) | `6af55d34002c0004000300000000000000000000c1c800000000000000000000000000c1c8000000000000dd` |

The README's own example packet is wrong (it says length `000a`; a Subscribe is 13 bytes, `000d`).

Payload layouts: [tss-readme-payload-sizes-wrong](tss-readme-payload-sizes-wrong.md).
