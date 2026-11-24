import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Command, State } from "../contract.gen";
import type { Conn } from "../hud/types";
import { backoffMs, SILENCE_MS, startLink, type SocketLike } from "./link";

class FakeSocket implements SocketLike {
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  readyState = 1;
  sent: string[] = [];
  failSend = false;

  constructor(readonly url: string) {}

  send(data: string): void {
    if (this.failSend) throw new Error("socket is closing");
    this.sent.push(data);
  }

  close(): void {
    this.closed = true;
  }
  open(): void {
    this.onopen?.();
  }
  message(data: unknown): void {
    this.onmessage?.({ data });
  }
  serverClose(): void {
    this.onclose?.();
  }
  fail(): void {
    this.onerror?.();
  }
}

function makeState(seq = 1): State {
  return {
    type: "state",
    v: 2,
    seq,
    t: 100,
    link: { tss: "ok", age_s: 0.2, mode: "sim", level: "nominal" },
    eva: { started: false, elapsed_s: 0, phase: null },
    suit: { values: { oxy_pri_storage: { value: 92, unit: "%", level: "nominal" } }, faults: null },
    dcu: { batt: "LOCAL", oxy: "PRI", comm: "A", fan: "PRI", pump: "OPEN", co2: "A" },
    uia: null,
    alerts: [],
    ui: { details_open: false },
  };
}

const msg = (seq = 1): string => JSON.stringify(makeState(seq));
const WS_URL = "ws://localhost:5173/ws";

function setup() {
  const sockets: FakeSocket[] = [];
  const onState = vi.fn<(state: State) => void>();
  const onConn = vi.fn<(conn: Conn) => void>();
  const link = startLink({
    url: WS_URL,
    onState,
    onConn,
    makeSocket: (url) => {
      const socket = new FakeSocket(url);
      sockets.push(socket);
      return socket;
    },
  });
  const sock = (index: number): FakeSocket => {
    const socket = sockets[index];
    if (socket === undefined) throw new Error(`no socket ${index}`);
    return socket;
  };
  return { sockets, sock, onState, onConn, link };
}

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("backoffMs", () => {
  it.each([
    [0, 500],
    [1, 1000],
    [2, 2000],
    [3, 4000],
    [4, 5000],
    [5, 5000],
    [20, 5000],
  ])("attempt %i waits %i ms", (attempt, ms) => {
    expect(backoffMs(attempt)).toBe(ms);
  });
});

