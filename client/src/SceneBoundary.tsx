// If drawing throws, React removes everything below the nearest boundary. This one catches the
// error, reports it, shows a fallback (nothing, by default) and builds its children again after
// a wait that grows with each failure in a row. A blank HUD for a few seconds is safe; a frozen
// one that looks alive is not.
//
// It is used twice. Inside the canvas, around the HUD: the renderer and a running headset
// session survive, only the panels are rebuilt. Around the whole canvas, as a last resort.
import { Component, type ReactNode } from "react";
import { retryDelayMs } from "./sceneRetry";

interface BoundaryProps {
  children: ReactNode;
  /** What to draw while waiting. Default: nothing. */
  fallback?: (problem: string) => ReactNode;
  /** Called with the reason when the children crash, and with null when they are rebuilt. */
  onProblem?: (problem: string | null) => void;
}

interface BoundaryState {
  problem: string | null;
}

export class SceneBoundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { problem: null };
  private retry: ReturnType<typeof setTimeout> | undefined;
  private failures = 0;

  static getDerivedStateFromError(error: unknown): BoundaryState {
    return { problem: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown): void {
    this.failures += 1;
    const waitMs = retryDelayMs(this.failures);
    console.error(`The HUD stopped and will be rebuilt in ${waitMs / 1000} s`, error);
    this.props.onProblem?.(error instanceof Error ? error.message : String(error));
    clearTimeout(this.retry);
    this.retry = setTimeout(() => {
      this.setState({ problem: null });
      this.props.onProblem?.(null);
    }, waitMs);
  }

  componentWillUnmount(): void {
    clearTimeout(this.retry);
  }

  render(): ReactNode {
    const { problem } = this.state;
    if (problem === null) return this.props.children;
    return this.props.fallback?.(problem) ?? null;
  }
}
