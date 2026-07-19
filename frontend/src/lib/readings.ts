export type Reading = { sensor_id: string; sensor_type: string; value: number }

export function getReading(readings: Reading[] | undefined, sensorType: string): number | undefined {
  return readings?.find(r => r.sensor_type === sensorType)?.value
}
