import { useEffect, useState } from 'react';
import type { BridgeMessage, SuitTelemetry, TSSErrorMessage } from './types';
import { makeMockTelemetry } from './mockTelemetry';
import {config} from "../config";

export type TelemetryState = {
  telemetry: SuitTelemetry | null;    // last good values, null until the first one arrives
  started: boolean;                   // EVA started?
  lastError: TSSErrorMessage | null;  // most recent tss_error, cleared by good data
  lastReceivedAt: number | null; // HUD clock (ms) when the last message arrived
  versionMismatch: boolean;     
};

const initialState: TelemetryState = {
  telemetry: null,
  started: false,
  lastError: null,
  lastReceivedAt: null,
  versionMismatch: false,
};

export function useTelemetry(): TelemetryState & { bridgeOffline: boolean } {
  const [state, setState] = useState<TelemetryState>(initialState);

  const [startedAt] = useState(Date.now());
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    function handle(msg: BridgeMessage) {
      const receivedAt = Date.now();

      if (msg.version !== 1) {
        setState(prev => ({ ...prev, versionMismatch: true, lastReceivedAt: receivedAt }));
        return;
      }
      if (msg.type === 'telemetry') {
        setState({
          telemetry: msg.data.telemetry,
          started: msg.data.status.started,
          lastError: null,
          lastReceivedAt: receivedAt,
          versionMismatch: false,
        });
      } else {
        // tss_error: keep the last values, just record the error
        setState(prev => ({ ...prev, lastError: msg, lastReceivedAt: receivedAt }));
      }
    }

    // SOURCE 1: fake data 
    if (config.useMock) {
        const timer = setInterval(() => handle(makeMockTelemetry()), 1000);
        return () => clearInterval(timer);
    }

    // SOURCE 2: live bridge
    const ws = new WebSocket(config.bridgeUrl);
    ws.onmessage = (event) => {
      try {
        handle(JSON.parse(event.data) as BridgeMessage);
      } catch {
        console.warn('Unreadable message from bridge:', event.data);
      }
    };
        return () => ws.close();
  }, []);

  const lastSeen = state.lastReceivedAt ?? startedAt;
  const bridgeOffline = now - lastSeen > 3000;

  return { ...state, bridgeOffline };
}

