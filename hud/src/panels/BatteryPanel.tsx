import type { SuitTelemetry } from '../telemetry/types';

function BatteryPanel({ telemetry }: { telemetry: SuitTelemetry | null}) {
  if (!telemetry) {
    return <div className="panel">Waiting for data...</div>;
  }

  return (
    <div className="panel">
      Primary battery: {Math.round(telemetry.primary_battery_level)}%
    </div>
  );
}

export default BatteryPanel;