On Windows, an asyncio UDP socket on the Proactor event loop stops receiving for good after one "port unreachable" error, while still looking open; close it and open a new one.

Found in M1 review (2026-11-16) on Python 3.12, and confirmed by `tests/tss/test_link_resilience.py::test_link_recovers_when_the_tss_starts_after_the_backend`, which fails without the fix.

- Trigger: sending to a port where nothing listens (backend started before the TSS, TSS restarted, or the fake TSS pushing to a client socket that closed). The OS reports ICMP "port unreachable" to the socket.
- Proactor calls `error_received` once, does not call `connection_lost`, `is_closing()` stays False, and no further datagram is ever delivered. The Selector loop keeps receiving. uvicorn uses Proactor on Windows.
- Fix used: `UdpEndpoint.error_received` closes the endpoint; `Subscription` and `LegacyPoller` reopen after `reopen_after_s` (`suits/tss/transport.py`). The fake TSS rebinds its port on an error.
- `socket.ioctl(SIO_UDP_CONNRESET)` would stop Windows reporting the error, but Python's `socket.ioctl` does not accept that code.
