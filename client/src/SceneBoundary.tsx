// If drawing the HUD throws, React removes the whole scene. This catches that, says so on the
// page, and builds the scene again after a moment, so one bad frame of data is not the end of
// the HUD. A blank HUD for a few seconds is safe; a frozen one that looks alive is not.
import { Component, type CSSProperties, type ReactNode } from "react";
import { theme } from "./theme";

const RETRY_MS = 2000;

const notice: CSSProperties = {
  position: "fixed",
  left: 16,
  bottom: 16,
  font: "16px system-ui, sans-serif",
  color: theme.color.warning,
};

interface BoundaryState {
  problem: string | null;
}

export class SceneBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { problem: null };
  private retry: ReturnType<typeof setTimeout> | undefined;

  static getDerivedStateFromError(error: unknown): BoundaryState {
    return { problem: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown): void {
    console.error("The HUD scene stopped and will be rebuilt", error);
    clearTimeout(this.retry);
    this.retry = setTimeout(() => this.setState({ problem: null }), RETRY_MS);
  }

  componentWillUnmount(): void {
    clearTimeout(this.retry);
  }

  render(): ReactNode {
    if (this.state.problem === null) return this.props.children;
    return (
      <div role="alert" style={notice}>
        The HUD stopped ({this.state.problem}). Restarting it.
      </div>
    );
  }
}
