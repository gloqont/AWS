import React from 'react';
import { EnhancedDecisionVisualizations } from './EnhancedDecisionVisualizations';

// Types for visualization data
type DecisionDeltaData = {
  before_composition: Array<{symbol: string, weight: number}>;
  after_composition: Array<{symbol: string, weight: number}>;
  delta_bar: {symbol: string, change: number};
};

type RiskFanChartData = {
  time_horizons: number[];
  base_case: number[];
  stress_case: number[];
  severe_stress_case: number[];
};

type ConcentrationShiftData = {
  before: Array<{ticker: string, weight: number}>;
  after: Array<{ticker: string, weight: number}>;
};

type RegimeSensitivityData = {
  regime_axes: string[];
  sensitivity_scores_before: {[key: string]: number};
  sensitivity_scores_after: {[key: string]: number};
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
  before_point: {risk: number; return: number; label: string};
  after_point: {risk: number; return: number; label: string};
  plane_limits: {min_risk: number; max_risk: number; min_return: number; max_return: number};
};

type ExposureHeatmapData = {
  sector_labels: string[];
  region_labels: string[];
  heatmap_matrix: number[][];
};

type RecoveryPathData = {
  time_points: number[];
  historical_recovery_paths: Array<{days: number; recovery_pct: number}>;
  current_portfolio_recovery: Array<{days: number; recovery_pct: number}>;
};

// Helper function to format percentages
function fmtPct(n: number) {
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

// Decision Delta Waterfall Visualization
const DecisionDeltaWaterfall: React.FC<{ data: DecisionDeltaData }> = ({ data }) => {
  if (!data || !data.before_composition || !data.after_composition) {
    return <div className='text-sm text-white/60'>No data available for waterfall chart</div>;
  }

  // Prepare data for visualization
  const beforeWeights = data.before_composition.slice(0, 5); // Top 5 positions
  const afterWeights = data.after_composition.slice(0, 5); // Top 5 positions

  // Calculate the change for the affected asset
  const deltaChange = data.delta_bar.change;

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Portfolio Composition Changes</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows portfolio composition before decision, the incremental change from this decision, and the final composition after the decision
      </div>

      <div className='space-y-2'>
        <div className='flex justify-between text-xs'>
          <span>Before Decision</span>
          <span>Decision Impact</span>
          <span>After Decision</span>
        </div>

        <div className='flex items-center space-x-1'>
          {/* Before composition bar */}
          <div className='flex-1 h-8 bg-gradient-to-r from-blue-500/30 to-blue-700/30 rounded flex items-center justify-center text-xs'>
            {beforeWeights.map((pos, idx) => (
              <div
                key={idx}
                className='h-full flex items-center justify-center px-1 border-r border-white/10 last:border-r-0'
                style={{ width: `${pos.weight}%` }}
                title={`${pos.symbol}: ${pos.weight}%`}
              >
                <span className='truncate'>{pos.symbol}</span>
              </div>
            ))}
          </div>

          {/* Delta bar */}
          <div
            className={`h-8 rounded flex items-center justify-center text-xs ${deltaChange >= 0 ? 'bg-green-500/30' : 'bg-red-500/30'}`}
            style={{ width: '15%' }}
            title={`Change: ${fmtPct(deltaChange)}`}
          >
            {fmtPct(deltaChange)}
          </div>

          {/* After composition bar */}
          <div className='flex-1 h-8 bg-gradient-to-r from-purple-500/30 to-purple-700/30 rounded flex items-center justify-center text-xs'>
            {afterWeights.map((pos, idx) => (
              <div
                key={idx}
                className='h-full flex items-center justify-center px-1 border-r border-white/10 last:border-r-0'
                style={{ width: `${pos.weight}%` }}
                title={`${pos.symbol}: ${pos.weight}%`}
              >
                <span className='truncate'>{pos.symbol}</span>
              </div>
            ))}
          </div>
        </div>

        <div className='flex justify-between text-xs'>
          <span>Before</span>
          <span>Δ Change</span>
          <span>After</span>
        </div>
      </div>
    </div>
  );
};

