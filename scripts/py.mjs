// Run the repo's .venv Python with the given arguments, from the repo root.
// npm scripts use this so they work the same on Windows and Linux.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

export function venvPython() {
  const candidates = [
    join(ROOT, ".venv", "Scripts", "python.exe"),
    join(ROOT, ".venv", "bin", "python"),
  ];
  const found = candidates.find((p) => existsSync(p));
  if (!found) {
    console.error("No .venv found. Run `npm run setup` first.");
    process.exit(1);
  }
  return found;
}

export function runPython(args, options = {}) {
  return spawnSync(venvPython(), args, { cwd: ROOT, stdio: "inherit", ...options });
}

const isMain =
  process.argv[1] &&
  resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase();
if (isMain) {
  const result = runPython(process.argv.slice(2));
  process.exit(result.status ?? 1);
}
