// WebSocket client: one socket to the backend, reconnect with backoff, and a silence watchdog.
//
// Every message is the full state, so there is nothing to catch up on after a reconnect.
// `seq` is not checked: the backend restarts it at 0 when it restarts, and dropping "old"
// messages would freeze the HUD on the values from before the restart.
//
// The backend sends a state every second. If nothing understandable arrives for SILENCE_MS the
// link is reported offline, whatever the socket claims, and the socket is replaced. That covers
// a backend that is up but cannot build a state, a half-open connection, and a version mismatch.
import type { Command, State } from "../contract.gen";
import type { Conn } from "../hud/types";
import { parseState } from "./parse";

export interface SocketLike {
  onopen: (() => void) | null;
  onmessage: ((event: { data: unknown }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  /** WebSocket.readyState: 1 is OPEN. send() on a closing socket drops data without an error. */
  readonly readyState: number;
  send(data: string): void;
  close(): void;
}

export interface Link {
  /**
   * Send a command now, or drop it with a warning in the console when the link is not live:
   * there is no queue, because an old command (an ack for an alert that has since changed)
   * must not arrive late. Returns whether it was handed to the socket.
   */
  send(command: Command): boolean;
  stop(): void;
}

export interface LinkOptions {
  url: string;
  onState: (state: State) => void;
  /** Called only when the status changes. The status starts as "connecting" without a call. */
  onConn: (conn: Conn) => void;
  makeSocket?: (url: string) => SocketLike;
}

export const SILENCE_MS = 3000;
const OPEN = 1; // WebSocket.OPEN, spelled out so tests need no browser
const BACKOFF_FIRST_MS = 500;
const BACKOFF_MAX_MS = 5000;

/** Wait before reconnect number `attempt` (0 = first): 500, 1000, 2000, 4000, then 5000 ms. */
export function backoffMs(attempt: number): number {
  return Math.min(BACKOFF_MAX_MS, BACKOFF_FIRST_MS * 2 ** Math.max(0, attempt));
}

function browserSocket(url: string): SocketLike {
  // A WebSocket has these four handlers and close(); its handler types are just wider
  // (MessageEvent has `data`), which TypeScript cannot see through a mutable property.
  return new WebSocket(url) as unknown as SocketLike;
}

export function startLink(options: LinkOptions): Link {
  const makeSocket = options.makeSocket ?? browserSocket;
  let socket: SocketLike | null = null;
  let conn: Conn = "connecting";
  let attempt = 0;
  let stopped = false;
  let silenceTimer: ReturnType<typeof setTimeout> | undefined;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let lastComplaint = "";

  function setConn(next: Conn): void {
    if (next === conn) return;
    // Tell the page first: if that throws, the status is not recorded and is tried again.
    options.onConn(next);
    conn = next;
  }

  function armSilenceTimer(): void {
    clearTimeout(silenceTimer);
    silenceTimer = setTimeout(() => {
      console.warn(`backend link: nothing usable for ${SILENCE_MS} ms, reconnecting`);
      lost();
    }, SILENCE_MS);
  }

  function connect(): void {
    retryTimer = undefined;
    let mine: SocketLike;
    try {
      mine = makeSocket(options.url);
    } catch (error) {
      // e.g. a URL the browser refuses. Keep trying: the HUD must heal without a reload.
      console.error("backend link: could not open a socket", error);
      lost();
      return;
    }
    socket = mine;
    armSilenceTimer();
    // No onopen or onerror handler: an open socket proves nothing until a state arrives, and
    // the browser always follows an error with a close.
    mine.onclose = () => {
      if (socket === mine) lost();
    };
    mine.onmessage = (event) => {
      if (socket !== mine) return;
      const result = parseState(event.data);
      if ("error" in result) {
        complain(result.error);
        return;
      }
      // State first, then "live": the other order would show the old values as fresh for a moment.
      try {
        options.onState(result.state);
        setConn("live");
      } catch (error) {
        // A state the page cannot apply is as good as no state. It must not feed the watchdog,
        // or the HUD would stay "live" on the last values it could show.
        console.error("backend link: a state could not be applied", error);
        return;
      }
      attempt = 0;
      lastComplaint = "";
      armSilenceTimer();
    };
  }

  /** The current socket is gone or useless: say so, drop it, and try again after the backoff. */
  function lost(): void {
    if (stopped) return;
    clearTimeout(silenceTimer);
    release();
    lastComplaint = ""; // a new socket may complain afresh
    // Schedule the retry before telling the page, so nothing the page does can stop it.
    if (retryTimer === undefined) {
      retryTimer = setTimeout(connect, backoffMs(attempt));
      attempt += 1;
    }
    try {
      setConn("offline");
    } catch (error) {
      console.error("backend link: the page could not be told the link is offline", error);
    }
  }

  function release(): void {
    const old = socket;
    socket = null;
    if (old === null) return;
    old.onopen = old.onmessage = old.onclose = old.onerror = null;
    try {
      old.close();
    } catch (error) {
      console.warn("backend link: closing the old socket failed", error);
    }
  }

  /** Log a rejected message, but not the same reason once a second for ever. */
  function complain(reason: string): void {
    if (reason === lastComplaint) return;
    lastComplaint = reason;
    console.warn(`backend link: ignored a message (${reason})`);
  }

  connect();

  return {
    send(command: Command): boolean {
      if (stopped || socket === null || conn !== "live") {
        console.warn(`backend link: dropped command ${command.name} (link is ${stopped ? "stopped" : conn})`);
        return false;
      }
      // "live" lasts up to SILENCE_MS after the socket started closing; a send then would vanish.
      if (socket.readyState !== OPEN) {
        console.warn(`backend link: dropped command ${command.name} (socket is not open)`);
        return false;
      }
      try {
        socket.send(JSON.stringify(command));
        return true;
      } catch (error) {
        console.warn(`backend link: could not send command ${command.name}`, error);
        return false;
      }
    },
    stop(): void {
      stopped = true;
      clearTimeout(silenceTimer);
      clearTimeout(retryTimer);
      release();
    },
  };
}
