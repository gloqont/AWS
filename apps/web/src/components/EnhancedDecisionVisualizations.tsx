import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ComposedChart,
  Scatter,
  ScatterChart,
  Cell,
  PieChart,
  Pie
} from 'recharts';

// Types for visualization data
type DecisionDeltaData = {
  before_composition: Array<{ symbol: string, weight: number }>;
  after_composition: Array<{ symbol: string, weight: number }>;
  delta_bar: { symbol: string, change: number };
};

type RiskFanChartData = {
  time_horizons: number[];
  base_case: number[];
  stress_case: number[];
  severe_stress_case: number[];
};

type ConcentrationShiftData = {
  before: Array<{ ticker: string, weight: number }>;
  after: Array<{ ticker: string, weight: number }>;
};

type RegimeSensitivityData = {
  regime_axes: string[];
  sensitivity_scores_before: { [key: string]: number };
  sensitivity_scores_after: { [key: string]: number };
};

type IrreversibilityHorizonData = {
  holding_periods: number[];
  irreversible_losses: number[];
  recovery_zone_threshold: number;
};

type TimeToDamageGaugeData = {
  current_value: number;
  max_possible: number;
  segments: Array<{
    range: [number, number];
    label: string;
    color: string;
  }>;
};

type RiskReturnPlaneData = {
  before_point: { risk: number; return: number; label: string };
  after_point: { risk: number; return: number; label: string };
  plane_limits: { min_risk: number; max_risk: number; min_return: number; max_return: number };
};

type ExposureHeatmapData = {
  sector_labels: string[];
  region_labels: string[];
  heatmap_matrix: number[][];
};

type RecoveryPathData = {
  time_points: number[];
  historical_recovery_paths: Array<{ days: number; recovery_pct: number }>;
  current_portfolio_recovery: Array<{ days: number; recovery_pct: number }>;
};

