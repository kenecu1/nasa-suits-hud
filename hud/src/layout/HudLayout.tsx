import './HudLayout.css';
import WarningBanner from '../panels/WarningBanner';
import BatteryPanel from '../panels/BatteryPanel';
import MapPanel from '../panels/MapPanel';
import MissionTracker from '../panels/MissionTracker';
import HeartRatePanel from '../panels/HeartRatePanel';
import VitalsPanel from '../panels/VitalsPanel';
import SuitDetailsPanel from '../panels/SuitDetailsPanel';
import { useTelemetry } from '../telemetry/useTelemetry';

function HudLayout() {
  const { telemetry, started, lastError, bridgeOffline, versionMismatch } = useTelemetry();
  const stale = bridgeOffline || lastError !== null;

  return (
    <div className="hud">
      <div className="area-battery"><BatteryPanel telemetry={telemetry} stale={stale}/></div>
      <div className="area-warning">
        <WarningBanner
          started={started}
          lastError={lastError}
          bridgeOffline={bridgeOffline}
          versionMismatch={versionMismatch}
         />
      </div>
      <div className="area-map"><MapPanel /></div>
      <div className="area-details"><SuitDetailsPanel telemetry={telemetry} stale={stale} /></div>
      <div className="area-tracker"><MissionTracker /></div>
      <div className="area-heart"><HeartRatePanel telemetry = {telemetry} stale={stale}/></div>
      <div className="area-vitals"><VitalsPanel telemetry={telemetry} stale={stale}/></div>
    </div>
  );
}

export default HudLayout;