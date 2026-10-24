import json

import pytest
from tss_client import poll_once


class FakeSocket:
    """Pretends to be the network. Remembers what was sent, answers with a canned reply."""

    def __init__(self, reply=b"", error=None):
        self.reply = reply      # bytes the pretend TSS answers with
        self.error = error      # if set, recv raises this instead of answering
        self.sent = []          # everything we sent, so the test can check it

    def sendto(self, request, address):
        self.sent.append((bytes(request), address))

    def recv(self, size):
        if self.error:
            raise self.error
        return self.reply


def test_good_reply_is_parsed():
    reply = json.dumps({"telemetry": {"oxy_pri_storage": 98.9}}).encode()
    sock = FakeSocket(reply=reply)

    data = poll_once(sock, ("1.2.3.4", 14142))

    assert data["telemetry"]["oxy_pri_storage"] == 98.9
    assert sock.sent == [(bytes(8), ("1.2.3.4", 14142))]   # 8 zero bytes, right address


def test_garbage_reply_raises_value_error():
    sock = FakeSocket(reply=b"not json at all")

    with pytest.raises(ValueError):
        poll_once(sock, ("1.2.3.4", 14142))


def test_timeout_raises_os_error():
    sock = FakeSocket(error=TimeoutError("timed out"))

    with pytest.raises(OSError):
        poll_once(sock, ("1.2.3.4", 14142))