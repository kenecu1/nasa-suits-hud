import type { TSSErrorMessage } from '../telemetry/types';

type Props = {
  started: boolean;
  lastError: TSSErrorMessage | null;
  bridgeOffline: boolean;
  versionMismatch: boolean;
};

type Level = 'nominal' | 'caution' | 'warning';

function getMessage(p: Props): { text: string; level: Level } {
  if (p.versionMismatch) {
    return { text: 'Contract version mismatch, update the HUD', level: 'warning' };
  }
  if (p.bridgeOffline) {
    return { text: 'Bridge offline', level: 'warning' };
  }
  if (p.lastError) {
    const what = p.lastError.reason === 'unreachable' ? 'TSS offline' : 'TSS sending bad data';
    const when = p.lastError.age !== null
      ? `, last data ${Math.round(p.lastError.age)}s ago`
      : ', no data received yet';
    return { text: what + when, level: 'warning' };
  }
  if (!p.started) {
    return { text: 'EVA not started', level: 'caution' };
  }
  return { text: 'All systems nominal', level: 'nominal' };
}

function WarningBanner(props: Props) {
  const { text, level } = getMessage(props);
  return <div className={`panel banner-${level}`}>{text}</div>;
}

export default WarningBanner;