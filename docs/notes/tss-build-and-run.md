Build the TSS yourself in WSL after every `git pull` (the binary is gitignored and goes stale silently), and keep stdin open when running it.

- **Stale binary (seen 2026-11-19):** `server.exe` is in the TSS `.gitignore`, so `git pull` updates the source and leaves an old binary. An old binary answers the legacy ports but ignores Subscribe on 14141: `npm run tss:smoke` reports "no answer to Subscribe … after 3 tries" while telemetry still arrives. Sign of a pre-`6293795` binary: at startup it prints `Failed to set eva1_power in EVA config file` ten times. Fix: delete `server.exe` and the `*.obj`/`*.pdb`/`*.ilk` files (Windows build leftovers, untracked) and rebuild.
- **Build:** WSL Ubuntu, `gcc` (11.4 works), from the TSS root. `build.bat` holds the command line:
  `gcc -g -Isrc/lib/cjson src/network.c src/data.c src/groups.c src/lib/ssu_simulation/ssu_sim.c src/lib/spm_simulation/spm_sim.c src/server.c src/lib/simulation/throw_errors.c src/lib/cjson/cJSON.c src/lib/simulation/sim_engine.c src/lib/simulation/sim_algorithms.c -o server.exe -lm`
  `build_windows.bat` is empty. There is no gcc, make or docker on the Windows side of Vlad's laptop.
- **`groups.h`:** at `6293795` it had merge-conflict markers and did not compile (fix: keep the "Stashed" side, `bool dcu; bool uia; uint16_t poi`). Upstream fixed it in `63e567d`; from `7dfc42b` on no patch is needed.
- **Run:** `./server.exe`. The server exits as soon as stdin is readable, so do not run it with stdin closed or piped from `/dev/null`. Run it in a terminal, or keep a pipe open (`tail -f /dev/null | ./server.exe`).
- **After every restart** the group and team assignment is gone: assign the laptop again ([tss-team-must-be-assigned](tss-team-must-be-assigned.md)).
- Ports: TCP + UDP 14141 (web UI, new protocol, peripherals), UDP 14142–14151 (legacy per-team).
- It binds to the machine's last non-loopback IPv4 address and prints it.
- Source for builder sessions: `https://github.com/SUITS-Techteam/TSS2027`, pinned commit in `backend/suits/tss/VERSION` (`7dfc42b` since 2026-11-19, smoke-tested live). `npm run setup` checks it out into `vendor/TSS2027` (gitignored). Milestones copy what they need from there into the repo (map images, `data/RockData.json`, procedure PDFs).
- Vlad's clone: WSL distro `Ubuntu`, `/root/nasa_suits/TSS2027` (has a local edit in `scripts/test_socket.py`). Built from `7dfc42b` on 2026-11-19.
- The M1 recording (`data/recordings/real-tss-6293795.jsonl`) came from a separate copy, `/root/tss-m1` at commit `6293795` with only the `groups.h` fix. So the legacy rate limit ([tss-legacy-port-is-slow](tss-legacy-port-is-slow.md)) comes from unpatched `server.c` and `network.c`.

Most tests must not need the real TSS. Use the fake TSS in the repo (built in M1) and recordings. The real TSS is for the live smoke check only.
