TSS2027 HEAD (6293795) does not compile because `src/groups.h` contains merge-conflict markers; build a patched copy in WSL and keep stdin open when running.

- Fix: in `src/groups.h` keep the "Stashed" side (`bool dcu; bool uia; uint16_t poi`), which is what `groups.c` uses. Check first whether NASA has pushed a fix (`git pull`).
- Build: WSL Ubuntu, `gcc` (11.4 works). `build.bat` holds the gcc command line. `build_windows.bat` is empty. There is no gcc, make or docker on the Windows side of Vlad's laptop.
- Run: `./server.exe`. The server exits as soon as stdin is readable, so do not run it with stdin closed or piped from `/dev/null`. Run it in a terminal, or keep a pipe open (`tail -f /dev/null | ./server.exe`).
- Ports: TCP + UDP 14141 (web UI, new protocol, peripherals), UDP 14142–14151 (legacy per-team).
- It binds to the machine's last non-loopback IPv4 address and prints it.
- Source for builder sessions: `https://github.com/SUITS-Techteam/TSS2027`, verified commit `6293795`. M1 adds a setup step that clones it into `vendor/TSS2027` (gitignored). Milestones copy what they need from there into the repo (map images, `data/RockData.json`, procedure PDFs).
- Vlad's existing clone: WSL distro `Ubuntu`, `/root/nasa_suits/TSS2027` (has a local edit in `scripts/test_socket.py`).

Most tests must not need the real TSS. Use the fake TSS in the repo (built in M1) and recordings. The real TSS is for the live smoke check only.
