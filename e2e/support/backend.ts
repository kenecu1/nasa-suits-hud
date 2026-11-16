// The backend as a process the tests can start, stop and ask directly (not through the page).
import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { State } from "../../client/src/contract.gen";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function venvPython(): string {
  const found = [join(ROOT, ".venv", "Scripts", "python.exe"), join(ROOT, ".venv", "bin", "python")].find((p) =>
    existsSync(p),
  );
  if (!found) throw new Error("No .venv found. Run `npm run setup` first.");
  return found;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export class Backend {
  private child: ChildProcess | null = null;
  private log: string[] = [];

  constructor(readonly port: number) {}

  get running(): boolean {
    return this.child !== null && this.child.exitCode === null;
  }

  /**
   * Start in sim mode and wait until its link to the fake TSS is ok. For the first 3 s or so
   * after a start the backend rightly reports unreachable, then stale, while data arrives.
   */
  async start(): Promise<void> {
    if (this.running) return;
    this.log = [];
    const child = spawn(
      venvPython(),
      ["-m", "uvicorn", "--factory", "suits.app:create_app", "--host", "127.0.0.1", "--port", String(this.port)],
      { cwd: ROOT, env: { ...process.env, SUITS_MODE: "sim", SUITS_RECORD: "" }, stdio: ["ignore", "pipe", "pipe"] },
    );
    const keep = (chunk: Buffer) => {
      this.log.push(chunk.toString());
      if (this.log.length > 200) this.log.shift();
    };
    child.stdout?.on("data", keep);
    child.stderr?.on("data", keep);
    this.child = child;

    const deadline = Date.now() + 20_000;
    while (Date.now() < deadline) {
      if (child.exitCode !== null) break;
      try {
        const health = (await (await fetch(`http://127.0.0.1:${this.port}/health`)).json()) as { tss: string | null };
        if (health.tss === "ok") return;
      } catch {
        // not listening yet
      }
      await sleep(100);
    }
    await this.stop();
    throw new Error(`backend did not come up on port ${this.port}:\n${this.log.join("")}`);
  }

  /** Kill it, the way a crash or a pulled plug would, and wait until it is gone. */
  async stop(): Promise<void> {
    const child = this.child;
    this.child = null;
    if (child === null || child.exitCode !== null) return;
    const gone = new Promise((resolve) => child.once("exit", resolve));
    child.kill();
    await gone;
  }

  /** The next state the backend sends, read on a socket of the test's own. */
  state(): Promise<State> {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(`ws://127.0.0.1:${this.port}/ws`);
      const timer = setTimeout(() => {
        socket.close();
        reject(new Error("no state from the backend within 5 s"));
      }, 5000);
      socket.onmessage = (event) => {
        clearTimeout(timer);
        socket.close();
        resolve(JSON.parse(String(event.data)) as State);
      };
      socket.onerror = () => {
        clearTimeout(timer);
        reject(new Error("could not connect to the backend's /ws"));
      };
    });
  }
}
