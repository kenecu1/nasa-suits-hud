// 4a. data.telemetry
export type SuitTelemetry = {
  primary_battery_level: number;    // %
  secondary_battery_level: number;  // %
  oxy_pri_storage: number;          // %
  oxy_sec_storage: number;          // %
  oxy_pri_pressure: number;         // psi
  oxy_sec_pressure: number;         // psi
  suit_pressure_oxy: number;        // psi, target 4.0
  suit_pressure_co2: number;        // psi
  suit_pressure_other: number;      // psi
  suit_pressure_total: number;      // psi
  helmet_pressure_co2: number;      // psi
  fan_pri_rpm: number;              // rpm
  fan_sec_rpm: number;              // rpm
  scrubber_a_co2_storage: number;   // %
  scrubber_b_co2_storage: number;   // %
  temperature: number;              // °C
  coolant_storage: number;          // %
  coolant_gas_pressure: number;     // psi
  coolant_liquid_pressure: number;  // psi
  heart_rate: number;               // bpm
  oxy_consumption: number;          // psi/min
  co2_production: number;           // psi/min
  eva_elapsed_time: number;         // seconds
};

// 4b. data.status
export type EvaStatus = {
  started: boolean;
};

// 4c. data.error
export type SuitErrors = {
  fan_error: boolean;
  oxy_error: boolean;
  power_error: boolean;
  scrubber_error: boolean;
};

// 4d. envelope telemetry
export type TelemetryMessage = {
  type: "telemetry";
  version: number;
  timestamp: number;  // Unix seconds
  data: {
    telemetry: SuitTelemetry;
    status: EvaStatus;
    error: SuitErrors;
  };
};

// 4e. TSSErrorMessage
export type TSSErrorMessage = {
    type: "tss_error";
    version: number;
    timestamp: number; // Unix seconds
    reason: "unreachable" | "bad_data";
    age: number | null; // Seconds, null if bridge never received good data
};

export type BridgeMessage = TelemetryMessage | TSSErrorMessage;




