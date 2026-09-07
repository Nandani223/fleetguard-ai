export const RISK_COLORS = {
  Green: { fill: '#16A34A', text: 'text-risk-green', bg: 'bg-risk-green-soft', border: 'border-risk-green/20' },
  Amber: { fill: '#D97706', text: 'text-risk-amber', bg: 'bg-risk-amber-soft', border: 'border-risk-amber/20' },
  Red: { fill: '#E5484D', text: 'text-risk-red', bg: 'bg-risk-red-soft', border: 'border-risk-red/20' },
}

export const TELEMATICS_SIGNALS = [
  'coolant_temp_variance',
  'oil_pressure_dips',
  'battery_voltage_sag',
  'dtc_recurrence_rate',
  'harsh_braking_frequency',
  'overload_duty_share',
  'high_rpm_dwell_time',
  'short_trip_ratio',
  'idle_time_pct',
]

export function signalLabel(signal) {
  return signal
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ')
}

export function pct(value, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`
}
