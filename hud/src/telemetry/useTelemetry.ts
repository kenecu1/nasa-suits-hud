import { useEffect, useState } from 'react';
import type { BridgeMessage, SuitTelemetry, TSSErrorMessage } from './types';
import { makeMockTelemetry } from './mockTelemetry';

export type TelemetryState = {
  telemetry: SuitTelemetry | null;    // last good values, null until the first one arrives
  started: boolean;                   // EVA started?
  lastError: TSSErrorMessage | null;  // most recent tss_error, cleared by good data
  lastReceivedAt: number | null;      // HUD clock (ms) when the last message arrived
};

const initialState: TelemetryState = {
  telemetry: null,
  started: false,
  lastError: null,
  lastReceivedAt: null,
};

export function useTelemetry(): TelemetryState {
  const [state, setState] = useState<TelemetryState>(initialState);

  useEffect(() => {
    function handle(msg: BridgeMessage) {
      const receivedAt = Date.now();

      if (msg.type === 'telemetry') {
        setState({
          telemetry: msg.data.telemetry,
          started: msg.data.status.started,
          lastError: null,
          lastReceivedAt: receivedAt,
        });
      } else {
        // tss_error: keep the last values, just record the error
        setState(prev => ({ ...prev, lastError: msg, lastReceivedAt: receivedAt }));
      }
    }

    // SOURCE: fake data for now. Later this becomes the WebSocket.
    const timer = setInterval(() => handle(makeMockTelemetry()), 1000);
    return () => clearInterval(timer);
  }, []);

  return state;
}