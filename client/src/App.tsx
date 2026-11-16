// The page: the HUD scene, and on top of it (outside the headset view only) a start bar with
// the Enter AR button. HTML is fine here; nothing inside the headset view is HTML.
import { useCallback, useState, type CSSProperties } from "react";
import { useStore } from "zustand";
import { SceneBoundary } from "./SceneBoundary";
import { HudScene } from "./scene/HudScene";
import { xrStore } from "./scene/xr";
import { theme } from "./theme";

const stage: CSSProperties = { position: "fixed", inset: 0, background: theme.color.backdrop };
const bar: CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  display: "flex",
  alignItems: "center",
  gap: 16,
  padding: 16,
  font: "16px system-ui, sans-serif",
  color: theme.color.label,
};
const button: CSSProperties = {
  font: "inherit",
  padding: "8px 16px",
  borderRadius: 8,
  border: `1px solid ${theme.color.label}`,
  background: theme.color.panel,
  color: theme.color.text,
  cursor: "pointer",
};
const notice: CSSProperties = {
  position: "fixed",
  left: 16,
  bottom: 16,
  font: "16px system-ui, sans-serif",
  color: theme.color.warning,
};

/** The whole canvas is being rebuilt, and a headset session cannot move to a new renderer. */
function endSessionOnCanvasCrash(problem: string | null): void {
  if (problem === null) return;
  const session = xrStore.getState().session;
  session?.end().catch((error: unknown) => console.error("Ending the AR session failed", error));
}

export function App() {
  const inSession = useStore(xrStore, (s) => s.session != null);
  const [problem, setProblem] = useState<string | null>(null);
  const [hudProblem, setHudProblem] = useState<string | null>(null);
  const onHudProblem = useCallback((reason: string | null) => setHudProblem(reason), []);

  // Entering AR must start from a click (a browser rule), so this stays a plain button.
  const enterAr = () => {
    setProblem(null);
    xrStore.enterAR().catch((error: unknown) => {
      console.error("Enter AR failed", error);
      const reason = error instanceof Error ? error.message : String(error);
      setProblem(`AR did not start: ${reason}`);
    });
  };

  const stopped = (reason: string) => (
    <div role="alert" style={notice}>
      The HUD stopped ({reason}). Restarting it.
    </div>
  );

  return (
    <>
      <div style={stage}>
        <SceneBoundary fallback={stopped} onProblem={endSessionOnCanvasCrash}>
          <HudScene onHudProblem={onHudProblem} />
        </SceneBoundary>
      </div>
      {hudProblem !== null && stopped(hudProblem)}
      {!inSession && (
        <div style={bar}>
          <strong style={{ color: theme.color.text }}>SUITS HUD</strong>
          <button type="button" style={button} onClick={enterAr}>
            Enter AR
          </button>
          {problem !== null && <span role="alert" style={{ color: theme.color.warning }}>{problem}</span>}
        </div>
      )}
    </>
  );
}
