import { useState } from 'react';
import type { SuitTelemetry } from '../telemetry/types';

type Row = {
  label: string;
  key: keyof SuitTelemetry;  // must be a real field name from the contract
  unit: string;
  digits?: number;           // decimal places, 0 if left out
};

const ROWS: Row[] = [
  { label: 'Secondary battery',       key: 'secondary_battery_level', unit: '%' },
  { label: 'Secondary O2',            key: 'oxy_sec_storage',         unit: '%' },
  { label: 'Primary O2 pressure',     key: 'oxy_pri_pressure',        unit: 'psi' },
  { label: 'Secondary O2 pressure',   key: 'oxy_sec_pressure',        unit: 'psi' },
  { label: 'Suit O2 pressure',        key: 'suit_pressure_oxy',       unit: 'psi', digits: 2 },
  { label: 'Suit CO2 pressure',       key: 'suit_pressure_co2',       unit: 'psi', digits: 2 },
  { label: 'Suit other pressure',     key: 'suit_pressure_other',     unit: 'psi', digits: 2 },
  { label: 'Suit total pressure',     key: 'suit_pressure_total',     unit: 'psi', digits: 2 },
  { label: 'Helmet CO2 pressure',     key: 'helmet_pressure_co2',     unit: 'psi', digits: 2 },
  { label: 'Primary fan',             key: 'fan_pri_rpm',             unit: 'rpm' },
  { label: 'Secondary fan',           key: 'fan_sec_rpm',             unit: 'rpm' },
  { label: 'Scrubber A CO2',          key: 'scrubber_a_co2_storage',  unit: '%' },
  { label: 'Scrubber B CO2',          key: 'scrubber_b_co2_storage',  unit: '%' },
  { label: 'Suit temperature',        key: 'temperature',             unit: '°C', digits: 1 },
  { label: 'Coolant',                 key: 'coolant_storage',         unit: '%' },
  { label: 'Coolant gas pressure',    key: 'coolant_gas_pressure',    unit: 'psi' },
  { label: 'Coolant liquid pressure', key: 'coolant_liquid_pressure', unit: 'psi' },
  { label: 'O2 consumption',          key: 'oxy_consumption',         unit: 'psi/min', digits: 3 },
  { label: 'CO2 production',          key: 'co2_production',          unit: 'psi/min', digits: 3 },
  { label: 'EVA time',                key: 'eva_elapsed_time',        unit: 's' },
];

function SuitDetailsPanel({ telemetry, stale }: { telemetry: SuitTelemetry | null; stale: boolean }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={stale ? 'panel stale' : 'panel'}>
      <button className="details-toggle" onClick={() => setOpen(!open)}>
        Suit details {open ? '▾' : '▸'}
      </button>

      {open && !telemetry && <div>Waiting for data...</div>}

      {open && telemetry && (
        <table className="details-table">
          <tbody>
            {ROWS.map(row => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{telemetry[row.key].toFixed(row.digits ?? 0)} {row.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default SuitDetailsPanel;