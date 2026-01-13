# argus/generate_visualizations.py

import logging
from typing import Any

from argus.models import DriverRiskProfile, StatisticalTest
from argus.utils import AnalysisContext
from argus.visualizations import ForensicVisualizer, prepare_visualization_data

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


def generate_executive_visualizations(
    context: AnalysisContext,
    all_tests: dict[str, StatisticalTest],
    driver_profiles: list[DriverRiskProfile],
    high_volume_drivers: list[DriverRiskProfile],
    save_path: str | None = None,
) -> None:
    """
    Generate and display/save executive visualizations.

    Args:
        full_df: Complete dataset
        target_location: Target location data
        others: Other branches data
        target_name: Name of target location
        analysis_period: Analysis period string
        all_tests: dictionary of statistical test results
        driver_profiles: list of driver risk profiles
        confidence_level: Statistical confidence level
        save_path: Optional path to save the dashboard
        show: Whether to display the dashboard
    """
    logger.debug('GENERATING EXECUTIVE VISUALIZATIONS')

    # Prepare data
    viz_data: dict[str, Any] = prepare_visualization_data(
        context=context,
        all_tests=all_tests,
        driver_profiles=driver_profiles,
        high_volume_drivers=high_volume_drivers,
    )

    # Create visualizer
    visualizer = ForensicVisualizer(context)

    # Generate dashboard
    visualizer.create_executive_dashboard(
        monthly_data=viz_data['monthly_data'],
        weekly_data=viz_data['weekly_data'],
        risk_indicators=viz_data['risk_indicators'],
        statistical_tests=viz_data['statistical_tests'],
        product_breakdown=viz_data['product_breakdown'],
        high_volume_drivers=viz_data['high_volume_drivers'],
    )

    logger.debug('\n✓ Executive dashboard generated successfully')
    if save_path:
        logger.info('  Dashboard saved to: %r', save_path)

    # Display if requested
    if context.config.output.display_report:
        visualizer.show()
    else:
        visualizer.close_all()