describe("startLink", () => {
  it("creates one socket for the url at once and does not call onConn", () => {
    const { sockets, onConn, onState } = setup();
    expect(sockets).toHaveLength(1);
    expect(sockets[0]?.url).toBe(WS_URL);
    expect(onConn).not.toHaveBeenCalled();
    expect(onState).not.toHaveBeenCalled();
  });

  it("delivers a valid state and goes live once", () => {
    const { sock, onState, onConn } = setup();
    sock(0).message(msg(1));
    sock(0).message(msg(2));
    expect(onState).toHaveBeenCalledTimes(2);
    expect(onState).toHaveBeenNthCalledWith(1, makeState(1));
    expect(onConn).toHaveBeenCalledTimes(1);
    expect(onConn).toHaveBeenCalledWith("live");
  });

  it("goes offline on close and reconnects after exactly 500 ms", () => {
    const { sockets, sock, onConn } = setup();
    sock(0).serverClose();
    expect(onConn).toHaveBeenCalledWith("offline");
    vi.advanceTimersByTime(499);
    expect(sockets).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(2);
  });

  it("waits longer after each close without a valid message", () => {
    const { sockets, sock } = setup();
    [500, 1000, 2000, 4000, 5000, 5000].forEach((delay, i) => {
      sock(i).serverClose();
      vi.advanceTimersByTime(delay - 1);
      expect(sockets).toHaveLength(i + 1);
      vi.advanceTimersByTime(1);
      expect(sockets).toHaveLength(i + 2);
    });
  });

  it("does not reset the backoff or go live when a socket only opens", () => {
    const { sockets, sock, onConn } = setup();
    sock(0).open();
    expect(onConn).not.toHaveBeenCalled();
    sock(0).serverClose();
    vi.advanceTimersByTime(500);
    sock(1).open();
    expect(onConn).not.toHaveBeenCalledWith("live");
    sock(1).serverClose();
    vi.advanceTimersByTime(999);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(3);
  });

  it("resets the backoff after a valid message", () => {
    const { sockets, sock } = setup();
    sock(0).serverClose();
    vi.advanceTimersByTime(500);
    sock(1).serverClose();
    vi.advanceTimersByTime(1000);
    sock(2).message(msg());
    sock(2).serverClose();
    vi.advanceTimersByTime(499);
    expect(sockets).toHaveLength(3);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(4);
  });

  it("goes live again and delivers state on the new socket after a reconnect", () => {
    const { sock, onState, onConn } = setup();
    sock(0).message(msg(1));
    sock(0).serverClose();
    vi.advanceTimersByTime(500);
    sock(1).message(msg(2));
    expect(onConn.mock.calls.map(([conn]) => conn)).toEqual(["live", "offline", "live"]);
    expect(onState).toHaveBeenLastCalledWith(makeState(2));
  });

  it("treats SILENCE_MS without a valid message since creation as offline and abandons the socket", () => {
    const { sockets, sock, onConn } = setup();
    vi.advanceTimersByTime(SILENCE_MS - 1);
    expect(onConn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onConn).toHaveBeenCalledWith("offline");
    expect(sock(0).closed).toBe(true);
    vi.advanceTimersByTime(499);
    expect(sockets).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(2);
  });

  it("counts silence from the last valid message", () => {
    const { sock, onConn } = setup();
    vi.advanceTimersByTime(2000);
    sock(0).message(msg());
    vi.advanceTimersByTime(1000);
    expect(onConn).toHaveBeenCalledTimes(1);
    expect(sock(0).closed).toBe(false);
    vi.advanceTimersByTime(1999);
    expect(sock(0).closed).toBe(false);
    vi.advanceTimersByTime(1);
    expect(sock(0).closed).toBe(true);
    expect(onConn).toHaveBeenCalledTimes(2);
    expect(onConn).toHaveBeenLastCalledWith("offline");
  });

  it("ignores a late close and message from a socket the watchdog abandoned", () => {
    const { sockets, sock, onState, onConn } = setup();
    vi.advanceTimersByTime(SILENCE_MS);
    const callsBefore = onConn.mock.calls.length;
    vi.advanceTimersByTime(200);
    sock(0).serverClose();
    sock(0).message(msg());
    expect(onState).not.toHaveBeenCalled();
    expect(onConn).toHaveBeenCalledTimes(callsBefore);
    vi.advanceTimersByTime(300);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(1000);
    expect(sockets).toHaveLength(2);
  });

  it("ignores invalid messages and does not reset the silence timer", () => {
    const { sock, onState, onConn } = setup();
    vi.advanceTimersByTime(2000);
    sock(0).message("not json");
    sock(0).message(JSON.stringify({ ...makeState(), type: "other" }));
    sock(0).message(JSON.stringify({ ...makeState(), v: 3 }));
    sock(0).message(new ArrayBuffer(8));
    expect(onState).not.toHaveBeenCalled();
    expect(onConn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(onConn.mock.calls.map(([conn]) => conn)).toEqual(["offline"]);
    expect(sock(0).closed).toBe(true);
  });

  it("delivers messages whose seq goes down or repeats", () => {
    const { sock, onState } = setup();
    [10, 3, 3].forEach((seq) => sock(0).message(msg(seq)));
    expect(onState.mock.calls.map(([state]) => state.seq)).toEqual([10, 3, 3]);
  });

  it("schedules exactly one reconnect for an error followed by a close", () => {
    const { sockets, sock } = setup();
    sock(0).fail();
    sock(0).serverClose();
    vi.advanceTimersByTime(500);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(499);
    expect(sockets).toHaveLength(2);
  });

  it("a state that cannot be applied does not count as heard: the link goes offline after the silence", () => {
    const { sockets, sock, onState, onConn } = setup();
    sock(0).message(msg(1));
    expect(onConn).toHaveBeenLastCalledWith("live");
    onState.mockImplementation(() => {
      throw new Error("view model blew up");
    });
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});

    // The backend keeps sending every second, but nothing can be shown from it.
    for (let second = 1; second <= 2; second++) {
      vi.advanceTimersByTime(1000);
      expect(() => sock(0).message(msg(1 + second))).not.toThrow();
    }
    expect(onConn).toHaveBeenLastCalledWith("live");
    vi.advanceTimersByTime(1000);
    expect(onConn).toHaveBeenLastCalledWith("offline");
    expect(sock(0).closed).toBe(true);
    expect(logged).toHaveBeenCalled();
    logged.mockRestore();

    // It keeps trying, and recovers once states can be applied again.
    onState.mockImplementation(() => {});
    vi.advanceTimersByTime(500);
    expect(sockets).toHaveLength(2);
    sock(1).message(msg(9));
    expect(onConn).toHaveBeenLastCalledWith("live");
  });

  it("keeps trying when a socket cannot even be created", () => {
    const sockets: FakeSocket[] = [];
    const onConn = vi.fn<(conn: Conn) => void>();
    const onState = vi.fn<(state: State) => void>();
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    let refuse = 2;
    const link = startLink({
      url: WS_URL,
      onState,
      onConn,
      makeSocket: (url) => {
        if (refuse-- > 0) throw new Error("refused");
        const socket = new FakeSocket(url);
        sockets.push(socket);
        return socket;
      },
    });

    expect(onConn).toHaveBeenLastCalledWith("offline");
    vi.advanceTimersByTime(500); // second try, refused again
    expect(sockets).toHaveLength(0);
    vi.advanceTimersByTime(999);
    expect(sockets).toHaveLength(0);
    vi.advanceTimersByTime(1); // third try, 1000 ms later: backoff applies here too
    expect(sockets).toHaveLength(1);
    sockets[0]?.message(msg());
    expect(onConn).toHaveBeenLastCalledWith("live");
    expect(onState).toHaveBeenCalledTimes(1);
    expect(logged).toHaveBeenCalledTimes(2);
    logged.mockRestore();
    link.stop();
  });

  it("a status change that cannot be applied does not count as heard either", () => {
    const { sock, onConn } = setup();
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    onConn.mockImplementation((conn) => {
      if (conn === "live") throw new Error("could not build the panels");
    });

    for (let second = 0; second < 3; second++) {
      expect(() => sock(0).message(msg(second))).not.toThrow();
      vi.advanceTimersByTime(1000);
    }
    // Messages kept coming, but none could be shown: the watchdog still fires at 3 s.
    expect(sock(0).closed).toBe(true);
    expect(logged).toHaveBeenCalled();
    logged.mockRestore();
  });

  it("stop closes the socket, creates no more sockets and fires no callbacks", () => {
    const { sockets, sock, onState, onConn, link } = setup();
    sock(0).message(msg());
    link.stop();
    expect(sock(0).closed).toBe(true);
    onState.mockClear();
    onConn.mockClear();
    sock(0).serverClose();
    sock(0).message(msg(2));
    vi.advanceTimersByTime(60_000);
    expect(sockets).toHaveLength(1);
    expect(onState).not.toHaveBeenCalled();
    expect(onConn).not.toHaveBeenCalled();
  });

  it("stop during a backoff wait cancels the reconnect", () => {
    const { sockets, sock, link } = setup();
    sock(0).serverClose();
    vi.advanceTimersByTime(200);
    link.stop();
    vi.advanceTimersByTime(60_000);
    expect(sockets).toHaveLength(1);
  });
});

