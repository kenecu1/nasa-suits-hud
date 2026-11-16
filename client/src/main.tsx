import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { wsUrl } from "./net/backendUrl";
import { startLink } from "./net/link";
import { useHud } from "./store";
import { installTestHook } from "./testHook";

const removeHook = installTestHook();

// The link lives outside React: it starts once and keeps reconnecting for the page's lifetime.
const link = startLink({
  url: wsUrl(window.location.href),
  onState: (state) => useHud.getState().receive(state),
  onConn: (conn) => useHud.getState().setConn(conn),
});

const container = document.getElementById("root");
if (container === null) throw new Error("index.html has no #root element");
const root = createRoot(container);
root.render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Dev server only: an emulated headset for trying Enter AR on the laptop.
if (import.meta.env.DEV) {
  void import("./scene/emulator")
    .then(({ startDevEmulator }) => startDevEmulator())
    .catch((error: unknown) => console.error("The headset emulator did not start", error));
}

// Dev only: when this module is replaced, do not leave a second socket running.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    link.stop();
    removeHook();
    root.unmount();
  });
}
