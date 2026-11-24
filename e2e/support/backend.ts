// The backend as a process the tests can start, stop and ask directly (not through the page).
import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { State } from "../../client/src/contract.gen";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

/** The real TSS run recorded in M1: oxygen drains from about 90%, unlike the sim's fixed 92. */
export const REAL_RECORDING = join(ROOT, "data", "recordings", "real-tss-6293795.jsonl");

/** Sim mode, optionally playing data/scenarios/<scenario>.yaml at `speed` times real time. */
export type BackendMode = { mode: "sim"; scenario?: string; speed?: number } | { mode: "replay"; recording: string };

const STOP_GRACE_MS = 5000;

function venvPython(): string {
  const found = [join(ROOT, ".venv", "Scripts", "python.exe"), join(ROOT, ".venv", "bin", "python")].find((p) =>
    existsSync(p),
  );
  if (!found) throw new Error("No .venv found. Run `npm run setup` first.");
  return found;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const alive = (child: ChildProcess) => child.exitCode === null && child.signalCode === null;

interface Health {
  tss: string | null;
  seq: number | null;
}

export class Backend {
  private child: ChildProcess | null = null;
  private log: string[] = [];
  private started: string | null = null;

  constructor(readonly port: number) {}

  get running(): boolean {
    return this.child !== null && alive(this.child);
  }

  private async health(): Promise<Health | null> {
    try {
      return (await (await fetch(`http://127.0.0.1:${this.port}/health`)).json()) as Health;
    } catch {
      return null; // not listening
    }
  }

  /**
   * Start the backend (sim mode unless told otherwise) and wait until it is ready. A backend
   * already running in another mode is restarted.
   *
   * Ready in sim mode means its link to the fake TSS is ok: for the first 3 s or so after a
   * start the backend rightly reports unreachable, then stale, while data arrives. In replay
   * mode it means the first state was sent; the recording decides the link from there.
   */
  async start(wanted: BackendMode = { mode: "sim" }): Promise<void> {
    const key = JSON.stringify(wanted);
    if (this.running && this.started === key) return;
    await this.stop();
    if ((await this.health()) !== null) {
      throw new Error(`port ${this.port} is already answering: a backend from an earlier run is still alive. Stop it.`);
    }

    this.log = [];
    const env = {
      ...process.env,
      SUITS_MODE: wanted.mode,
      SUITS_RECORDING: wanted.mode === "replay" ? wanted.recording : "",
      SUITS_RECORD: "",
      SUITS_SCENARIO: wanted.mode === "sim" ? (wanted.scenario ?? "") : "",
      SUITS_SCENARIO_SPEED: wanted.mode === "sim" && wanted.speed !== undefined ? String(wanted.speed) : "",
    };
    const child = spawn(
      venvPython(),
      [
        "-m",
        "uvicorn",
        "--factory",
        "suits.app:create_app",
        "--host",
        "127.0.0.1",
        "--port",
        String(this.port),
        // As in `npm run dev`: the backend refuses bigger frames than a command needs.
        "--ws-max-size",
        "65536",
      ],
      { cwd: ROOT, env, stdio: ["ignore", "pipe", "pipe"] },
    );
    const keep = (chunk: unknown) => {
      this.log.push(String(chunk));
      if (this.log.length > 200) this.log.shift();
    };
    let failed = false;
    child.once("error", (error) => {
      failed = true;
      keep(`could not start the backend process: ${String(error)}\n`);
    });
    child.stdout?.on("data", keep);
    child.stderr?.on("data", keep);
    this.child = child;
    this.started = key;

    const deadline = Date.now() + 20_000;
    while (Date.now() < deadline && !failed && alive(child)) {
      const health = await this.health();
      const ready = wanted.mode === "sim" ? health?.tss === "ok" : health != null && health.seq !== null;
      if (ready && alive(child)) return;
      await sleep(100);
    }
    await this.stop();
    throw new Error(`backend (${wanted.mode}) did not come up on port ${this.port}:\n${this.log.join("")}`);
  }

  /** Kill it, the way a crash or a pulled plug would, and wait until it is gone. */
  async stop(): Promise<void> {
    const child = this.child;
    this.child = null;
    this.started = null;
    if (child === null || !alive(child)) return;
    const gone = new Promise<void>((resolve) => child.once("exit", () => resolve()));
    child.kill();
    // On Linux kill() asks politely, and a server with an open socket may take its time.
    const hard = setTimeout(() => child.kill("SIGKILL"), STOP_GRACE_MS);
    await gone;
    clearTimeout(hard);
  }

  /** The next state the backend sends, read on a socket of the test's own. */
  state(): Promise<State> {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(`ws://127.0.0.1:${this.port}/ws`);
      const finish = (act: () => void) => {
        clearTimeout(timer);
        socket.close();
        act();
      };
      const timer = setTimeout(() => finish(() => reject(new Error("no state from the backend within 5 s"))), 5000);
      socket.onmessage = (event) => {
        try {
          const state = JSON.parse(String(event.data)) as State;
          finish(() => resolve(state));
        } catch (error) {
          finish(() => reject(new Error(`the backend sent something that is not JSON: ${String(error)}`)));
        }
      };
      socket.onerror = () => finish(() => reject(new Error("could not connect to the backend's /ws")));
    });
  }
}
