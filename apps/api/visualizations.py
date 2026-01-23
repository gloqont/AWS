
"""
Visualization Components for GloQont

This module creates visual representations of trading decision consequences
using matplotlib, plotly, and other visualization libraries.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
from typing import Dict, List, Any, Optional
import io
import base64
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class RiskReturnVisualizer:
    """Visualizes risk-return characteristics of portfolio decisions"""
    
    @staticmethod
    def create_risk_return_plane(before_point: Dict[str, float], after_point: Dict[str, float], 
                                trade_off_arrow: Dict[str, Any]) -> go.Figure:
        """
        Create a risk-return plane showing before and after portfolio states
        
        Args:
            before_point: Dictionary with 'risk', 'return', 'label' keys
            after_point: Dictionary with 'risk', 'return', 'label' keys
            trade_off_arrow: Dictionary with 'direction', 'magnitude', 'risk_change', 'return_change' keys
        
        Returns:
            Plotly figure object
        """
        fig = go.Figure()
        
        # Add before point
        fig.add_trace(go.Scatter(
            x=[before_point['risk']], 
            y=[before_point['return']], 
            mode='markers+text',
            marker=dict(size=15, color='blue', symbol='circle'),
            text=[before_point['label']],
            textposition="top center",
            name="Before Decision",
            hovertemplate='<b>%{text}</b><br>' +
                         'Risk (Std Dev): %{x:.4f}<br>' +
                         'Expected Return: %{y:.4f}<extra></extra>'
        ))
        
        # Add after point
        fig.add_trace(go.Scatter(
            x=[after_point['risk']], 
            y=[after_point['return']], 
            mode='markers+text',
            marker=dict(size=15, color='red', symbol='diamond'),
            text=[after_point['label']],
            textposition="top center",
            name="After Decision",
            hovertemplate='<b>%{text}</b><br>' +
                         'Risk (Std Dev): %{x:.4f}<br>' +
                         'Expected Return: %{y:.4f}<extra></extra>'
        ))
        
        # Add arrow showing the trade-off
        fig.add_annotation(
            x=after_point['risk'],
            y=after_point['return'],
            ax=before_point['risk'],
            ay=before_point['return'],
            xref='x',
            yref='y',
            axref='x',
            ayref='y',
            showarrow=True,
            arrowhead=3,
            arrowsize=2,
            arrowwidth=2,
            arrowcolor='purple',
            text="Decision Impact",
            font=dict(color='purple')
        )
        
        fig.update_layout(
            title="Risk-Return Trade-off Analysis",
            xaxis_title="Risk (Standard Deviation)",
            yaxis_title="Expected Return",
            showlegend=True,
            width=800,
            height=600,
            template='plotly_white'
        )
        
        return fig


class ExposureHeatmapVisualizer:
    """Visualizes exposure heatmaps for portfolio decisions"""
    
    @staticmethod
    def create_exposure_heatmap(sector_exposure: Dict[str, float], regional_exposure: Dict[str, float],
                               heatmap_matrix: List[List[float]], sector_labels: List[str], 
                               region_labels: List[str]) -> go.Figure:
        """
        Create an exposure heatmap showing sector and regional exposures
        
        Args:
            sector_exposure: Dictionary mapping sectors to exposure percentages
            regional_exposure: Dictionary mapping regions to exposure percentages
            heatmap_matrix: 2D matrix of sector-region exposure values
            sector_labels: List of sector labels
            region_labels: List of region labels
        
        Returns:
            Plotly figure object
        """
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{"type": "heatmap", "rowspan": 2}, {"type": "bar"}],
                   [None, {"type": "bar"}]],
            subplot_titles=("Sector-Region Exposure Matrix", "Sector Exposure", "Regional Exposure"),
            vertical_spacing=0.1,
            horizontal_spacing=0.15
        )
        
        # Main heatmap
        fig.add_trace(
            go.Heatmap(
                z=heatmap_matrix,
                x=sector_labels,
                y=region_labels,
                colorscale='Viridis',
                text=np.round(heatmap_matrix, 2),
                texttemplate="%{text}",
                textfont={"size": 10},
                name="Exposure Matrix"
            ),
            row=1, col=1
        )
        
        # Sector exposure bar chart
        sectors = list(sector_exposure.keys())
        sector_values = list(sector_exposure.values())
        fig.add_trace(
            go.Bar(
                x=sector_values,
                y=sectors,
                orientation='h',
                name="Sector Exposure",
                marker_color='steelblue'
            ),
            row=1, col=2
        )
        
        # Regional exposure bar chart
        regions = list(regional_exposure.keys())
        region_values = list(regional_exposure.values())
        fig.add_trace(
            go.Bar(
                x=region_values,
                y=regions,
                orientation='h',
                name="Regional Exposure",
                marker_color='orange'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title="Portfolio Exposure Analysis",
            height=700,
            showlegend=False
        )
        
        return fig


class RecoveryPathVisualizer:
    """Visualizes recovery path comparisons"""
    
    @staticmethod
    def create_recovery_path_comparison(historical_paths: List[Dict[str, float]], 
                                     current_portfolio_paths: List[Dict[str, float]]) -> go.Figure:
        """
        Create a comparison of historical vs current portfolio recovery paths
        
        Args:
            historical_paths: List of dictionaries with 'days', 'recovery_pct' keys
            current_portfolio_paths: List of dictionaries with 'days', 'recovery_pct' keys
        
        Returns:
            Plotly figure object
        """
        fig = go.Figure()
        
        # Extract data
        hist_days = [p['days'] for p in historical_paths]
        hist_recovery = [p['recovery_pct'] for p in historical_paths]
        
        curr_days = [p['days'] for p in current_portfolio_paths]
        curr_recovery = [p['recovery_pct'] for p in current_portfolio_paths]
        
        # Add historical path
        fig.add_trace(go.Scatter(
            x=hist_days,
            y=hist_recovery,
            mode='lines+markers',
            name='Historical Analog Recovery',
            line=dict(color='blue', dash='dash'),
            marker=dict(size=6)
        ))
        
        # Add current portfolio path
        fig.add_trace(go.Scatter(
            x=curr_days,
            y=curr_recovery,
            mode='lines+markers',
            name='Current Portfolio Recovery',
            line=dict(color='red'),
            marker=dict(size=6)
        ))
        
        # Add reference line at 100% recovery
        fig.add_hline(y=100, line_dash="dot", line_color="green", 
                     annotation_text="Full Recovery", annotation_position="top right")
        
        fig.update_layout(
            title="Portfolio Recovery Path Comparison",
            xaxis_title="Days",
            yaxis_title="Recovery Percentage (%)",
            showlegend=True,
            template='plotly_white'
        )
        
        return fig


class TimeToDamageVisualizer:
    """Visualizes time-to-damage gauges"""
    
    @staticmethod
    def create_time_to_damage_gauge(current_value: int, max_possible: int, 
                                   segments: List[Dict[str, Any]]) -> go.Figure:
        """
        Create a gauge showing time to material loss
        
        Args:
            current_value: Current time to damage value
            max_possible: Maximum possible time value
            segments: List of segment dictionaries with 'range', 'label', 'color' keys
        
        Returns:
            Plotly figure object
        """
        # Create gauge with custom segments
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Time to Material Loss"},
            number={'suffix': " days"},
            gauge={
                'axis': {'range': [None, max_possible], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': segment['range'], 'color': segment['color']}
                    for segment in segments
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': current_value
                }
            }
        ))
        
        fig.update_layout(
            height=400,
            font={'color': "darkblue", 'family': "Arial"},
            template='plotly_white'
        )
        
        return fig


class RiskScenariosVisualizer:
    """Visualizes risk scenarios and fan charts"""
    
    @staticmethod
    def create_risk_scenario_fan_chart(fan_chart_data: Dict[str, List[float]]) -> go.Figure:
        """
        Create a fan chart showing risk scenarios
        
        Args:
            fan_chart_data: Dictionary with 'time_horizons', 'base_case', 'stress_case', 'severe_stress_case' keys
        
        Returns:
            Plotly figure object
        """
        fig = go.Figure()
        
        time_horizons = fan_chart_data['time_horizons']
        
        # Add base case
        fig.add_trace(go.Scatter(
            x=time_horizons,
            y=fan_chart_data['base_case'],
            mode='lines',
            name='Base Case',
            line=dict(color='green', width=2)
        ))
        
        # Add stress case
        fig.add_trace(go.Scatter(
            x=time_horizons,
            y=fan_chart_data['stress_case'],
            mode='lines',
            name='Stress Case',
            line=dict(color='orange', width=2)
        ))
        
        # Add severe stress case
        fig.add_trace(go.Scatter(
            x=time_horizons,
            y=fan_chart_data['severe_stress_case'],
            mode='lines',
            name='Severe Stress Case',
            line=dict(color='red', width=2)
        ))
        
        # Add confidence bands
        fig.add_trace(go.Scatter(
            x=time_horizons + time_horizons[::-1],
            y=fan_chart_data['stress_case'] + [-x for x in fan_chart_data['base_case'][::-1]],
            fill='toself',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False,
            name='Stress Band'
        ))
        
        fig.update_layout(
            title="Risk Scenario Fan Chart",
            xaxis_title="Time Horizon (Days)",
            yaxis_title="Expected Loss (%)",
            showlegend=True,
            template='plotly_white'
        )
        
        return fig


class ConcentrationVisualizer:
    """Visualizes portfolio concentration before and after decisions"""
    
    @staticmethod
    def create_concentration_comparison(before_data: List[Dict[str, float]], 
                                      after_data: List[Dict[str, float]]) -> go.Figure:
        """
        Create a comparison of portfolio concentration before and after decision
        
        Args:
            before_data: List of dictionaries with 'symbol', 'weight' keys
            after_data: List of dictionaries with 'symbol', 'weight' keys
        
        Returns:
            Plotly figure object
        """
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Before Decision', 'After Decision'),
            specs=[[{"type": "pie"}, {"type": "pie"}]]
        )
        
        # Before pie chart
        before_symbols = [item['symbol'] for item in before_data]
        before_weights = [item['weight'] for item in before_data]
        fig.add_trace(
            go.Pie(labels=before_symbols, values=before_weights, name="Before"),
            row=1, col=1
        )
        
        # After pie chart
        after_symbols = [item['symbol'] for item in after_data]
        after_weights = [item['weight'] for item in after_data]
        fig.add_trace(
            go.Pie(labels=after_symbols, values=after_weights, name="After"),
            row=1, col=2
        )
        
        fig.update_layout(
            title="Portfolio Concentration Comparison",
            height=600
        )
        
        return fig


class RegimeSensitivityVisualizer:
    """Visualizes regime sensitivity analysis"""
    
    @staticmethod
    def create_regime_sensitivity_chart(sensitivity_scores_before: Dict[str, float],
                                       sensitivity_scores_after: Dict[str, float],
                                       regime_axes: List[str]) -> go.Figure:
        """
        Create a radar chart showing regime sensitivity before and after decision
        
        Args:
            sensitivity_scores_before: Dictionary mapping regime axes to sensitivity scores
            sensitivity_scores_after: Dictionary mapping regime axes to sensitivity scores
            regime_axes: List of regime axis labels
        
        Returns:
            Plotly figure object
        """
        fig = go.Figure()
        
        # Prepare data for radar chart
        before_values = [sensitivity_scores_before[axis.lower().replace(' ', '_')] for axis in regime_axes]
        after_values = [sensitivity_scores_after[axis.lower().replace(' ', '_')] for axis in regime_axes]
        
        # Close the polygon
        before_values += [before_values[0]]
        after_values += [after_values[0]]
        regime_axes_closed = regime_axes + [regime_axes[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=before_values,
            theta=regime_axes_closed,
            fill='toself',
            name='Before Decision',
            line_color='blue'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=after_values,
            theta=regime_axes_closed,
            fill='toself',
            name='After Decision',
            line_color='red'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            showlegend=True,
            title="Regime Sensitivity Analysis"
        )
        
        return fig


class IrreversibilityVisualizer:
    """Visualizes irreversibility and time-to-recovery analysis"""
    
    @staticmethod
    def create_irreversibility_horizon_chart(horizon_chart_data: Dict[str, List[float]]) -> go.Figure:
        """
        Create a chart showing irreversible losses over different holding periods
        
        Args:
            horizon_chart_data: Dictionary with 'holding_periods', 'irreversible_losses' keys
        
        Returns:
            Plotly figure object
        """
        fig = go.Figure()
        
        holding_periods = horizon_chart_data['holding_periods']
        irreversible_losses = horizon_chart_data['irreversible_losses']
        recovery_zone_threshold = horizon_chart_data.get('recovery_zone_threshold', 0.05)
        
        fig.add_trace(go.Scatter(
            x=holding_periods,
            y=irreversible_losses,
            mode='lines+markers',
            name='Irreversible Loss',
            line=dict(color='red', width=3),
            marker=dict(size=8)
        ))
        
        # Add recovery zone threshold
        fig.add_hline(y=recovery_zone_threshold, line_dash="dash", line_color="green",
                     annotation_text="Recovery Zone Threshold", annotation_position="bottom right")
        
        fig.update_layout(
            title="Irreversible Loss Over Holding Periods",
            xaxis_title="Holding Period (Months)",
            yaxis_title="Irreversible Loss (%)",
            showlegend=True,
            template='plotly_white'
        )
        
        return fig


class GloQontVisualizer:
    """Main visualization class that orchestrates all visualizations"""
    
    def __init__(self):
        self.risk_return_viz = RiskReturnVisualizer()
        self.exposure_viz = ExposureHeatmapVisualizer()
        self.recovery_viz = RecoveryPathVisualizer()
        self.damage_viz = TimeToDamageVisualizer()
        self.scenario_viz = RiskScenariosVisualizer()
        self.concentration_viz = ConcentrationVisualizer()
        self.regime_viz = RegimeSensitivityVisualizer()
        self.irreversibility_viz = IrreversibilityVisualizer()
    
    def create_all_visualizations(self, visualization_data: Dict[str, Any]) -> Dict[str, go.Figure]:
        """
        Create all visualizations based on visualization data
        
        Args:
            visualization_data: Dictionary containing all visualization data
        
        Returns:
            Dictionary mapping visualization names to figure objects
        """
        figures = {}
        
        # Risk-Return Plane
        if 'risk_return_plane' in visualization_data:
            plane_data = visualization_data['risk_return_plane']
            figures['risk_return_plane'] = self.risk_return_viz.create_risk_return_plane(
                plane_data['before_point'],
                plane_data['after_point'],
                plane_data['trade_off_arrow']
            )
        
        # Exposure Heatmap
        if 'exposure_heatmap' in visualization_data:
            heatmap_data = visualization_data['exposure_heatmap']
            figures['exposure_heatmap'] = self.exposure_viz.create_exposure_heatmap(
                heatmap_data['sector_exposure'],
                heatmap_data['regional_exposure'],
                heatmap_data['heatmap_matrix'],
                heatmap_data['sector_labels'],
                heatmap_data['region_labels']
            )
        
        # Recovery Path Comparison
        if 'recovery_path_comparison' in visualization_data:
            recovery_data = visualization_data['recovery_path_comparison']
            figures['recovery_path_comparison'] = self.recovery_viz.create_recovery_path_comparison(
                recovery_data['historical_recovery_paths'],
                recovery_data['current_portfolio_recovery']
            )
        
        # Time to Damage Gauge
        if 'time_to_damage_gauge' in visualization_data:
            gauge_data = visualization_data['gauge_data']
            figures['time_to_damage_gauge'] = self.damage_viz.create_time_to_damage_gauge(
                gauge_data['current_value'],
                gauge_data['max_possible'],
                gauge_data['segments']
            )
        
        # Risk Scenarios Fan Chart
        if 'risk_scenarios' in visualization_data:
            scenario_data = visualization_data['risk_scenarios']
            figures['risk_scenario_fan_chart'] = self.scenario_viz.create_risk_scenario_fan_chart(
                scenario_data['fan_chart_data']
            )
        
        # Concentration Comparison
        if 'concentration_data' in visualization_data:
            concentration_data = visualization_data['concentration_data']
            figures['concentration_comparison'] = self.concentration_viz.create_concentration_comparison(
                concentration_data['before'],
                concentration_data['after']
            )
        
        # Regime Sensitivity Chart
        if 'regime_sensitivity' in visualization_data:
            regime_data = visualization_data['regime_sensitivity']
            figures['regime_sensitivity_chart'] = self.regime_viz.create_regime_sensitivity_chart(
                regime_data['sensitivity_scores_before'],
                regime_data['sensitivity_scores_after'],
                regime_data['regime_axes']
            )
        
        # Irreversibility Horizon Chart
        if 'irreversibility_data' in visualization_data:
            irreversibility_data = visualization_data['irreversibility_data']
            figures['irreversibility_horizon_chart'] = self.irreversibility_viz.create_irreversibility_horizon_chart(
                irreversibility_data['horizon_chart_data']
            )
        
        return figures
    
    def generate_interactive_dashboard(self, visualization_data: Dict[str, Any]) -> str:
        """
        Generate an interactive HTML dashboard with all visualizations
        
        Args:
            visualization_data: Dictionary containing all visualization data
        
        Returns:
            HTML string for the dashboard
        """
        figures = self.create_all_visualizations(visualization_data)
        
        html_parts = [
            "<html>",
            "<head><title>GloQont Decision Visualization Dashboard</title>",
            "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>",
            "</head>",
            "<body>",
            "<h1>GloQont: Decision Consequences Visualization</h1>"
        ]
        
        for name, fig in figures.items():
            div_id = name.replace(" ", "_").replace("-", "_")
            html_parts.append(f"<div id='{div_id}' style='width:100%;height:600px;'></div>")
            html_parts.append(f"<script>Plotly.newPlot('{div_id}', {fig.to_json()}, {{responsive: true}});</script>")
        
        html_parts.extend([
            "</body>",
            "</html>"
        ])
        
        return "\\n".join(html_parts)


# Example usage
if __name__ == "__main__":
    # Example data for testing
    sample_visualization_data = {
        "risk_return_plane": {
            "before_point": {"risk": 0.15, "return": 0.08, "label": "Before Decision"},
            "after_point": {"risk": 0.18, "return": 0.10, "label": "After Decision"},
            "trade_off_arrow": {"direction": "up_and_right", "magnitude": 0.05, "risk_change": 0.03, "return_change": 0.02}
        },
        "exposure_heatmap": {
            "sector_exposure": {"Technology": 30, "Finance": 25, "Healthcare": 20, "Consumer": 15, "Energy": 10},
            "regional_exposure": {"North America": 60, "Europe": 25, "Asia": 15},
            "heatmap_matrix": [[18, 15, 12], [15, 10, 8], [12, 8, 6], [9, 6, 4], [6, 4, 2]],
            "sector_labels": ["Technology", "Finance", "Healthcare", "Consumer", "Energy"],
            "region_labels": ["North America", "Europe", "Asia"]
        },
        "recovery_path_comparison": {
            "historical_recovery_paths": [{"days": 30, "recovery_pct": 25}, {"days": 60, "recovery_pct": 50}, {"days": 90, "recovery_pct": 75}],
            "current_portfolio_recovery": [{"days": 30, "recovery_pct": 20}, {"days": 60, "recovery_pct": 45}, {"days": 90, "recovery_pct": 70}]
        },
        "gauge_data": {
            "current_value": 90,
            "max_possible": 365,
            "segments": [
                {"range": [0, 14], "label": "Immediate", "color": "#ef4444"},
                {"range": [15, 45], "label": "Short-term", "color": "#f97316"},
                {"range": [46, 120], "label": "Medium-term", "color": "#eab308"},
                {"range": [121, 365], "label": "Long-term", "color": "#22c55e"}
            ]
        },
        "risk_scenarios": {
            "fan_chart_data": {
                "time_horizons": [1, 7, 14, 30, 60, 90, 180, 365],
                "base_case": [-0.01, -0.03, -0.05, -0.08, -0.12, -0.15, -0.18, -0.20],
                "stress_case": [-0.02, -0.06, -0.10, -0.15, -0.20, -0.25, -0.30, -0.35],
                "severe_stress_case": [-0.03, -0.09, -0.15, -0.22, -0.30, -0.38, -0.45, -0.50]
            }
        },
        "concentration_data": {
            "before": [{"symbol": "AAPL", "weight": 25}, {"symbol": "MSFT", "weight": 20}, {"symbol": "GOOGL", "weight": 15}],
            "after": [{"symbol": "AAPL", "weight": 20}, {"symbol": "MSFT", "weight": 25}, {"symbol": "TSLA", "weight": 10}]
        },
        "regime_sensitivity": {
            "sensitivity_scores_before": {"volatility_spike": 0.3, "liquidity_stress": 0.2, "rate_shock": 0.25, "growth_slowdown": 0.2, "credit_crisis": 0.35, "currency_crisis": 0.1},
            "sensitivity_scores_after": {"volatility_spike": 0.4, "liquidity_stress": 0.3, "rate_shock": 0.35, "growth_slowdown": 0.3, "credit_crisis": 0.45, "currency_crisis": 0.15},
            "regime_axes": ["Volatility Spike", "Liquidity Stress", "Rate Shock", "Growth Slowdown", "Credit Crisis", "Currency Crisis"]
        },
        "irreversibility_data": {
            "horizon_chart_data": {
                "holding_periods": [1, 3, 6, 12, 18, 24, 36],
                "irreversible_losses": [0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04],
                "recovery_zone_threshold": 0.05
            }
        }
    }
    
    # Create visualizer and generate dashboard
    visualizer = GloQontVisualizer()
    dashboard_html = visualizer.generate_interactive_dashboard(sample_visualization_data)
    
    
    # Create individual figures
    figures = visualizer.create_all_visualizations(sample_visualization_data)
    print(f"Created {len(figures)} visualization figures")