// Downside Risk Fan Chart Visualization
const DownsideRiskFanChart: React.FC<{ data: RiskFanChartData }> = ({ data }) => {
  if (!data || !data.time_horizons || !data.base_case) {
    return <div className='text-sm text-white/60'>No data available for risk fan chart</div>;
  }

  // Find min and max values for scaling
  const allValues = [...data.base_case, ...data.stress_case, ...data.severe_stress_case];
  const minValue = Math.min(...allValues, 0);
  const maxValue = Math.max(...allValues, 0);
  const range = maxValue - minValue || 1; // Avoid division by zero

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Downside Risk Evolution Over Time</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows how downside risk evolves over different time horizons under various stress scenarios
      </div>

      <div className='relative h-48 w-full bg-gray-900/30 rounded-lg border border-white/10 p-2'>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => (
          <div
            key={idx}
            className='absolute w-full border-t border-white/10 text-xs text-white/50'
            style={{ top: `${ratio * 100}%` }}
          >
            {fmtPct(minValue + (1 - ratio) * range)}
          </div>
        ))}

        {/* Time labels */}
        <div className='absolute bottom-0 left-0 right-0 flex justify-between text-xs text-white/70'>
          {data.time_horizons.map((time, idx) => (
            <div key={idx}>{time}d</div>
          ))}
        </div>

        {/* Severe stress case (outermost) */}
        <svg className='absolute inset-0 w-full h-full'>
          <polyline
            fill='rgba(220, 38, 38, 0.2)' // Red with opacity
            stroke='none'
            points={data.time_horizons.map((_, idx) => {
              const x = (idx / (data.time_horizons.length - 1)) * 100;
              const y = ((data.severe_stress_case[idx] - minValue) / range) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ') + ' ' +
            data.time_horizons.slice().reverse().map((_, idx) => {
              const x = ((data.time_horizons.length - 1 - idx) / (data.time_horizons.length - 1)) * 100;
              const y = ((data.base_case[data.time_horizons.length - 1 - idx] - minValue) / range) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ')}
          />
        </svg>

        {/* Stress case */}
        <svg className='absolute inset-0 w-full h-full'>
          <polyline
            fill='rgba(249, 115, 22, 0.3)' // Orange with opacity
            stroke='none'
            points={data.time_horizons.map((_, idx) => {
              const x = (idx / (data.time_horizons.length - 1)) * 100;
              const y = ((data.stress_case[idx] - minValue) / range) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ') + ' ' +
            data.time_horizons.slice().reverse().map((_, idx) => {
              const x = ((data.time_horizons.length - 1 - idx) / (data.time_horizons.length - 1)) * 100;
              const y = ((data.base_case[data.time_horizons.length - 1 - idx] - minValue) / range) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ')}
          />
        </svg>

        {/* Base case line */}
        <svg className='absolute inset-0 w-full h-full'>
          <polyline
            fill='none'
            stroke='#22c55e' // Green
            strokeWidth='2'
            points={data.time_horizons.map((_, idx) => {
              const x = (idx / (data.time_horizons.length - 1)) * 100;
              const y = ((data.base_case[idx] - minValue) / range) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ')}
          />
        </svg>

        {/* Legend */}
        <div className='absolute top-2 right-2 flex flex-col space-y-1 text-xs'>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-green-500 mr-1'></div>
            <span>Base Case</span>
          </div>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-orange-500 mr-1'></div>
            <span>Stress Case</span>
          </div>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-red-500 mr-1'></div>
            <span>Severe Stress</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Concentration Shift Chart Visualization
const ConcentrationShiftChart: React.FC<{ data: ConcentrationShiftData }> = ({ data }) => {
  if (!data || !data.before || !data.after) {
    return <div className='text-sm text-white/60'>No data available for concentration chart</div>;
  }

  // Take top 5 positions for both before and after
  const beforeTop5 = data.before.slice(0, 5);
  const afterTop5 = data.after.slice(0, 5);

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Concentration Shift Analysis</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows top holdings before and after the decision to visualize concentration changes
      </div>

      <div className='grid grid-cols-2 gap-4'>
        <div>
          <h4 className='text-sm font-medium mb-2'>Before Decision</h4>
          <div className='space-y-1'>
            {beforeTop5.map((pos, idx) => (
              <div key={idx} className='flex items-center'>
                <div className='w-20 text-xs truncate'>{pos.ticker}</div>
                <div className='flex-1 ml-2'>
                  <div
                    className='h-4 bg-blue-500/30 rounded-full overflow-hidden'
                    style={{ width: `${Math.abs(pos.weight)}%` }}
                  >
                    <div className='h-full bg-blue-500 flex items-center justify-end pr-1 text-xs text-white'>
                      {fmtPct(pos.weight)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className='text-sm font-medium mb-2'>After Decision</h4>
          <div className='space-y-1'>
            {afterTop5.map((pos, idx) => (
              <div key={idx} className='flex items-center'>
                <div className='w-20 text-xs truncate'>{pos.ticker}</div>
                <div className='flex-1 ml-2'>
                  <div
                    className='h-4 bg-purple-500/30 rounded-full overflow-hidden'
                    style={{ width: `${Math.abs(pos.weight)}%` }}
                  >
                    <div className='h-full bg-purple-500 flex items-center justify-end pr-1 text-xs text-white'>
                      {fmtPct(pos.weight)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Regime Sensitivity Map Visualization
const RegimeSensitivityMap: React.FC<{ data: RegimeSensitivityData }> = ({ data }) => {
  if (!data || !data.regime_axes || !data.sensitivity_scores_before) {
    return <div className='text-sm text-white/60'>No data available for regime sensitivity map</div>;
  }

  // Convert sensitivity keys to match the axes
  const sensitivityKeys = Object.keys(data.sensitivity_scores_before);
  const sensitivityLabels = {
    'volatility_spike': 'Volatility Spike',
    'liquidity_stress': 'Liquidity Stress',
    'rate_shock': 'Rate Shock',
    'growth_slowdown': 'Growth Slowdown',
    'credit_crisis': 'Credit Crisis',
    'currency_crisis': 'Currency Crisis'
  };

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Regime Sensitivity Analysis</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows how sensitive your portfolio is to different market regimes before and after the decision
      </div>

      <div className='overflow-x-auto'>
        <table className='w-full text-sm'>
          <thead>
            <tr>
              <th className='text-left p-2'>Regime</th>
              <th className='text-center p-2'>Before Decision</th>
              <th className='text-center p-2'>After Decision</th>
              <th className='text-center p-2'>Change</th>
            </tr>
          </thead>
          <tbody>
            {data.regime_axes.map((regime, idx) => {
              // Find corresponding sensitivity key
              const key = sensitivityKeys.find(k =>
                sensitivityLabels[k as keyof typeof sensitivityLabels] === regime
              );

              if (!key) return null;

              const beforeScore = data.sensitivity_scores_before[key] || 0;
              const afterScore = data.sensitivity_scores_after[key] || 0;
              const change = afterScore - beforeScore;

              return (
                <tr key={idx} className='border-t border-white/10'>
                  <td className='p-2'>{regime}</td>
                  <td className='p-2 text-center'>
                    <div className='flex items-center justify-center'>
                      <div
                        className='h-2 bg-blue-500 rounded-full'
                        style={{ width: `${beforeScore * 100}px`, maxWidth: '100px' }}
                      ></div>
                      <span className='ml-2'>{(beforeScore * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className='p-2 text-center'>
                    <div className='flex items-center justify-center'>
                      <div
                        className='h-2 bg-red-500 rounded-full'
                        style={{ width: `${afterScore * 100}px`, maxWidth: '100px' }}
                      ></div>
                      <span className='ml-2'>{(afterScore * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className={`p-2 text-center font-medium ${change > 0 ? 'text-red-400' : change < 0 ? 'text-green-400' : 'text-white'}`}>
                    {fmtPct(change * 100)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Irreversibility Horizon Chart Visualization
const IrreversibilityHorizonChart: React.FC<{ data: IrreversibilityHorizonData }> = ({ data }) => {
  if (!data || !data.holding_periods || !data.irreversible_losses) {
    return <div className='text-sm text-white/60'>No data available for irreversibility chart</div>;
  }

  // Find min and max values for scaling
  const minValue = Math.min(...data.irreversible_losses, data.recovery_zone_threshold || 0, 0);
  const maxValue = Math.max(...data.irreversible_losses, 0);
  const range = maxValue - minValue || 1; // Avoid division by zero

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Irreversibility Risk Over Time</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows how irreversible loss changes over different holding periods, with recovery zone highlighted
      </div>

      <div className='relative h-48 w-full bg-gray-900/30 rounded-lg border border-white/10 p-2'>
        {/* Recovery zone */}
        {data.recovery_zone_threshold !== undefined && (
          <div
            className='absolute left-0 right-0 bg-green-500/10 border-b border-green-500/30'
            style={{
              top: `${100 - ((data.recovery_zone_threshold - minValue) / range) * 100}%`,
              height: `${((data.recovery_zone_threshold - minValue) / range) * 100}%`
            }}
          >
            <div className='text-xs text-green-400 text-center pt-1'>Recovery Zone</div>
          </div>
        )}

        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => (
          <div
            key={idx}
            className='absolute w-full border-t border-white/10 text-xs text-white/50'
            style={{ top: `${ratio * 100}%` }}
          >
            {fmtPct(minValue + (1 - ratio) * range)}
          </div>
        ))}

        {/* Time labels */}
        <div className='absolute bottom-0 left-0 right-0 flex justify-between text-xs text-white/70'>
          {data.holding_periods.map((period, idx) => (
            <div key={idx}>{period}m</div>
          ))}
        </div>

        {/* Irreversible loss line */}
        <svg className='absolute inset-0 w-full h-full'>
          <polyline
            fill='none'
            stroke='#ef4444' // Red
            strokeWidth='2'
            strokeLinecap='round'
            strokeLinejoin='round'
            points={data.holding_periods.map((_, idx) => {
              const x = (idx / (data.holding_periods.length - 1)) * 100;
              const y = ((data.irreversible_losses[idx] - minValue) / range) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ')}
          />
          {/* Data points */}
          {data.holding_periods.map((_, idx) => {
            const x = (idx / (data.holding_periods.length - 1)) * 100;
            const y = ((data.irreversible_losses[idx] - minValue) / range) * 100;
            return (
              <circle
                key={idx}
                cx={`${x}%`}
                cy={`${(100 - y)}%`}
                r='4'
                fill='#ef4444'
              />
            );
          })}
        </svg>

        {/* Threshold line */}
        {data.recovery_zone_threshold !== undefined && (
          <svg className='absolute inset-0 w-full h-full pointer-events-none'>
            <line
              x1='0%'
              y1={`${100 - ((data.recovery_zone_threshold - minValue) / range) * 100}%`}
              x2='100%'
              y2={`${100 - ((data.recovery_zone_threshold - minValue) / range) * 100}%`}
              stroke='#22c55e'
              strokeWidth='1'
              strokeDasharray='4,4'
            />
          </svg>
        )}

        {/* Legend */}
        <div className='absolute top-2 right-2 flex flex-col space-y-1 text-xs'>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-red-500 mr-1'></div>
            <span>Irreversible Loss</span>
          </div>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-green-500 mr-1 dashed'></div>
            <span>Recovery Threshold</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Time-to-Damage Gauge Visualization
const TimeToDamageGauge: React.FC<{ data: TimeToDamageGaugeData }> = ({ data }) => {
  if (!data || !data.segments) {
    return <div className='text-sm text-white/60'>No data available for time-to-damage gauge</div>;
  }

  // Calculate the angle for the needle based on the current value
  const percentage = Math.min(1, Math.max(0, (data.current_value || 0) / (data.max_possible || 1)));
  const angle = -135 + (270 * percentage); // From -135° to 135°

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Time-to-Damage Assessment</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows the estimated time until material loss could occur based on current risk factors
      </div>

      <div className='flex flex-col items-center'>
        <div className='relative w-48 h-24'>
          {/* Gauge background */}
          <svg viewBox='0 0 200 100' className='w-full h-full'>
            {/* Colored segments */}
            {data.segments.map((segment, idx) => {
              const startPercent = segment.range[0] / data.max_possible;
              const endPercent = segment.range[1] / data.max_possible;
              const startAngle = -135 + (270 * startPercent);
              const endAngle = -135 + (270 * endPercent);

              // Convert angles to radians
              const startRad = (startAngle * Math.PI) / 180;
              const endRad = (endAngle * Math.PI) / 180;

              // Calculate coordinates
              const x1 = 100 + 80 * Math.cos(startRad);
              const y1 = 100 + 80 * Math.sin(startRad);
              const x2 = 100 + 80 * Math.cos(endRad);
              const y2 = 100 + 80 * Math.sin(endRad);

              // Large arc flag (1 if sweep > 180°, 0 otherwise)
              const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

              return (
                <path
                  key={idx}
                  d={`M ${x1} ${y1} A 80 80 0 ${largeArcFlag} 1 ${x2} ${y2} L 100 100 Z`}
                  fill={segment.color}
                  stroke='none'
                />
              );
            })}

            {/* Needle */}
            <line
              x1='100'
              y1='100'
              x2={100 + 70 * Math.cos((angle * Math.PI) / 180)}
              y2={100 + 70 * Math.sin((angle * Math.PI) / 180)}
              stroke='#ffffff'
              strokeWidth='3'
              strokeLinecap='round'
            />

            {/* Center circle */}
            <circle cx='100' cy='100' r='5' fill='#ffffff' />
          </svg>

          {/* Value display */}
          <div className='absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center'>
            <div className='text-lg font-bold'>{data.current_value || 0}</div>
            <div className='text-xs text-white/70'>days</div>
          </div>
        </div>

        {/* Labels */}
        <div className='flex justify-between w-full mt-4 text-xs'>
          <span>Immediate</span>
          <span>Long-term</span>
        </div>

        {/* Legend */}
        <div className='flex flex-wrap justify-center gap-2 mt-3'>
          {data.segments.map((segment, idx) => (
            <div key={idx} className='flex items-center'>
              <div
                className='w-3 h-3 mr-1 rounded-sm'
                style={{ backgroundColor: segment.color }}
              ></div>
              <span>{segment.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Risk-Return Trade-off Plane Visualization
const RiskReturnPlane: React.FC<{ data: RiskReturnPlaneData }> = ({ data }) => {
  if (!data || !data.before_point || !data.after_point) {
    return <div className='text-sm text-white/60'>No data available for risk-return plane</div>;
  }

  // Calculate scaling factors
  const riskRange = (data.plane_limits.max_risk - data.plane_limits.min_risk) || 1;
  const returnRange = (data.plane_limits.max_return - data.plane_limits.min_return) || 1;

  // Calculate positions as percentages
  const beforeX = ((data.before_point.risk - data.plane_limits.min_risk) / riskRange) * 100;
  const beforeY = 100 - ((data.before_point.return - data.plane_limits.min_return) / returnRange) * 100;
  const afterX = ((data.after_point.risk - data.plane_limits.min_risk) / riskRange) * 100;
  const afterY = 100 - ((data.after_point.return - data.plane_limits.min_return) / returnRange) * 100;

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Risk-Return Trade-off Analysis</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows the risk-return profile before and after the rebalancing decision
      </div>

      <div className='relative h-64 w-full bg-gray-900/30 rounded-lg border border-white/10 p-2'>
        {/* Grid lines */}
        <div className='absolute inset-0 grid grid-cols-5 grid-rows-5'>
          {[...Array(5)].map((_, i) => (
            <React.Fragment key={i}>
              <div className='border-r border-white/10'></div>
              <div className='border-t border-white/10'></div>
            </React.Fragment>
          ))}
        </div>

        {/* Axis labels */}
        <div className='absolute bottom-2 left-0 right-0 text-center text-xs text-white/70'>
          Portfolio Risk (Volatility)
        </div>
        <div
          className='absolute top-0 left-2 text-center text-xs text-white/70 transform -rotate-90 origin-center'
          style={{ writingMode: 'vertical-rl' }}
        >
          Expected Return
        </div>

        {/* Points and arrow */}
        <svg className='absolute inset-0 w-full h-full'>
          {/* Arrow from before to after */}
          <defs>
            <marker
              id='arrowhead'
              markerWidth='10'
              markerHeight='7'
              refX='9'
              refY='3.5'
              orient='auto'
            >
              <polygon
                points='0 0, 10 3.5, 0 7'
                fill='#3b82f6'
              />
            </marker>
          </defs>
          <line
            x1={`${beforeX}%`}
            y1={`${beforeY}%`}
            x2={`${afterX}%`}
            y2={`${afterY}%`}
            stroke='#3b82f6'
            strokeWidth='2'
            markerEnd='url(#arrowhead)'
          />

          {/* Before point */}
          <circle
            cx={`${beforeX}%`}
            cy={`${beforeY}%`}
            r='6'
            fill='#93c5fd'
            stroke='#ffffff'
            strokeWidth='2'
          />
          <text
            x={`${beforeX}%`}
            y={`${beforeY - 10}%`}
            textAnchor='middle'
            fill='#bfdbfe'
            fontSize='10'
          >
            Before
          </text>

          {/* After point */}
          <circle
            cx={`${afterX}%`}
            cy={`${afterY}%`}
            r='6'
            fill='#3b82f6'
            stroke='#ffffff'
            strokeWidth='2'
          />
          <text
            x={`${afterX}%`}
            y={`${afterY - 10}%`}
            textAnchor='middle'
            fill='#bfdbfe'
            fontSize='10'
          >
            After
          </text>
        </svg>

        {/* Legend */}
        <div className='absolute top-2 right-2 flex flex-col space-y-1 text-xs'>
          <div className='flex items-center'>
            <div className='w-3 h-3 bg-blue-300 rounded-full mr-1'></div>
            <span>Before</span>
          </div>
          <div className='flex items-center'>
            <div className='w-3 h-3 bg-blue-500 rounded-full mr-1'></div>
            <span>After</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Exposure Heatmap Visualization
const ExposureHeatmap: React.FC<{ data: ExposureHeatmapData }> = ({ data }) => {
  if (!data || !data.sector_labels || !data.region_labels || !data.heatmap_matrix) {
    return <div className='text-sm text-white/60'>No data available for exposure heatmap</div>;
  }

  // Calculate max value for color scaling
  const maxValue = Math.max(...data.heatmap_matrix.flat(), 1);

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Exposure Heatmap (Sector vs Region)</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows portfolio exposure across different sectors and regions before and after the rebalancing decision
      </div>

      <div className='overflow-x-auto'>
        <div className='inline-block min-w-full'>
          {/* Header with sector labels */}
          <div className='flex'>
            <div className='w-24'></div> {/* Empty corner cell */}
            {data.sector_labels.map((sector, idx) => (
              <div
                key={idx}
                className='flex-1 p-2 text-center text-xs rotate-45 origin-center transform'
                style={{ minWidth: '60px' }}
              >
                {sector}
              </div>
            ))}
          </div>

          {/* Rows with region labels and heatmap cells */}
          {data.region_labels.map((region, rowIdx) => (
            <div key={rowIdx} className='flex'>
              <div className='w-24 p-2 text-xs truncate'>{region}</div>
              {data.heatmap_matrix[rowIdx]?.map((value, colIdx) => {
                // Calculate color intensity based on value
                const intensity = Math.min(1, value / maxValue);
                const hue = 120; // Green
                const saturation = 70;
                const lightness = 70 - (intensity * 40); // Lighter for lower values

                return (
                  <div
                    key={colIdx}
                    className='flex-1 h-12 flex items-center justify-center text-xs border border-white/10'
                    style={{
                      backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
                      minWidth: '60px'
                    }}
                    title={`${region} - ${data.sector_labels[colIdx]}: ${value.toFixed(2)}%`}
                  >
                    {value > 0 ? value.toFixed(1) : ''}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Color scale */}
      <div className='mt-3'>
        <div className='text-xs text-white/70 mb-1'>Intensity Scale</div>
        <div className='h-4 w-full bg-gradient-to-r from-green-700 to-green-300 rounded'></div>
        <div className='flex justify-between text-xs text-white/70'>
          <span>Low</span>
          <span>High</span>
        </div>
      </div>
    </div>
  );
};

// Recovery Path Comparison Visualization
const RecoveryPathComparison: React.FC<{ data: RecoveryPathData }> = ({ data }) => {
  if (!data || !data.time_points || !data.historical_recovery_paths || !data.current_portfolio_recovery) {
    return <div className='text-sm text-white/60'>No data available for recovery path comparison</div>;
  }

  // Find max value for scaling
  const allHistorical = data.historical_recovery_paths.map(p => p.recovery_pct);
  const allCurrent = data.current_portfolio_recovery.map(p => p.recovery_pct);
  const maxValue = Math.max(...allHistorical, ...allCurrent, 100);

  return (
    <div className='w-full'>
      <h3 className='font-medium text-amber-200 mb-2'>Recovery Path Comparison</h3>
      <div className='text-xs text-white/60 mb-3'>
        Shows expected recovery paths based on historical analogs vs current portfolio after rebalancing
      </div>

      <div className='relative h-48 w-full bg-gray-900/30 rounded-lg border border-white/10 p-2'>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => (
          <div
            key={idx}
            className='absolute w-full border-t border-white/10 text-xs text-white/50'
            style={{ top: `${ratio * 100}%` }}
          >
            {(maxValue * (1 - ratio)).toFixed(0)}%
          </div>
        ))}

        {/* Time labels */}
        <div className='absolute bottom-0 left-0 right-0 flex justify-between text-xs text-white/70'>
          {data.time_points.map((time, idx) => (
            <div key={idx}>{time}d</div>
          ))}
        </div>

        {/* Historical path */}
        <svg className='absolute inset-0 w-full h-full'>
          <polyline
            fill='none'
            stroke='#60a5fa' // Blue
            strokeWidth='2'
            strokeLinecap='round'
            strokeLinejoin='round'
            points={data.historical_recovery_paths.map((point, idx) => {
              const x = (idx / (data.historical_recovery_paths.length - 1)) * 100;
              const y = ((point.recovery_pct) / maxValue) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ')}
          />
          {/* Data points for historical */}
          {data.historical_recovery_paths.map((point, idx) => {
            const x = (idx / (data.historical_recovery_paths.length - 1)) * 100;
            const y = ((point.recovery_pct) / maxValue) * 100;
            return (
              <circle
                key={`hist-${idx}`}
                cx={`${x}%`}
                cy={`${(100 - y)}%`}
                r='3'
                fill='#60a5fa'
              />
            );
          })}
        </svg>

        {/* Current portfolio path */}
        <svg className='absolute inset-0 w-full h-full'>
          <polyline
            fill='none'
            stroke='#fbbf24' // Yellow
            strokeWidth='2'
            strokeLinecap='round'
            strokeLinejoin='round'
            points={data.current_portfolio_recovery.map((point, idx) => {
              const x = (idx / (data.current_portfolio_recovery.length - 1)) * 100;
              const y = ((point.recovery_pct) / maxValue) * 100;
              return `${x}%,${(100 - y)}%`;
            }).join(' ')}
          />
          {/* Data points for current */}
          {data.current_portfolio_recovery.map((point, idx) => {
            const x = (idx / (data.current_portfolio_recovery.length - 1)) * 100;
            const y = ((point.recovery_pct) / maxValue) * 100;
            return (
              <circle
                key={`curr-${idx}`}
                cx={`${x}%`}
                cy={`${(100 - y)}%`}
                r='3'
                fill='#fbbf24'
              />
            );
          })}
        </svg>

        {/* Legend */}
        <div className='absolute top-2 right-2 flex flex-col space-y-1 text-xs'>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-blue-400 mr-1'></div>
            <span>Historical Analog</span>
          </div>
          <div className='flex items-center'>
            <div className='w-3 h-0.5 bg-yellow-400 mr-1'></div>
            <span>Current Portfolio</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main visualization component that renders all visualizations based on decision type
export const DecisionVisualizations: React.FC<{
  visualizationData: any;
  decisionType: string
}> = ({ visualizationData, decisionType }) => {
  if (!visualizationData) {
    return <div className='text-sm text-white/60'>No visualization data available</div>;
  }

  return (
    <div className='mt-6 space-y-6'>
      {/* Use the enhanced visualizations */}
      <EnhancedDecisionVisualizations visualizationData={visualizationData} decisionType={decisionType} />
    </div>
  );
};