// Helper function to format percentages
function fmtPct(n: number) {
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

// Enhanced Decision Delta Waterfall Visualization
const EnhancedDecisionDeltaWaterfall: React.FC<{ data: DecisionDeltaData }> = ({ data }) => {
  if (!data || !data.before_composition || !data.after_composition) {
    return <div className='text-sm text-white/60'>No data available for waterfall chart</div>;
  }

  // Prepare data for visualization
  const beforeWeights = data.before_composition.slice(0, 5); // Top 5 positions
  const afterWeights = data.after_composition.slice(0, 5); // Top 5 positions
  const deltaChange = data.delta_bar.change;

  // Prepare data for the chart
  const chartData = [
    { name: 'Before', value: 100, type: 'before' },
    { name: 'Δ Change', value: deltaChange, type: 'delta' },
    { name: 'After', value: 100 + deltaChange, type: 'after' }
  ];

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Portfolio Composition Changes</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows portfolio composition before decision, the incremental change from this decision, and the final composition after the decision
      </div>

      <div className='h-64'>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis dataKey="name" stroke="#aaa" />
            <YAxis stroke="#aaa" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
              formatter={(value) => [`${value}%`, 'Weight']}
            />
            <Legend />
            <Bar dataKey="value" name="Portfolio Weight">
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.type === 'before' ? '#3b82f6' :
                      entry.type === 'delta' ? (deltaChange >= 0 ? '#10b981' : '#ef4444') :
                        '#10b981'
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed breakdown */}
      <div className='mt-4 grid grid-cols-3 gap-4'>
        <div className='bg-gray-800/50 p-3 rounded-lg'>
          <h4 className='text-sm font-medium mb-2'>Before Decision</h4>
          {beforeWeights.map((pos, idx) => (
            <div key={idx} className='flex justify-between text-xs py-1 border-b border-gray-700'>
              <span>{pos.symbol}</span>
              <span>{fmtPct(pos.weight)}</span>
            </div>
          ))}
        </div>

        <div className='bg-gray-800/50 p-3 rounded-lg'>
          <h4 className='text-sm font-medium mb-2'>Δ Change</h4>
          <div className='flex justify-between text-xs py-1'>
            <span>{data.delta_bar.symbol}</span>
            <span className={deltaChange >= 0 ? 'text-green-400' : 'text-red-400'}>
              {fmtPct(deltaChange)}
            </span>
          </div>
        </div>

        <div className='bg-gray-800/50 p-3 rounded-lg'>
          <h4 className='text-sm font-medium mb-2'>After Decision</h4>
          {afterWeights.map((pos, idx) => (
            <div key={idx} className='flex justify-between text-xs py-1 border-b border-gray-700'>
              <span>{pos.symbol}</span>
              <span>{fmtPct(pos.weight)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Enhanced Downside Risk Fan Chart Visualization
const EnhancedDownsideRiskFanChart: React.FC<{ data: RiskFanChartData }> = ({ data }) => {
  if (!data || !data.time_horizons || !data.base_case) {
    return <div className='text-sm text-white/60'>No data available for risk fan chart</div>;
  }

  // Prepare data for the chart
  const chartData = data.time_horizons.map((time, idx) => ({
    time: time,
    base_case: data.base_case[idx],
    stress_case: data.stress_case[idx],
    severe_stress_case: data.severe_stress_case[idx]
  }));

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Downside Risk Evolution Over Time</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows how downside risk evolves over different time horizons under various stress scenarios
      </div>

      <div className='h-80'>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis
              dataKey="time"
              stroke="#aaa"
              label={{ value: 'Time (days)', position: 'insideBottomRight', fill: '#aaa' }}
            />
            <YAxis
              stroke="#aaa"
              label={{ value: 'Risk Level', angle: -90, position: 'insideLeft', fill: '#aaa' }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="severe_stress_case"
              name="Severe Stress"
              stackId="1"
              stroke="#dc2626"
              fill="#dc2626"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="stress_case"
              name="Stress Case"
              stackId="1"
              stroke="#f97316"
              fill="#f97316"
              fillOpacity={0.3}
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="base_case"
              name="Base Case"
              stroke="#22c55e"
              strokeWidth={3}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Enhanced Concentration Shift Chart Visualization
const EnhancedConcentrationShiftChart: React.FC<{ data: ConcentrationShiftData }> = ({ data }) => {
  if (!data || !data.before || !data.after) {
    return <div className='text-sm text-white/60'>No data available for concentration chart</div>;
  }

  // Take top 5 positions for both before and after
  const beforeTop5 = data.before.slice(0, 5);
  const afterTop5 = data.after.slice(0, 5);

  // Prepare data for the chart
  const chartData = beforeTop5.map((pos, idx) => ({
    ticker: pos.ticker,
    before: pos.weight,
    after: afterTop5[idx]?.weight || 0
  }));

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Concentration Shift Analysis</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows top holdings before and after the decision to visualize concentration changes
      </div>

      <div className='h-80'>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis dataKey="ticker" stroke="#aaa" />
            <YAxis stroke="#aaa" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
              formatter={(value) => [`${value}%`, 'Weight']}
            />
            <Legend />
            <Bar dataKey="before" name="Before Decision" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="after" name="After Decision" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Helper function to convert regime axis labels to sensitivity score keys
// Maps "Volatility Spike" -> "volatility_spike", "Liquidity Stress" -> "liquidity_stress", etc.
function regimeToKey(regimeLabel: string): string {
  return regimeLabel
    .toLowerCase()
    .replace(/\s+/g, '_');
}

// Helper function to convert sensitivity score keys to regime axis labels
// Maps "volatility_spike" -> "Volatility Spike", "liquidity_stress" -> "Liquidity Stress", etc.
function keyToRegime(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Enhanced Regime Sensitivity Map Visualization
const EnhancedRegimeSensitivityMap: React.FC<{ data: RegimeSensitivityData }> = ({ data }) => {
  if (!data || !data.regime_axes || !data.sensitivity_scores_before) {
    return <div className='text-sm text-white/60'>No data available for regime sensitivity map</div>;
  }

  // Prepare data for the chart - use key mapping to properly access sensitivity scores
  const chartData = data.regime_axes.map((regime) => {
    // Convert regime label to key for lookup (e.g., "Volatility Spike" -> "volatility_spike")
    const key = regimeToKey(regime);
    const beforeScore = data.sensitivity_scores_before[key] ?? data.sensitivity_scores_before[regime] ?? 0;
    const afterScore = data.sensitivity_scores_after[key] ?? data.sensitivity_scores_after[regime] ?? 0;
    return {
      regime,
      before: parseFloat(beforeScore.toFixed(3)),
      after: parseFloat(afterScore.toFixed(3)),
      change: parseFloat((afterScore - beforeScore).toFixed(3))
    };
  });

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Regime Sensitivity Analysis</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows how sensitive your portfolio is to different market regimes before and after the decision
      </div>

      <div className='h-80'>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
            <PolarGrid stroke="#444" />
            <PolarAngleAxis dataKey="regime" tick={{ fill: '#aaa' }} />
            <PolarRadiusAxis angle={90} domain={[0, 1]} tick={{ fill: '#aaa' }} />
            <Radar
              name="Before Decision"
              dataKey="before"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.3}
            />
            <Radar
              name="After Decision"
              dataKey="after"
              stroke="#10b981"
              fill="#10b981"
              fillOpacity={0.3}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
              formatter={(value) => [typeof value === 'number' ? value.toFixed(2) : value, 'Value']}

            />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Additional table view for detailed data */}
      <div className='mt-4 overflow-x-auto'>
        <table className='w-full text-sm'>
          <thead>
            <tr className='border-b border-white/20'>
              <th className='text-left p-2'>Regime</th>
              <th className='text-center p-2'>Before</th>
              <th className='text-center p-2'>After</th>
              <th className='text-center p-2'>Change</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((item, idx) => (
              <tr key={idx} className='border-b border-white/10'>
                <td className='p-2'>{item.regime}</td>
                <td className='p-2 text-center'>{item.before.toFixed(3)}</td>
                <td className='p-2 text-center'>{item.after.toFixed(3)}</td>
                <td className={`p-2 text-center font-medium ${item.change > 0 ? 'text-red-400' : item.change < 0 ? 'text-green-400' : 'text-white'}`}>
                  {item.change >= 0 ? '+' : ''}{item.change.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Enhanced Irreversibility Horizon Chart Visualization
const EnhancedIrreversibilityHorizonChart: React.FC<{ data: IrreversibilityHorizonData }> = ({ data }) => {
  if (!data || !data.holding_periods || !data.irreversible_losses) {
    return <div className='text-sm text-white/60'>No data available for irreversibility chart</div>;
  }

  // Prepare data for the chart
  const chartData = data.holding_periods.map((period, idx) => ({
    period,
    irreversible_loss: data.irreversible_losses[idx],
    threshold: data.recovery_zone_threshold
  }));

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Irreversibility Risk Over Time</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows how irreversible loss changes over different holding periods, with recovery zone highlighted
      </div>

      <div className='h-80'>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis
              dataKey="period"
              stroke="#aaa"
              label={{ value: 'Holding Period (months)', position: 'insideBottomRight', fill: '#aaa' }}
            />
            <YAxis
              stroke="#aaa"
              label={{ value: 'Irreversible Loss', angle: -90, position: 'insideLeft', fill: '#aaa' }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="irreversible_loss"
              name="Irreversible Loss"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="threshold"
              name="Recovery Threshold"
              stroke="#22c55e"
              strokeDasharray="5 5"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Enhanced Time-to-Damage Gauge Visualization
const EnhancedTimeToDamageGauge: React.FC<{ data: TimeToDamageGaugeData }> = ({ data }) => {
  if (!data || !data.segments) {
    return <div className='text-sm text-white/60'>No data available for time-to-damage gauge</div>;
  }

  // Calculate the percentage for the current value
  const percentage = Math.min(1, Math.max(0, (data.current_value || 0) / (data.max_possible || 1)));

  // Prepare data for the pie chart (gauge-like)
  const gaugeData = [
    { name: 'Used', value: data.current_value || 0, color: '#ef4444' },
    { name: 'Remaining', value: (data.max_possible || 1) - (data.current_value || 0), color: '#374151' }
  ];

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Time-to-Damage Assessment</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows the estimated time until material loss could occur based on current risk factors
      </div>

      <div className='flex flex-col items-center'>
        <div className='w-64 h-64'>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={gaugeData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                startAngle={180}
                endAngle={0}
                paddingAngle={0}
                dataKey="value"
              >
                {gaugeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-lg font-bold fill-white"
              >
                {data.current_value || 0}d
              </text>
              <text
                x="50%"
                y="60%"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-sm fill-gray-400"
              >
                days
              </text>
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className='flex flex-wrap justify-center gap-4 mt-4'>
          {data.segments.map((segment, idx) => (
            <div key={idx} className='flex items-center'>
              <div
                className='w-4 h-4 mr-2 rounded-sm'
                style={{ backgroundColor: segment.color }}
              ></div>
              <span className='text-sm'>{segment.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Enhanced Risk-Return Trade-off Plane Visualization
const EnhancedRiskReturnPlane: React.FC<{ data: RiskReturnPlaneData }> = ({ data }) => {
  if (!data || !data.before_point || !data.after_point) {
    return <div className='text-sm text-white/60'>No data available for risk-return plane</div>;
  }

  // Prepare data for the chart
  const chartData = [
    {
      risk: data.before_point.risk,
      return: data.before_point.return,
      label: data.before_point.label,
      type: 'Before'
    },
    {
      risk: data.after_point.risk,
      return: data.after_point.return,
      label: data.after_point.label,
      type: 'After'
    }
  ];

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Risk-Return Trade-off Analysis</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows the risk-return profile before and after the rebalancing decision
      </div>

      <div className='h-80'>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart
            margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis
              type="number"
              dataKey="risk"
              name="Risk"
              label={{ value: 'Risk (Volatility)', position: 'insideBottomRight', fill: '#aaa' }}
              stroke="#aaa"
            />
            <YAxis
              type="number"
              dataKey="return"
              name="Return"
              label={{ value: 'Expected Return', angle: -90, position: 'insideLeft', fill: '#aaa' }}
              stroke="#aaa"
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
              formatter={(value) => [typeof value === 'number' ? value.toFixed(2) : value, 'Value']}
            />
            <Legend />
            <Scatter name="Risk-Return Points" data={chartData}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.type === 'Before' ? '#3b82f6' : '#10b981'}
                  stroke="#fff"
                  strokeWidth={2}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Enhanced Exposure Heatmap Visualization
const EnhancedExposureHeatmap: React.FC<{ data: ExposureHeatmapData }> = ({ data }) => {
  if (!data || !data.sector_labels || !data.region_labels || !data.heatmap_matrix) {
    return <div className='text-sm text-white/60'>No data available for exposure heatmap</div>;
  }

  // Prepare data for the chart
  const chartData: Array<{ sector: string, region: string, exposure: number }> = [];

  data.region_labels.forEach((region, rIdx) => {
    data.sector_labels.forEach((sector, sIdx) => {
      chartData.push({
        sector,
        region,
        exposure: data.heatmap_matrix[rIdx][sIdx]
      });
    });
  });

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Exposure Heatmap (Sector vs Region)</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows portfolio exposure across different sectors and regions before and after the rebalancing decision
      </div>

      <div className='h-96'>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart
            margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis
              type="category"
              dataKey="sector"
              name="Sector"
              stroke="#aaa"
            />
            <YAxis
              type="category"
              dataKey="region"
              name="Region"
              stroke="#aaa"
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
              formatter={(value) => [`${value}%`, 'Exposure']}
            />
            <Legend />
            <Scatter name="Exposure" data={chartData}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={`hsl(120, 70%, ${70 - (Math.min(1, entry.exposure) * 40)}%)`}
                  opacity={0.8}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Enhanced Recovery Path Comparison Visualization
const EnhancedRecoveryPathComparison: React.FC<{ data: RecoveryPathData }> = ({ data }) => {
  if (!data || !data.time_points || !data.historical_recovery_paths || !data.current_portfolio_recovery) {
    return <div className='text-sm text-white/60'>No data available for recovery path comparison</div>;
  }

  // Prepare data for the chart
  const chartData = data.time_points.map((time, idx) => ({
    time,
    historical: data.historical_recovery_paths[idx]?.recovery_pct || 0,
    current: data.current_portfolio_recovery[idx]?.recovery_pct || 0
  }));

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Recovery Path Comparison</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows expected recovery paths based on historical analogs vs current portfolio after rebalancing
      </div>

      <div className='h-80'>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
            <XAxis
              dataKey="time"
              stroke="#aaa"
              label={{ value: 'Time (days)', position: 'insideBottomRight', fill: '#aaa' }}
            />
            <YAxis
              stroke="#aaa"
              label={{ value: 'Recovery (%)', angle: -90, position: 'insideLeft', fill: '#aaa' }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="historical"
              name="Historical Analog"
              stroke="#60a5fa"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="current"
              name="Current Portfolio"
              stroke="#fbbf24"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Main enhanced visualization component that renders all visualizations based on decision type
export const EnhancedDecisionVisualizations: React.FC<{
  visualizationData: any;
  decisionType: string
}> = ({ visualizationData, decisionType }) => {
  if (!visualizationData) {
    return <div className='text-sm text-white/60'>No visualization data available</div>;
  }

  return (
    <div className='mt-6 space-y-6'>
      {/* V1. Enhanced Decision Delta Waterfall */}
      {visualizationData.decision_delta && (
        <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
          <EnhancedDecisionDeltaWaterfall data={visualizationData.decision_delta} />
        </div>
      )}

      {/* V2. Enhanced Downside Risk Fan Chart */}
      {visualizationData.risk_scenarios?.fan_chart_data && (
        <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
          <EnhancedDownsideRiskFanChart data={visualizationData.risk_scenarios.fan_chart_data} />
        </div>
      )}

      {/* V3. Enhanced Concentration Shift Chart */}
      {visualizationData.concentration_data && (
        <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
          <EnhancedConcentrationShiftChart data={visualizationData.concentration_data} />
        </div>
      )}

      {/* V4. Enhanced Regime Sensitivity Map */}
      {visualizationData.regime_sensitivity && (
        <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
          <EnhancedRegimeSensitivityMap data={visualizationData.regime_sensitivity} />
        </div>
      )}

      {/* V5. Enhanced Irreversibility Horizon Chart */}
      {visualizationData.irreversibility_data?.horizon_chart_data && (
        <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
          <EnhancedIrreversibilityHorizonChart data={visualizationData.irreversibility_data.horizon_chart_data} />
        </div>
      )}

      {/* Trade-specific visualizations */}
      {decisionType === 'trade_decision' && (
        <>
          {/* V6. Position Risk Profile - keeping original since it's informational */}
          {visualizationData.position_risk_profile && (
            <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
              <h3 className='font-medium text-amber-200 mb-2'>Position Risk Profile</h3>
              <div className='text-sm'>
                <div><strong>Asset:</strong> {visualizationData.position_risk_profile.asset}</div>
                <div><strong>Current Weight:</strong> {fmtPct(visualizationData.position_risk_profile.current_weight)}</div>
                <div><strong>Volatility Contribution:</strong> {fmtPct(visualizationData.position_risk_profile.volatility_contribution * 100)}</div>
                <div><strong>Drawdown Risk:</strong> {fmtPct(visualizationData.position_risk_profile.drawdown_risk * 100)}</div>

                <div className='mt-2'><strong>Before vs After Volatility:</strong></div>
                <div className='ml-2'>
                  <div>Before: {fmtPct(visualizationData.position_risk_profile.before_vs_after.volatility_before * 100)}</div>
                  <div>After: {fmtPct(visualizationData.position_risk_profile.before_vs_after.volatility_after * 100)}</div>
                  <div>Change: {fmtPct(visualizationData.position_risk_profile.before_vs_after.volatility_change * 100)}</div>
                </div>
              </div>
            </div>
          )}

          {/* V7. Enhanced Time-to-Damage Gauge */}
          {visualizationData.time_to_damage_gauge?.gauge_data && (
            <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
              <EnhancedTimeToDamageGauge data={visualizationData.time_to_damage_gauge.gauge_data} />
            </div>
          )}
        </>
      )}

      {/* Rebalancing-specific visualizations */}
      {decisionType === 'portfolio_rebalancing' && (
        <>
          {/* V8. Enhanced Risk–Return Trade-off Plane */}
          {visualizationData.risk_return_plane && (
            <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
              <EnhancedRiskReturnPlane data={visualizationData.risk_return_plane} />
            </div>
          )}

          {/* V9. Enhanced Exposure Heatmap */}
          {visualizationData.exposure_heatmap && (
            <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
              <EnhancedExposureHeatmap data={visualizationData.exposure_heatmap} />
            </div>
          )}

          {/* V10. Enhanced Recovery Path Comparison */}
          {visualizationData.recovery_path_comparison && (
            <div className='rounded-xl border border-white/10 bg-black/20 p-4'>
              <EnhancedRecoveryPathComparison data={visualizationData.recovery_path_comparison} />
            </div>
          )}
        </>
      )}
    </div>
  );
};