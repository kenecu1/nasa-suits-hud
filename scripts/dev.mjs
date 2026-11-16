// npm run dev: the backend (SUITS_MODE, default sim) on :8000 and the client dev server.
// Open http://localhost:5173 once the client exists (milestone M1, session 2).
import { spawn } from "node:child_process";
import { ROOT, venvPython } from "./py.mjs";

const isWindows = process.platform === "win32";
const children = [];

function start(name, cmd, args) {
  // npm is a .cmd file on Windows and needs a shell: pass one command line, not an args array
  const child =
    isWindows && cmd === "npm"
      ? spawn([cmd, ...args].join(" "), { cwd: ROOT, stdio: "inherit", shell: true })
      : spawn(cmd, args, { cwd: ROOT, stdio: "inherit" });
  child.on("exit", (code) => {
    console.log(`${name} exited (${code})`);
    stopAll();
  });
  children.push(child);
}

function stopAll() {
  for (const child of children) {
    if (child.exitCode === null) child.kill();
  }
}

process.on("SIGINT", stopAll);
process.on("SIGTERM", stopAll);

start("backend", venvPython(), [
  "-m", "uvicorn", "--factory", "suits.app:create_app",
  "--host", "0.0.0.0", "--port", process.env.SUITS_PORT ?? "8000",
]);
start("client", "npm", ["run", "dev", "--workspace", "client", "--if-present"]);
