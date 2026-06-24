export type TrendMetrics = {
  direction: "upward" | "downward" | "stable";
  percentageChange: number;
  averageValue: number;
  dataPoints: number[];
};

export function analyzeMetricTrend(dataPoints: number[]): TrendMetrics {
  if (dataPoints.length < 2) {
    return { direction: "stable", percentageChange: 0, averageValue: dataPoints[0] || 0, dataPoints };
  }
  
  const firstVal = dataPoints[0];
  const lastVal = dataPoints[dataPoints.length - 1];
  const avg = dataPoints.reduce((s, x) => s + x, 0) / dataPoints.length;
  
  const delta = lastVal - firstVal;
  const percentageChange = firstVal !== 0 ? (delta / firstVal) * 100 : 0;
  
  let direction: "upward" | "downward" | "stable" = "stable";
  if (percentageChange > 5) {
    direction = "upward";
  } else if (percentageChange < -5) {
    direction = "downward";
  }
  
  return {
    direction,
    percentageChange: Math.round(percentageChange),
    averageValue: Math.round(avg),
    dataPoints
  };
}
