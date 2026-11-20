The TSS answers Subscribe with Ack 1 and sends no data until our IP address is assigned to a group and that group to a team in the TSS web UI.

Verified live at commit 6293795; still true at 7dfc42b (2026-11-19).

- The TSS identifies a client by source IP. Assignment is done in the web UI at `http://<tss-ip>:14141` (it sends `POST /groups`).
- From a script (verified 2026-11-16): our IP appears in `GET /data/groups.json` under `devices` after our first Subscribe. Then `POST /groups` with form body `device=<index>&group=<g>` puts it in a group, and `group=<g>&team=<t>` assigns the group to a team (both return 201). With the TSS in WSL, the laptop's address as the TSS sees it is the WSL host adapter (for example `172.22.240.1`), not the Wi-Fi address.
- Before assignment: Ack result 1. After: Ack 0, then 1 Hz telemetry.
- The README says one device per team. The code does not enforce it: every team-type device in the group receives all packets. Do not rely on either behaviour. Our design has exactly one TSS client (the backend on the laptop); the headset never talks to the TSS.
- The legacy per-team ports (14142–14151) need no assignment.

The adapter must report "connected but not assigned" as its own status so the HUD can say what to fix.
