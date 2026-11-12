The Quest Browser has no working speech recognition and speech synthesis is unreliable in immersive mode, so speech-to-text and text-to-speech run on the laptop and audio travels over our WebSocket.

Source: web research 2026-11-12 (forum reports 2023–2025). Low confidence, not checked on a device.

- Microphone capture with `getUserMedia` is reported to work in an immersive session once permission is granted, with at least one report of it failing. The page must be a secure context (`localhost` or HTTPS).
- Design: the browser captures microphone audio and sends it to the backend; the backend runs speech-to-text (faster-whisper), produces the answer, runs text-to-speech (Piper) and sends audio back; the browser plays it with Web Audio.
- Fallback if the headset microphone fails: use a microphone on the laptop (or a Bluetooth headset paired to the laptop). The backend accepts audio from either source, so this is a config switch.
- Check on the first day with the headset (milestone M9).
