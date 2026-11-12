# M6 — Voice assistant

**Goal:** the astronaut holds a button, asks a question or gives a command in plain language, and gets a short spoken answer that is grounded in live data. NASA requirement 3b and the hallucination guardrail.

**Builder:** Opus 5.5. Load the `claude-api` skill before writing any Claude API code. **Fable review after:** yes, of the guardrails and the evaluation.

**Read first:** `docs/walkthroughs/M2.md`; decision 8 in `architecture.md`; note `quest-speech-runs-on-laptop`.

## Scope

1. **Audio path:** the `talk` intent (hold to talk), added to both binding tables. The client captures the microphone with `getUserMedia` and streams 16 kHz mono PCM to the backend as binary frames. An `audio_source` setting lets the backend use a laptop microphone instead.
2. **Speech-to-text** (`voice/stt.py`): faster-whisper, English `base` model, on CPU, behind an interface. `npm run setup` downloads the speech-to-text and text-to-speech models into `models/` (gitignored); tests never download.
3. **Router** (`voice/intents.py`, `data/voice/intents.yaml`): fixed intents matched by patterns, answered from templates with no language model. Like tools, an intent is active only if its part of the state exists; otherwise the answer is "Not available yet." Queries: oxygen, battery, CO2, heart rate, suit status summary, time left, range, current step, distance to target, alerts. Commands: next step, previous step, drop pin, navigate to a point or the lander, acknowledge alert, show or hide map.
4. **Assistant** (`voice/assistant.py`): anything else goes to Claude (`claude-haiku-5-5` by default, in config) with tools.
   - Read-only tools: `get_suit_status`, `get_alerts`, `get_forecast`, `get_procedure`, `get_navigation`, `get_science`. Register a tool only if its part of the state exists, so this milestone does not depend on M3–M7.
   - Action tools: the same commands as the fixed intents, nothing else.
   - System prompt: answer in at most two short sentences, only from tool results, say "I don't have that" when a tool has no value.
5. **Guardrails** (`voice/guardrails.py`): before an answer is spoken, every number in it must equal a value returned by a tool in that turn (after rounding to the spoken precision). If not, the answer is replaced by a template built from the tool results, or by "I can't confirm that." Actions outside the allowed list are refused. No key, no network or a timeout of 4 s gives the fixed-intent answer or "Assistant offline."
6. **Text-to-speech** (`voice/tts.py`): Piper on the laptop, behind an interface; audio is sent to the client and played with Web Audio. The answer text also shows on the HUD.
7. **Contract:** `assistant { status, heard, reply }`; a text command `ask` for typed questions (used by tests and as a keyboard fallback).
8. **Evaluation** (`npm run eval:voice` → `docs/ml/voice-report.md`): about 60 questions in `data/voice/eval.yaml`, each with a mission state, the expected tool or intent and the expected values. Reports: routing accuracy, tool choice accuracy, share of answers with all numbers grounded before and after the guardrail, latency at the 50th and 95th percentile. This uses the real API and costs a few cents; it is not part of `npm run check`.

## Acceptance

Backend (pytest, no network; the language model is a fake that returns scripted replies)
1. Each fixed intent whose state exists at build time (suit values, alerts and status summary always; the rest when M3–M5 are merged): three phrasings route correctly; the answer contains the live value from the given state, in the short form NASA shows ("Primary O2 47 percent, secondary 99 percent").
2. Each active command intent produces the right `command`. An inactive intent answers "Not available yet." M8 checks the full list.
3. Guardrail: a scripted reply with a number that no tool returned is not spoken; the replacement contains only tool values. A scripted reply asking for an action outside the list is refused.
4. With no API key and with a timeout, fixed intents still work and other questions give "Assistant offline."
5. Tools are registered only for parts of the state that exist.
6. Speech round trip: audio made by the text-to-speech engine for five test sentences is transcribed by the speech-to-text engine and routes to the right intent. Mark this test slow; it runs in `npm run check` and is skipped when `SUITS_SKIP_SPEECH_MODELS=1` or the models are not in `models/` (CI sets the flag).
7. `assistant.status` moves idle → listening → thinking → speaking → idle for one request.

Client and end to end
8. View model for the assistant panel in each status.
9. Playwright, desktop: send `ask` "how much oxygen do I have"; `window.__hud.panels.assistant.reply` contains the backend's value. Emulated headset: holding the emulated controller button sets status to listening (audio is injected from a fixture, not a microphone).

Manual
10. With an API key: `npm run eval:voice` (added in this milestone) writes the report. Zero ungrounded numbers reach the user. Record latency.

## For the review

Hand the reviewer `voice/guardrails.py`, `voice/assistant.py`, the tests for item 3, `docs/ml/voice-report.md` and this file.
