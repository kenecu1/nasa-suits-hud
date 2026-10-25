import type { SuitTelemetry } from '../telemetry/types';

function BatteryPanel({ telemetry, stale }: { telemetry: SuitTelemetry | null; stale: boolean}) {
  if (!telemetry) {
    return <div className="panel">Waiting for data...</div>;
  }

  return (
    <div className={stale ? 'panel stale' : 'panel'}>
      Primary battery: {Math.round(telemetry.primary_battery_level)}%
    </div>
  );
}

export default BatteryPanel;