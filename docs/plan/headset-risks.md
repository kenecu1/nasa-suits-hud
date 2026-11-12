# Risks we cannot check without the headset

Each row: what could go wrong, how we check it once the Quest 3S arrives, and what we do if it fails. M9 runs rows 1–8 on the first day. M10 handles rows 9–14. Record each result as a note in `docs/notes/`.

| # | Risk | Check on the device | If it fails |
|---|---|---|---|
| 1 | The page does not load or is not a secure context | `adb reverse`, open `http://localhost:5173`, see the start page | HTTPS with a self-signed certificate over Wi-Fi |
| 2 | `immersive-ar` does not start or passthrough is not visible | Press Enter AR; the room is visible behind the HUD | Check session features one by one; drop optional features |
| 3 | Frame rate is low | Meta's performance overlay shows a steady 72 fps for 5 minutes with all panels on | Cut draw calls and text updates; lower render scale |
| 4 | Microphone capture does not work inside the session | Hold talk, speak, see the heard text on the HUD | Use a microphone on the laptop (config switch) |
| 5 | Speech audio does not play | Ask a question, hear the answer in the headset | Play audio on the laptop speaker or a Bluetooth earpiece |
| 6 | Controller or hand input is unreliable | Each intent 10 times with a controller, then with a pinch | Controllers only (they track better in low light), plus voice |
| 7 | WebSocket drops over Wi-Fi when untethered | Walk the room for 10 minutes; `link` stays ok; reconnects are counted | Move the router; raise the stale threshold; stay tethered with a long cable |
| 8 | Emulator and device behave differently (pose, input, feature support) | Run the M8 mission script on the device and compare with the laptop run | Fix per finding; add a note |
| 9 | Text is hard to read through passthrough in a dim room | Read every panel at arm's-length-plus distance in the demo lighting; a second person reads values aloud from a casting view | Tune size, weight, backing opacity with the live tuning page |
| 10 | Head-following panels are uncomfortable or block the ground | Walk for 5 minutes; wearer rates comfort; ground at 2 m ahead stays visible | Tune distance, follow delay, panel positions; offer a "hide HUD" intent |
| 11 | Headset tracking fails in low light | Walk the route in the demo lighting; watch for tracking-lost warnings | Raise the light a little; add an infrared lamp (reported to help, unverified); fall back to scripted position, standing still |
| 12 | Real movement does not match the map (scale, heading, drift) | Calibrate at the lander mark, walk a measured square, compare the breadcrumb trail | Recalibrate intent mid-mission; larger arrival radius; fall back to scripted position |
| 13 | Built-in recording does not capture the HUD over passthrough | Record 30 seconds and play it back | Cast to the laptop and screen-record |
| 14 | Battery or heat ends a session early | Run the full mission twice in a row | Shorter mission script; charge between takes |

What emulation does cover, so it is not on this list: session start and end logic, the HUD rig maths, input-to-intent mapping, the pose-to-map transform, reconnects, and everything in the backend.
