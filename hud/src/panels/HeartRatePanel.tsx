import type { SuitTelemetry } from '../telemetry/types';

function HeartRatePanel({ telemetry }: { telemetry: SuitTelemetry | null}) {
  if (!telemetry) {
    return <div className="panel">Waiting for data...</div>;
  }

  return (
    <div className="panel">
      Primary heart_rate: {Math.round(telemetry.heart_rate)}bpm
    </div>
  );
}

export default HeartRatePanel;