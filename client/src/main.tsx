import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { createIntentHandler, setIntentHandler, fireIntent } from "./input/dispatch";
import { startKeyboard } from "./input/keyboard";
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

// Every user action: intent -> command -> link. The backend's next State shows the result.
setIntentHandler(
  createIntentHandler({
    send: (command) => link.send(command),
    panels: () => useHud.getState().panels,
    onRecord: (record) => useHud.getState().noteIntent(record),
  }),
);
const stopKeyboard = startKeyboard(fireIntent);

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

// Dev only: when this module is replaced, do not leave a second socket or listener running.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    stopKeyboard();
    setIntentHandler(null);
    link.stop();
    removeHook();
    root.unmount();
  });
}
