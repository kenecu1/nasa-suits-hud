import type { SuitTelemetry } from '../telemetry/types';

function HeartRatePanel({ telemetry, stale }: { telemetry: SuitTelemetry | null; stale: boolean}) {
  if (!telemetry) {
    return <div className="panel">Waiting for data...</div>;
  }

  return (
    <div className={stale ? 'panel stale' : 'panel'}> 
      Heart rate: {Math.round(telemetry.heart_rate)} bpm
    </div>
  );
}

export default HeartRatePanel;