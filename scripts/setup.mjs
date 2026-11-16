// npm run setup: create .venv, install Python and Node packages, Playwright browsers,
// and clone NASA's TSS at the pinned commit into vendor/TSS2027.
// The only command that downloads anything.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT, venvPython } from "./py.mjs";

const isWindows = process.platform === "win32";

const quote = (arg) => (/[\s"]/.test(arg) ? `"${arg.replace(/"/g, '\\"')}"` : arg);

// On Windows, npm and npx are .cmd files and need a shell; pass one quoted command line.
function spawnArgs(cmd, args) {
  return isWindows ? [[cmd, ...args].map(quote).join(" "), [], { shell: true }] : [cmd, args, {}];
}

function run(cmd, args, options = {}) {
  console.log(`> ${cmd} ${args.join(" ")}`);
  const [file, fileArgs, shell] = spawnArgs(cmd, args);
  const result = spawnSync(file, fileArgs, { cwd: ROOT, stdio: "inherit", ...shell, ...options });
  if (result.status !== 0) {
    console.error(`Failed: ${cmd} ${args.join(" ")}`);
    process.exit(result.status ?? 1);
  }
}

function findBasePython() {
  const candidates = isWindows ? [["py", ["-3.12"]], ["py", ["-3"]], ["python", []]] : [["python3", []], ["python", []]];
  for (const [cmd, pre] of candidates) {
    const [file, fileArgs, shell] = spawnArgs(cmd, [
      ...pre, "-c", "import sys; print(sys.version_info >= (3, 11))",
    ]);
    const probe = spawnSync(file, fileArgs, { encoding: "utf8", ...shell });
    if (probe.status === 0 && probe.stdout.trim() === "True") return [cmd, pre];
  }
  console.error("Python 3.11 or newer is needed.");
  process.exit(1);
}

// 1. Python
if (!existsSync(join(ROOT, ".venv"))) {
  const [cmd, pre] = findBasePython();
  run(cmd, [...pre, "-m", "venv", ".venv"]);
}
const py = venvPython();
run(py, ["-m", "pip", "install", "--quiet", "--upgrade", "pip"]);
run(py, ["-m", "pip", "install", "--quiet", "-e", "backend[dev]"]);

// 2. Node (root + client workspace)
run("npm", ["install"]);

// 3. The browser the end-to-end tests drive. CI machines also need its system libraries.
run("npx", ["playwright", "install", ...(process.env.CI ? ["--with-deps"] : []), "chromium"]);

// 4. NASA's TSS at the pinned commit (gitignored, for reference and the live smoke test)
const pinned = readFileSync(join(ROOT, "backend", "suits", "tss", "VERSION"), "utf8").split(/\s/)[0];
const vendor = join(ROOT, "vendor", "TSS2027");
if (!existsSync(vendor)) {
  run("git", ["clone", "--quiet", "https://github.com/SUITS-Techteam/TSS2027", vendor]);
}
run("git", ["-C", vendor, "fetch", "--quiet", "origin"]);
run("git", ["-C", vendor, "-c", "advice.detachedHead=false", "checkout", "--quiet", pinned]);
console.log(`vendor/TSS2027 at ${pinned}. See docs/notes/tss-build-and-run.md to build and run it.`);
console.log("Setup done.");
