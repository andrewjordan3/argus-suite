# argus/visualizations.py

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Literal

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from argus.models import DriverRiskProfile, StatisticalTest
from argus.utils import AnalysisContext

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class ForensicVisualizer:
    """
    Handles all visualization generation for the Fuel Card Forensic Analysis.
    Creates professional charts and dashboards for executive reporting.
    """

    # Color scheme for consistent branding
    COLORS: ClassVar[dict[str, str]] = {
        'target': '#E53935',  # Red for target location
        'others': '#1E88E5',  # Blue for other branches
        'primary': '#1E88E5',  # Blue for primary/normal data
        'success': '#43A047',  # Green for positive/diesel
        'warning': '#FB8C00',  # Orange for warnings
        'danger': '#E53935',  # Red for danger
        'neutral': '#757575',  # Gray for neutral
        'background': '#F5F5F5',  # Light gray background
    }

    def __init__(
        self,
        context: AnalysisContext
    ) -> None:
        """
        Initialize the visualizer.

        Args:
            target_location: Name of the target branch
            analysis_period: Period being analyzed (e.g., "2025 YTD")
            confidence_level: Statistical confidence level
            report_date: Date of report generation
        """
        self.context: AnalysisContext = context
        self.target_location: str = self.context.target_location_name
        self.analysis_period: str = self.context.analysis_period_label
        self.confidence_level: float = self.context.config.analysis.confidence_level
        self.save_path: Path = self.context.config.output.output_directory
        self.report_date: str = datetime.now(UTC).date().isoformat()

        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = '#FAFAFA'

    def create_executive_dashboard(
        self,
        monthly_data: pd.DataFrame,
        weekly_data: pd.DataFrame,
        risk_indicators: dict[str, float],
        statistical_tests: dict[str, Any],
        product_breakdown: pd.Series,
        high_volume_drivers: pd.DataFrame,
    ) -> Figure:
        """
        Create comprehensive executive dashboard with all key visualizations.

        Args:
            monthly_data: DataFrame with monthly statistics by branch
            weekly_data: DataFrame with weekly statistics by branch
            risk_indicators: dict with target and other branch percentages
            statistical_tests: dict with test results and p-values
            product_breakdown: Series with product counts for target location
            driver_risk_scores: DataFrame with driver risk scores
            save_path: Optional path to save the figure

        Returns:
            matplotlib Figure object
        """
        # Create figure with professional layout
        fig: Figure = plt.figure(figsize=(20, 14))
        fig.suptitle(
            'Fuel Card Forensic Analysis — Executive Dashboard',
            fontsize=18,
            fontweight='bold',
            y=0.98,
        )

        # Add subtitle with metadata
        fig.text(
            0.5,
            0.94,
            f'Analysis Period: {self.analysis_period} | '
            f'Report Date: {self.report_date} | '
            f'Confidence Level: {int(self.confidence_level * 100)}%',
            ha='center',
            fontsize=10,
            style='italic',
        )

        # Create grid layout
        gs: GridSpec = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3, top=0.91)

        # Generate each chart
        self._plot_risk_indicators(
            fig.add_subplot(gs[0, :2]), risk_indicators, statistical_tests
        )
        self._plot_statistical_panel(fig.add_subplot(gs[0, 2]), statistical_tests)
        self._plot_monthly_trend(fig.add_subplot(gs[1, :]), monthly_data)
        self._plot_product_breakdown(fig.add_subplot(gs[2, 0]), product_breakdown)
        # self._plot_monthly_spend(fig.add_subplot(gs[2, 1]), monthly_data)
        self._plot_weekly_spend(fig.add_subplot(gs[2, 1]), weekly_data)
        # self._plot_top_drivers(fig.add_subplot(gs[2, 2]), driver_risk_scores)
        self._plot_top_volume_drivers(fig.add_subplot(gs[2, 2]), high_volume_drivers)

        # plt.tight_layout(rect=[0, 0, 1, 0.93])

        if self.context.config.output.save_report:
            plt.savefig(self.save_path, dpi=300, bbox_inches='tight')

        return fig

    def _plot_risk_indicators(
        self,
        ax: Axes,
        risk_indicators: dict[str, float],
        statistical_tests: dict[str, Any],
    ) -> None:
        """Plot key risk indicators comparison bar chart."""
        metrics_data = pd.DataFrame(
            {
                self.target_location: [
                    risk_indicators['target_no_eld'],
                    risk_indicators['target_non_diesel'],
                    risk_indicators['target_after_hours'],
                ],
                'Other Branches': [
                    risk_indicators['others_no_eld'],
                    risk_indicators['others_non_diesel'],
                    risk_indicators['others_after_hours'],
                ],
            },
            index=['No ELD Match', 'Non-Diesel/DEF', 'After Hours/Weekend'],
        )

        metrics_data.plot(
            kind='bar',
            ax=ax,
            color=[self.COLORS['target'], self.COLORS['others']],
            width=0.7,
        )

        ax.set_title('Key Risk Indicators Comparison', fontsize=14, fontweight='bold')
        ax.set_ylabel('Percentage of Transactions (%)', fontsize=11)
        ax.set_xlabel('')
        ax.legend(title='Branch Group', frameon=True, fancybox=True)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

        # Add significance markers
        y_max: float = ax.get_ylim()[1]
        if statistical_tests.get('No ELD Match', {}).get('is_significant', False):
            ax.text(0, y_max * 0.95, '***', ha='center', fontsize=14, color='red')
        if statistical_tests.get('Non-Diesel/DEF Purchases', {}).get(
            'is_significant', False
        ):
            ax.text(1, y_max * 0.95, '***', ha='center', fontsize=14, color='red')
        if statistical_tests.get('After-Hours Transactions', {}).get(
            'is_significant', False
        ):
            ax.text(2, y_max * 0.95, '***', ha='center', fontsize=14, color='red')

    def _plot_statistical_panel(
        self, ax: Axes, statistical_tests: dict[str, Any]
    ) -> None:
        """Plot statistical significance information panel."""
        ax.axis('off')

        sig_text: str = 'STATISTICAL SIGNIFICANCE\n' + '─' * 30 + '\n\n'

        # No ELD Match
        if 'No ELD Match' in statistical_tests:
            test = statistical_tests['No ELD Match']
            sig_text += 'No ELD Match:\n'
            sig_text += f'  {self.context.report_formatter.format_p_value(test.get("p_value", 1.0))}\n'
            if 'risk_ratio' in test:
                rr: float = test['risk_ratio']
                rr_ci: tuple[float | None, float | None] = test.get(
                    'risk_ratio_ci', (None, None)
                )
                sig_text += f'  RR = {rr:.2f}'
                if rr_ci[0] is not None:
                    sig_text += f' [{rr_ci[0]:.2f}, {rr_ci[1]:.2f}]'
                sig_text += '\n'
            if 'effect_size' in test:
                sig_text += f"  Cramér's V = {test['effect_size']:.3f}\n"
            sig_text += '\n'

        # Non-Diesel Purchases
        if 'Non-Diesel/DEF Purchases' in statistical_tests:
            test = statistical_tests['Non-Diesel/DEF Purchases']
            sig_text += 'Non-Diesel Purchases:\n'
            sig_text += f'  {self.context.report_formatter.format_p_value(test.get("p_value", 1.0))}\n'
            if 'risk_ratio' in test:
                rr = test['risk_ratio']
                rr_ci = test.get('risk_ratio_ci', (None, None))
                sig_text += f'  RR = {rr:.2f}'
                if rr_ci[0] is not None:
                    sig_text += f' [{rr_ci[0]:.2f}, {rr_ci[1]:.2f}]'
                sig_text += '\n'
            sig_text += '\n'

        # After Hours
        if 'After-Hours Transactions' in statistical_tests:
            test = statistical_tests['After-Hours Transactions']
            sig_text += 'After Hours:\n'
            sig_text += f'  {self.context.report_formatter.format_p_value(test.get("p_value", 1.0))}\n\n'

        # Multiple Fillups
        if 'Multiple Same-Day Fillups' in statistical_tests:
            test = statistical_tests['Multiple Same-Day Fillups']
            sig_text += 'Multiple Fillups:\n'
            sig_text += f'  {self.context.report_formatter.format_p_value(test.get("p_value", 1.0))}\n'
            if 'risk_ratio' in test:
                sig_text += f'  RR = {test["risk_ratio"]:.2f}\n'
            sig_text += '\n'

        sig_text += 'Legend:\n'
        sig_text += '*** p < 0.001\n'
        sig_text += '**  p < 0.01\n'
        sig_text += '*   p < 0.05\n'
        sig_text += 'RR = Risk Ratio [95% CI]'

        ax.text(
            0.1,
            0.5,
            sig_text,
            fontsize=9,
            family='monospace',
            verticalalignment='center',
        )

    def _plot_monthly_trend(self, ax: Axes, monthly_data: pd.DataFrame) -> None:
        """Plot monthly trend of No ELD Match rate."""
        # Prepare data
        target_data: pd.DataFrame = monthly_data[
            monthly_data['branch_group'] == self.target_location
        ]
        others_data: pd.DataFrame = monthly_data[
            monthly_data['branch_group'] == 'Other Branches'
        ]

        # Get unique months (shared x-axis)
        all_months: list[str] = sorted(monthly_data['month_str'].unique())

        # Create dictionaries for easy lookup
        target_dict: dict[str, float] = dict(
            zip(target_data['month_str'], target_data['no_eld_rate'], strict=False)
        )
        others_dict: dict[str, float] = dict(
            zip(others_data['month_str'], others_data['no_eld_rate'], strict=False)
        )

        # Fill in data for all months (use NaN if missing)
        target_values: list[float] = [
            target_dict.get(month, np.nan) for month in all_months
        ]
        others_values: list[float] = [
            others_dict.get(month, np.nan) for month in all_months
        ]

        # Plot lines
        ax.plot(
            all_months,
            target_values,
            marker='o',
            linewidth=2.5,
            label=self.target_location,
            color=self.COLORS['target'],
            markersize=8,
        )

        ax.plot(
            all_months,
            others_values,
            marker='o',
            linewidth=2.5,
            label='Other Branches',
            color=self.COLORS['others'],
            markersize=8,
        )

        # Formatting
        if all_months:
            month_range: str = f'({all_months[0]} to {all_months[-1]})'
        else:
            month_range = ''

        ax.set_title(
            f'Monthly Trend: Transactions Without ELD Verification {month_range}',
            fontsize=14,
            fontweight='bold',
        )
        ax.set_xlabel('Month', fontsize=11)
        ax.set_ylabel('No ELD Match Rate (%)', fontsize=11)
        ax.legend(loc='best', frameon=True, fancybox=True)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)

        # If there are many months, show only every nth label
        if len(all_months) > 12:
            # Show every 2nd or 3rd month label
            step: Literal[2] | Literal[3] = 2 if len(all_months) <= 24 else 3
            ax.set_xticks(range(0, len(all_months), step))
            ax.set_xticklabels([all_months[i] for i in range(0, len(all_months), step)])

    def _plot_product_breakdown(self, ax: Axes, product_counts: pd.Series) -> None:
        """Plot pie chart of product breakdown."""
        # Group small categories
        if len(product_counts) > 4:
            top_4: pd.Series = product_counts.nlargest(4)
            other_count = product_counts.nsmallest(len(product_counts) - 4).sum()
            if other_count > 0:
                top_4['Other'] = other_count
            plot_data: pd.Series = top_4
        else:
            plot_data = product_counts

        # Define colors
        color_map: dict[str, str] = {
            'diesel': self.COLORS['success'],
            'def': self.COLORS['success'],
            'premium': self.COLORS['warning'],
            'gasoline': self.COLORS['target'],
            'regular': self.COLORS['warning'],
            'unknown': self.COLORS['neutral'],
            'Other': '#BDBDBD',
        }
        pie_colors: list[str] = [
            color_map.get(label.lower(), '#BDBDBD') for label in plot_data.index
        ]

        # Create pie chart
        wedges, _, autotexts = ax.pie(
            plot_data,
            labels=plot_data.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=pie_colors,
            wedgeprops={'edgecolor': 'white', 'linewidth': 1},
        )

        plt.setp(autotexts, size=8, weight='bold', color='white')
        ax.set_title(
            f'Product Breakdown ({self.target_location})',
            fontsize=14,
            fontweight='bold',
        )
        ax.axis('equal')

    def _plot_monthly_spend(self, ax: Axes, monthly_data: pd.DataFrame) -> None:
        """Plot monthly spend bar chart."""
        target_data = monthly_data[
            monthly_data['branch_group'] == self.target_location
        ].copy()

        if target_data.empty:
            ax.text(
                0.5,
                0.5,
                'No data available',
                ha='center',
                va='center',
                transform=ax.transAxes,
            )
            return

        # Sort by month
        target_data: pd.DataFrame = target_data.sort_values('month')

        bars: plt.BarContainer = ax.bar(
            target_data['month_str'],
            target_data['total_cost'],
            color=self.COLORS['target'],
            alpha=0.8,
            edgecolor='black',
            linewidth=1,
        )

        ax.set_title(
            f'Total Monthly Spend ({self.target_location})',
            fontsize=14,
            fontweight='bold',
        )
        ax.set_ylabel('Total Cost ($)', fontsize=11)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis='y')

        # Format Y-axis as currency
        formatter = mticker.FormatStrFormatter('$%1.0f')
        ax.yaxis.set_major_formatter(formatter)

        # Add value labels for high-value months
        max_height = target_data['total_cost'].max()
        threshold = max_height * 0.8

        # Add value labels for high-value months
        if len(target_data) > 0:
            max_height = target_data['total_cost'].max()
            threshold = max_height * 0.8

            for bar, (_, _) in zip(bars, target_data.iterrows()):
                height = bar.get_height()
                if height > threshold:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f'${height:,.0f}',
                        ha='center',
                        va='bottom',
                        fontsize=9,
                    )

    def _plot_weekly_spend(self, ax: Axes, weekly_stats: pd.DataFrame) -> None:
        """
        Plot weekly spend for the most recent ~12 months (last 52 weeks) without rebuilding datetimes.

        Expectations for `weekly_stats` (already prepared upstream):
            - Columns:
                'year' (int, ISO year),
                'week_number' (int, ISO week 1..52/53),
                'branch_group' (str),
                'total_cost' (float),
                'week_str' (str, e.g., '2024-W05')
            - Sorted by ['year', 'week_number'] ascending before calling this method
            - Contains all locations; this method filters to self.target_location

        Visualization choices (executive-friendly):
            - Primary weekly line for actuals (52 points)
            - Subtle area fill for visual weight (low alpha to avoid clutter)
            - 4-week rolling mean to stabilize noise and reveal trend
            - Sparse x-axis labeling (~12 ticks) using `week_str`, not every week
            - Currency formatting on the Y-axis
            - Last-point annotation for quick read
        """
        # -------------------------------
        # 1) Validate inputs and filter
        # -------------------------------
        required_cols: set[str] = {
            'year',
            'week_number',
            'branch_group',
            'total_cost',
            'week_str',
        }
        missing: set[str] = required_cols - set(weekly_stats.columns)
        if missing:
            ax.text(
                0.5,
                0.5,
                f'Missing columns: {", ".join(sorted(missing))}',
                ha='center',
                va='center',
                transform=ax.transAxes,
            )
            return

        # Scope to the same location as monthly (branch_group == self.target_location)
        data: pd.DataFrame = weekly_stats[
            weekly_stats['branch_group'] == self.target_location
        ].copy()
        if data.empty:
            ax.text(
                0.5,
                0.5,
                'No data available',
                ha='center',
                va='center',
                transform=ax.transAxes,
            )
            return

        # Ensure chronological order (should already be sorted upstream)
        data = data.sort_values(['year', 'week_number'], kind='mergesort')

        # -------------------------------
        # 2) Rolling window: last 52 weeks
        # -------------------------------
        data_window: pd.DataFrame = data.tail(52).reset_index(drop=True)
        if data_window.empty:
            ax.text(
                0.5,
                0.5,
                'No recent weekly data',
                ha='center',
                va='center',
                transform=ax.transAxes,
            )
            return

        # 4-week rolling mean for trend
        data_window['rolling_4wk_mean'] = (
            data_window['total_cost'].rolling(window=4, min_periods=1).mean()
        )

        # -------------------------------
        # 3) Plot primitives
        # -------------------------------
        x_positions: NDArray[np.int64] = np.arange(len(data_window))  # 0..N-1
        y_weekly: NDArray[np.float64] = data_window['total_cost'].to_numpy(dtype=np.float64)
        y_trend: NDArray[np.float64] = data_window['rolling_4wk_mean'].to_numpy(dtype=np.float64)

        color_week: str = self.COLORS.get(
            'target', '#E53935'
        )  # red for target location
        color_trend: str = self.COLORS.get('others', '#1E88E5')  # blue for trend
        color_neutral: str = self.COLORS.get(
            'neutral', '#757575'
        )  # gray for labels/grid

        # Weekly line (actuals)
        ax.plot(
            x_positions,
            y_weekly,
            linewidth=1.6,
            color=color_week,
            alpha=0.95,
            label='Weekly',
        )

        # Subtle area fill for visual weight
        ax.fill_between(x_positions, y_weekly, step=None, alpha=0.08, color=color_week)

        # Rolling trend (4-week avg)
        ax.plot(
            x_positions,
            y_trend,
            linewidth=2.6,
            color=color_trend,
            alpha=0.95,
            label='4-wk avg',
        )

        # -------------------------------
        # 4) Axes styling & currency
        # -------------------------------
        ax.set_title(
            f'Weekly Spend (Last 52 Weeks) — {self.target_location}',
            fontsize=14,
            fontweight='bold',
        )
        ax.set_ylabel('Total Cost ($)', fontsize=11)

        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
        ax.grid(True, which='major', axis='y', alpha=0.3)

        # Sparse X tick labels (~12 evenly spaced)
        n_points: int = len(data_window)
        if n_points > 1:
            desired_ticks: int = min(12, n_points)
            tick_positions: NDArray[np.int64] = np.unique(
                np.linspace(0, n_points - 1, num=desired_ticks, dtype=int)
            )
            tick_labels: list[str] = data_window.iloc[tick_positions]['week_str'].tolist()
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=9)
        else:
            ax.set_xticks([0])
            ax.set_xticklabels(
                [data_window.iloc[0]['week_str']], rotation=0, ha='center', fontsize=9
            )

        # -------------------------------
        # 5) Label high-value weeks (>80% max), matching monthly behavior
        # -------------------------------
        if n_points > 0:
            max_height = float(np.nanmax(y_weekly))
            threshold: float = max_height * 0.8

            # Only annotate points above the threshold; nudge labels slightly upward
            for xi, yi, _ in zip(x_positions, y_weekly, data_window['week_str'], strict=False):
                if yi > threshold:
                    ax.text(
                        xi,
                        yi,
                        f'${yi:,.0f}',
                        ha='center',
                        va='bottom',
                        fontsize=9,
                        color=color_neutral,
                        clip_on=True,  # avoid spilling outside axes
                    )

        # Last-point annotation for quick read (like the monthly callout)
        last_x = x_positions[-1]
        last_y = y_weekly[-1]
        ax.text(
            last_x + 0.5,
            last_y,
            f' ${last_y:,.0f}',
            va='center',
            ha='left',
            fontsize=9,
            color=color_neutral,
        )

        # Legend without frame
        ax.legend(loc='upper left', frameon=False)

    def _plot_top_drivers(self, ax: Axes, driver_risk_scores: pd.DataFrame) -> None:
        """Plot horizontal bar chart of top high-risk drivers."""
        top_drivers: pd.DataFrame = driver_risk_scores.head(5)

        bars: plt.BarContainer = ax.barh(
            range(len(top_drivers)),
            top_drivers['risk_score'].to_numpy(),
            color=self.COLORS['warning'],
            edgecolor='black',
            linewidth=1,
        )

        ax.set_yticks(range(len(top_drivers)))
        ax.set_yticklabels(top_drivers['driver_name'].values, fontsize=9)
        ax.set_xlabel('Risk Score', fontsize=11)
        ax.set_title('Top High-Risk Drivers', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()
        ax.set_xlim(0, 100)

        # Add value labels
        for i, (_, score) in enumerate(
            zip(bars, top_drivers['risk_score'].to_numpy(), strict=False)
        ):
            ax.text(score + 1, i, f'{score:.1f}', va='center', fontsize=9)

    def _plot_top_volume_drivers(
        self, ax: Axes, high_volume_drivers: pd.DataFrame
    ) -> None:
        """Plot horizontal bar chart of top high-volume drivers."""
        top_drivers: pd.DataFrame = high_volume_drivers.head(3)

        if top_drivers.empty:
            ax.text(
                0.5,
                0.5,
                'No volume data available',
                ha='center',
                va='center',
                fontsize=12,
            )
            ax.set_title('Top High-Volume Drivers', fontsize=14, fontweight='bold')
            return

        # Create bars colored by z-score (red for high outliers)
        colors: list[str] = []
        for z_score in top_drivers['volume_z_score'].array:
            if z_score > 2.0:
                colors.append(self.COLORS['danger'])  # Red for outliers
            elif z_score > 1.5:
                colors.append(self.COLORS['warning'])  # Orange/yellow for elevated
            else:
                colors.append(self.COLORS['primary'])  # Blue for normal

        bars: plt.BarContainer = ax.barh(
            range(len(top_drivers)),
            top_drivers['total_volume'].to_numpy(),
            color=colors,
            edgecolor='black',
            linewidth=1,
        )

        ax.set_yticks(range(len(top_drivers)))
        ax.set_yticklabels(top_drivers['driver_name'].values, fontsize=9)
        ax.set_xlabel('Total Volume (gallons)', fontsize=11)
        ax.set_title('Top High-Volume Drivers', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()

        # Add value labels with z-score
        for i, (_, volume, z_score) in enumerate(
            zip(
                bars,
                top_drivers['total_volume'].values,
                top_drivers['volume_z_score'].values,
                strict=False
            )
        ):
            # Volume label
            ax.text(
                volume + (volume * 0.02),
                i,
                f'{volume:,.0f}',
                va='center',
                fontsize=9,
                fontweight='bold',
            )

            # Z-score label (if significant)
            if z_score > 1.5:
                ax.text(
                    volume * 0.98,
                    i,
                    f'z={z_score:.1f}',
                    va='center',
                    ha='right',
                    fontsize=8,
                    color='white',
                    fontweight='bold',
                )

    def show(self) -> None:
        """Display all open figures."""
        plt.show()

    def close_all(self) -> None:
        """Close all open figures."""
        plt.close('all')


def prepare_visualization_data(
    context: AnalysisContext,
    all_tests: dict[str, StatisticalTest],
    driver_profiles: list[DriverRiskProfile],
    high_volume_drivers: list[DriverRiskProfile],
) -> dict[str, Any]:
    """
    Prepare all data needed for visualizations.

    Args:
        full_df: Complete dataset
        target_location: Target location data
        others: Other branches data
        target_name: Name of target location
        all_tests: dictionary of statistical test results
        driver_profiles: list of driver risk profiles
        high_volume_drivers: list of high volume driver profiles

    Returns:
        dictionary containing prepared visualization data
    """
    complete_df: pd.DataFrame = context.complete_unsplit_transactions.copy()
    target_df: pd.DataFrame = context.target_period_transactions.copy()
    peers_df: pd.DataFrame = context.peer_period_transactions.copy()

    # Helper function to avoid Pylance "partially unknown type" warnings from
    # lambda expressions.
    def percent_false(x: pd.Series) -> float:
        """
        Helper function to compute and return the percentage
        of False values (as a float between 0 and 100).
        """
        return 100 * (~x).mean()

    # Calculate monthly aggregates
    monthly_stats: pd.DataFrame = (
        complete_df.groupby(['month', 'branch_group'])
        .agg(
            {
                'has_eld_activity': percent_false,
                'is_diesel_def': percent_false,
                'cost': 'sum',
                'datetime_parsed': 'nunique',
            }
        )
        .rename(
            columns={
                'has_eld_activity': 'no_eld_rate',
                'is_diesel_def': 'non_diesel_rate',
                'cost': 'total_cost',
                'datetime_parsed': 'transaction_count',
            }
        )
        .round(1)
    )

    # Reset index to make month and branch_group regular columns
    monthly_stats = monthly_stats.reset_index()

    # Convert Period to string with year-month format (e.g., "2024-01")
    monthly_stats['month_str'] = monthly_stats['month'].astype(str)

    # Sort by month to ensure proper ordering
    monthly_stats: pd.DataFrame = monthly_stats.sort_values('month')

    # Calculate weekly aggregates for the full dataset
    weekly_stats = (
        complete_df.groupby(['year', 'week_number', 'branch_group'])
        .agg(
            {
                'has_eld_activity': percent_false,
                'is_diesel_def': percent_false,
                'cost': 'sum',
                'datetime_parsed': 'nunique',
            }
        )
        .rename(
            columns={
                'has_eld_activity': 'no_eld_rate',
                'is_diesel_def': 'non_diesel_rate',
                'cost': 'total_cost',
                'datetime_parsed': 'transaction_count',
            }
        )
        .round(1)
    )

    # Reset index to make year and week_number regular columns
    weekly_stats = weekly_stats.reset_index()

    # Create a combined string for plotting (e.g., "2024-W05")
    # This is analogous to the 'month_str' column
    weekly_stats['week_str'] = (
        weekly_stats['year'].astype(str)
        + '-W'
        + weekly_stats['week_number'].astype(str).str.zfill(2)
    )

    # Sort by year and week to ensure proper ordering for charts
    weekly_stats: pd.DataFrame = weekly_stats.sort_values(['year', 'week_number'])

    # Calculate risk indicators
    risk_indicators: dict[str, float] = {
        'target_no_eld': 100 * (~target_df['has_eld_activity']).mean(),
        'target_non_diesel': 100 * (~target_df['is_diesel_def']).mean(),
        'target_after_hours': 100 * (~target_df['is_business_hours']).mean(),
        'others_no_eld': 100 * (~peers_df['has_eld_activity']).mean(),
        'others_non_diesel': 100 * (~peers_df['is_diesel_def']).mean(),
        'others_after_hours': 100 * (~peers_df['is_business_hours']).mean(),
    }

    # Prepare statistical tests for visualization
    viz_tests: dict[str, dict[str, Any]] = {}
    for test_name, test_obj in all_tests.items():
        viz_tests[test_name] = {
            'p_value': test_obj.p_value,
            'is_significant': test_obj.is_significant,
            'risk_ratio': test_obj.risk_ratio,
            'risk_ratio_ci': test_obj.risk_ratio_ci,
            'effect_size': test_obj.effect_size,
        }

    # Product breakdown for target location
    product_breakdown: pd.Series[int] = target_df['product_clean'].value_counts()

    # Driver risk scores - handle empty list
    if driver_profiles and len(driver_profiles) > 0:
        driver_risk_df = pd.DataFrame(
            [
                {'driver_name': p.driver_name, 'risk_score': p.risk_score}
                for p in driver_profiles
            ]
        )
        # Sort by risk score descending
        driver_risk_df: pd.DataFrame = driver_risk_df.sort_values(
            'risk_score', ascending=False
        )
    else:
        # Create empty DataFrame with correct columns
        driver_risk_df = pd.DataFrame(columns=['driver_name', 'risk_score'])

    # High volume drivers - handle empty list
    if high_volume_drivers and len(high_volume_drivers) > 0:
        high_volume_df = pd.DataFrame(
            [
                {
                    'driver_name': p.driver_name,
                    'total_volume': p.total_volume,
                    'volume_z_score': p.volume_z_score,
                    'transaction_count': p.transaction_count,
                }
                for p in high_volume_drivers
            ]
        )
        # Sort by total volume descending (already sorted but being explicit)
        high_volume_df: pd.DataFrame = high_volume_df.sort_values(
            'total_volume', ascending=False
        )
    else:
        # Create empty DataFrame with correct columns
        high_volume_df = pd.DataFrame(
            columns=[
                'driver_name',
                'total_volume',
                'volume_z_score',
                'transaction_count',
            ]
        )

    return {
        'monthly_data': monthly_stats,
        'weekly_data': weekly_stats,
        'risk_indicators': risk_indicators,
        'statistical_tests': viz_tests,
        'product_breakdown': product_breakdown,
        'driver_risk_scores': driver_risk_df,
        'high_volume_drivers': high_volume_df,
    }
