To open the dev page on the Quest, connect USB, run `adb reverse` for the client and backend ports, and open `http://localhost:<port>` in the Quest Browser; `localhost` counts as a secure context, so WebXR and the microphone work without certificates.

Source: Meta browser remote-debugging docs and pmndrs/xr setup docs, 2026-11-12. Not checked on a device.

```
adb reverse tcp:5173 tcp:5173   # client (Vite)
adb reverse tcp:8000 tcp:8000   # backend (WebSocket)
```

- `chrome://inspect` on the laptop then gives remote DevTools for the headset page.
- If both USB and Wi-Fi adb are connected, `adb reverse` can fail: name the device with `adb -s <serial>`.
- Untethered (needed for the walking demo): serve over HTTPS with `@vitejs/plugin-basic-ssl` and `vite --host`, accept the certificate warning once on the headset. The backend WebSocket must then be `wss://` too: proxy it through Vite so there is one origin and one certificate.
- The client must take the backend URL from the page origin (same host, proxied path), never a hard-coded IP.
