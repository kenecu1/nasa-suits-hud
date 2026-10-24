import './HudLayout.css';
import WarningBanner from '../panels/WarningBanner';
import BatteryPanel from '../panels/BatteryPanel';
import MapPanel from '../panels/MapPanel';
import MissionTracker from '../panels/MissionTracker';
import HeartRatePanel from '../panels/HeartRatePanel';
import VitalsPanel from '../panels/VitalsPanel';
import { useTelemetry } from '../telemetry/useTelemetry';

function HudLayout() {
  const { telemetry } = useTelemetry();
  return (
    <div className="hud">
      <div className="area-battery"><BatteryPanel /></div>
      <div className="area-warning"><WarningBanner /></div>
      <div className="area-map"><MapPanel /></div>
      <div className="area-tracker"><MissionTracker /></div>
      <div className="area-heart"><HeartRatePanel /></div>
      <div className="area-vitals"><VitalsPanel telemetry={telemetry} /></div>
    </div>
  );
}

export default HudLayout;