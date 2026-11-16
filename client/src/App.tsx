// The page: the HUD scene, and on top of it (outside the headset view only) a start bar with
// the Enter AR button. HTML is fine here; nothing inside the headset view is HTML.
import { useState, type CSSProperties } from "react";
import { useStore } from "zustand";
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

export function App() {
  const inSession = useStore(xrStore, (s) => s.session != null);
  const [problem, setProblem] = useState<string | null>(null);

  // Entering AR must start from a click (a browser rule), so this stays a plain button.
  const enterAr = () => {
    setProblem(null);
    xrStore.enterAR().catch((error: unknown) => {
      console.error("Enter AR failed", error);
      const reason = error instanceof Error ? error.message : String(error);
      setProblem(`AR did not start: ${reason}`);
    });
  };

  return (
    <>
      <div style={stage}>
        <HudScene />
      </div>
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
