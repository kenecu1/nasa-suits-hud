import type { TelemetryMessage } from './types';

const START_TIME = Date.now();

// adds small random noise so values look live
function jitter(value: number, amount: number): number {
  return value + (Math.random() - 0.5) * amount;
}

export function makeMockTelemetry(): TelemetryMessage {
  const elapsed = (Date.now() - START_TIME) / 1000; // seconds since the HUD started
  const minutes = elapsed / 60;

  return {
    type: 'telemetry',
    version: 1,
    timestamp: Date.now() / 1000, // Unix seconds, like Python time.time()
    data: {
      telemetry: {
        primary_battery_level: Math.max(0, 100 - minutes * 0.5),
        secondary_battery_level: 100,
        oxy_pri_storage: Math.max(0, 100 - minutes * 0.8),
        oxy_sec_storage: 100,
        oxy_pri_pressure: Math.max(0, 3000 - minutes * 24),
        oxy_sec_pressure: 3000,
        suit_pressure_oxy: jitter(4.0, 0.02),
        suit_pressure_co2: jitter(0.04, 0.005),
        suit_pressure_other: 0,
        suit_pressure_total: jitter(4.04, 0.02),
        helmet_pressure_co2: jitter(0.06, 0.005),
        fan_pri_rpm: jitter(30000, 200),
        fan_sec_rpm: 30000,
        scrubber_a_co2_storage: Math.min(100, minutes * 0.6),
        scrubber_b_co2_storage: 0,
        temperature: jitter(22.5, 0.4),
        coolant_storage: Math.max(0, 100 - minutes * 0.2),
        coolant_gas_pressure: 0,
        coolant_liquid_pressure: jitter(500, 5),
        heart_rate: jitter(90, 6),
        oxy_consumption: jitter(0.1, 0.01),
        co2_production: jitter(0.11, 0.01),
        eva_elapsed_time: Math.floor(elapsed),
      },
      status: { started: true },
      error: {
        fan_error: false,
        oxy_error: false,
        power_error: false,
        scrubber_error: false,
      },
    },
  };
}