The TSS answers Subscribe with Ack 1 and sends no data until our IP address is assigned to a group and that group to a team in the TSS web UI.

Verified live at commit 6293795.

- The TSS identifies a client by source IP. Assignment is done in the web UI at `http://<tss-ip>:14141` (it sends `POST /groups`).
- Before assignment: Ack result 1. After: Ack 0, then 1 Hz telemetry.
- The README says one device per team. The code does not enforce it: every team-type device in the group receives all packets. Do not rely on either behaviour. Our design has exactly one TSS client (the backend on the laptop); the headset never talks to the TSS.
- The legacy per-team ports (14142–14151) need no assignment.

The adapter must report "connected but not assigned" as its own status so the HUD can say what to fix.
