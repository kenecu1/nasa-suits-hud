import type { SuitTelemetry } from '../telemetry/types';

function VitalsPanel({ telemetry, stale }: { telemetry: SuitTelemetry | null; stale: boolean}) {
  if (!telemetry) {
    return <div className="panel">Waiting for data...</div>;
  }

  return (
    <div className={stale ? 'panel stale' : 'panel'}>
      Primary O2: {Math.round(telemetry.oxy_pri_storage)}%
    </div>
  );
}

export default VitalsPanel;