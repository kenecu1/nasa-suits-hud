import type { SuitErrors, TSSErrorMessage } from '../telemetry/types';

type Props = {
  started: boolean;
  errors: SuitErrors | null;
  lastError: TSSErrorMessage | null;
  bridgeOffline: boolean;
  versionMismatch: boolean;
};

type Level = 'nominal' | 'caution' | 'warning';

// Plain-words name for each fault flag in the contract (section 4c)
const FAULT_NAMES: Record<keyof SuitErrors, string> = {
  fan_error: 'Fan fault',
  oxy_error: 'Oxygen fault',
  power_error: 'Power fault',
  scrubber_error: 'CO2 scrubber fault',
};

// The names of every flag that is true, so several faults can show at once
function activeFaults(errors: SuitErrors | null): string[] {
  if (!errors) return [];
  const keys = Object.keys(FAULT_NAMES) as (keyof SuitErrors)[];
  return keys.filter(key => errors[key]).map(key => FAULT_NAMES[key]);
}

// Priority, most serious first:
// 1. version mismatch  2. bridge offline  3. TSS error  (we can't trust any data)
// 4. suit faults       5. EVA not started  6. nominal
// A real fault beats "EVA not started" because it is more urgent.

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
    const faults = activeFaults(p.errors);
  if (faults.length > 0) {
    return { text: faults.join(', '), level: 'warning' };
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