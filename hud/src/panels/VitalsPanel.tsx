import type { SuitTelemetry } from '../telemetry/types';

function VitalsPanel({ telemetry }: { telemetry: SuitTelemetry | null}) {
  if (!telemetry) {
    return <div className="panel">Waiting for data...</div>;
  }

  return (
    <div className="panel">
      Primary O2: {Math.round(telemetry.oxy_pri_storage)}%
    </div>
  );
}

export default VitalsPanel;