describe("send", () => {
  const ack: Command = { type: "command", name: "ack_alert", args: { id: "fan" } };

  it("sends a command as JSON once the link is live", () => {
    const { sock, link } = setup();
    sock(0).message(msg());
    expect(link.send(ack)).toBe(true);
    expect(sock(0).sent.map((d) => JSON.parse(d) as unknown)).toEqual([ack]);
  });

  it("drops a command before the first state, with a warning, and queues nothing", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { sock, link } = setup();
    expect(link.send(ack)).toBe(false);
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("dropped command ack_alert (link is connecting)"));
    sock(0).message(msg());
    expect(sock(0).sent).toEqual([]);
    warn.mockRestore();
  });

  it("drops a command while offline, and sends on the new socket once live again", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { sock, link } = setup();
    sock(0).message(msg());
    sock(0).serverClose();
    expect(link.send(ack)).toBe(false);
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("(link is offline)"));
    vi.advanceTimersByTime(backoffMs(0));
    sock(1).message(msg(2));
    expect(link.send(ack)).toBe(true);
    expect(sock(0).sent).toEqual([]);
    expect(sock(1).sent).toHaveLength(1);
    warn.mockRestore();
  });

  it("reports a socket that throws on send as not sent", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { sock, link } = setup();
    sock(0).message(msg());
    sock(0).failSend = true;
    expect(link.send(ack)).toBe(false);
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("could not send command ack_alert"), expect.any(Error));
    warn.mockRestore();
  });

  it("drops a command, with a warning, when the socket is closing but the link still says live", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { sock, link } = setup();
    sock(0).message(msg());
    sock(0).readyState = 2; // CLOSING: a browser would discard the data without an error
    expect(link.send(ack)).toBe(false);
    expect(sock(0).sent).toEqual([]);
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("dropped command ack_alert (socket is not open)"));
    warn.mockRestore();
  });

  it("drops a command after stop", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { sock, link } = setup();
    sock(0).message(msg());
    link.stop();
    expect(link.send(ack)).toBe(false);
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("(link is stopped)"));
    warn.mockRestore();
  });
});
