export type TelemetryAnomaly = {
  timestamp: string;
  metric: "CPU" | "RAM" | "LATENCY" | "STORAGE";
  nodeName: string;
  value: number;
  threshold: number;
  details: string;
};

export function detectTelemetryAnomalies(metrics: {
  cpu: number;
  ram: number;
  latency: number;
  node: string;
}): TelemetryAnomaly[] {
  const anomalies: TelemetryAnomaly[] = [];
  const now = new Date().toISOString();
  
  if (metrics.cpu > 85) {
    anomalies.push({
      timestamp: now,
      metric: "CPU",
      nodeName: metrics.node,
      value: metrics.cpu,
      threshold: 85,
      details: `CPU utilization sustained at ${metrics.cpu}%, exceeding ZTA safety threshold.`
    });
  }
  
  if (metrics.latency > 5.0) {
    anomalies.push({
      timestamp: now,
      metric: "LATENCY",
      nodeName: metrics.node,
      value: metrics.latency,
      threshold: 5.0,
      details: `ICMP ping latency spike at ${metrics.latency.toFixed(1)}ms, indicating packet degradation.`
    });
  }
  
  return anomalies;
}
