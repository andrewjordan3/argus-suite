# ARGUS Suite (Analytics & Risk Governance Utility Suite)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Comprehensive forensic analysis toolkit for fuel card fraud detection and operational risk assessment**

ARGUS Suite is a production-grade Python framework for statistical fraud detection and risk assessment in fuel card transaction data. Built with a sophisticated configuration system, Pydantic-validated data models, and rigorous statistical methodology, it provides enterprise-level forensic analysis capabilities with full internationalization support.

## 🎯 Key Features

### Advanced Configuration System
- **YAML-Based Configuration**: Flexible three-tier system (config/policy/locale)
- **Pydantic Validation**: Type-safe configuration with comprehensive validation
- **Column Mapping**: Flexible field mapping to adapt to any data schema
- **Internationalization**: Full locale support for multi-language reporting
- **Policy Management**: Configurable thresholds, weights, and business rules

### Data Preprocessing Pipeline
- **8-Stage Processing**: Cleaning → Feature Engineering → ELD Processing → Quality Assessment
- **Automatic Schema Validation**: Ensures data integrity before analysis
- **Deduplication**: Intelligent duplicate detection and removal
- **Feature Engineering**: 30+ derived features (MPG, business hours, rush hour, cost per gallon, etc.)
- **Quality Metrics**: Comprehensive data quality assessment and reporting
- **ELD Integration**: Advanced electronic logging device data processing

### Statistical Analysis
- **Categorical Tests**: Two-proportion z-tests, chi-square tests, Fisher's exact test
- **Risk Metrics**: Risk ratios with Wilson confidence intervals, odds ratios
- **Effect Sizes**: Cramér's V, Cliff's Delta, Cohen's d
- **Multiple Testing Correction**: Benjamini-Hochberg False Discovery Rate (FDR) control
- **Non-parametric Tests**: Mann-Whitney U, Mann-Kendall trend test, Hodges-Lehmann estimator
- **Bootstrap Methods**: Percentile-based confidence intervals

### Risk Identification
- **Driver Risk Profiling**: Multi-dimensional z-score-based risk scoring
- **Vehicle Risk Assessment**: Fleet-wide anomaly detection with MPG analysis
- **Composite Risk Scoring**: Weighted combination of 10+ risk indicators
- **Focused Analysis**: Deep-dive investigations of high-risk entities
- **Automated Prioritization**: Identifies top suspicious drivers/vehicles automatically
- **Temporal Risk Profiles**: 8-component time-series risk assessment

### Pattern Detection
- **Multi-fillup Analysis**: Same-day multiple transactions with 7-flag scoring system:
  - LC: Low Cost transactions
  - LV: Low Volume purchases
  - ND: Non-Diesel fuel (for diesel vehicles)
  - MF: Multiple Fillups indicator
  - MS: Multiple Stations usage
  - NE: No ELD Match
  - RS: Rapid Succession purchases
- **Passenger Vehicle Fraud**: Identifies gasoline purchases suggesting personal vehicle use
- **Geographic Anomalies**: Station-level pattern analysis with configurable thresholds
- **Off-Hours Concentration**: Business hours vs. off-hours transaction analysis
- **Spike-and-Retreat Detection**: Identifies suspicious temporal patterns

### Temporal Analysis
- **Fraud Emergence Detection**: Identifies when suspicious behavior began
- **Trend Analysis**: Mann-Kendall statistical testing of metric trends over time
- **Change Point Detection**: CUSUM and Bayesian methods for behavior change identification
- **Multiple Changepoint Detection**: Identifies complex temporal patterns
- **Period Comparison**: Statistical comparison of time periods (early vs. late)
- **Rolling Window Anomalies**: Moving average-based anomaly detection
- **Autocorrelation Analysis**: Detects systematic temporal dependencies
- **Fraud Pattern Recognition**: 4 distinct temporal fraud signatures

### Professional Reporting
- **Template-Driven Reports**: SafeTemplate system with placeholder validation
- **Executive Summaries**: Clear, non-technical findings for decision-makers
- **Statistical Details**: Full methodology and test results with FDR correction
- **Visualizations**: Publication-ready charts and executive dashboards
- **Formatted Output**: Professional text reports with structured sections
- **Multi-Language Support**: Full internationalization via locale system

## 📋 Requirements

- Python 3.12 or higher
- pandas >= 2.3.0
- numpy >= 2.3.0
- scipy >= 1.16.0
- matplotlib >= 3.10.0
- pydantic >= 2.11.0
- pyyaml >= 6.0.0
- ruptures >= 1.1.10 (change point detection)
- statsmodels >= 0.14 (statistical methods)

## 🚀 Installation

### Basic Installation
```bash
pip install -e .
```

### Development Installation
```bash
pip install -e ".[dev]"
```

This includes:
- **ruff**: Linting and code formatting
- **mypy**: Type checking with stubs for pandas, scipy
- **pytest**: Testing framework with coverage

## 📖 Quick Start

### Basic Usage with Default Configuration

```python
import pandas as pd
from argus.pipeline import ForensicAnalysisPipeline
from argus.config import load_config

# Load your data
df = pd.read_csv('fuel_card_data.csv')

# Load configuration (uses examples/config.yaml by default)
config = load_config('path/to/config.yaml')

# Run analysis
pipeline = ForensicAnalysisPipeline(config)
results = pipeline.run(df)
```

### Using Example Configuration

```python
from argus.pipeline import ForensicAnalysisPipeline

# Uses default configuration
pipeline = ForensicAnalysisPipeline()
results = pipeline.run(df, highlight_drivers=['John Doe', 'Jane Smith'])
```

### Custom Configuration Files

ARGUS Suite uses three YAML configuration files:

1. **config.yaml** - Main analysis configuration
2. **policy.yaml** - Business rules and thresholds
3. **english.yaml** - Locale settings (or other language)

See the `examples/` directory for complete templates.

## ⚙️ Configuration System

### 1. Main Configuration (config.yaml)

```yaml
# Data Sources
data_sources:
  fuel_transactions: "data/fuel_cards.csv"
  eld_telemetry: "data/eld_data.csv"

# Column Mapping - Map YOUR columns to ARGUS fields
column_mapping:
  # Core Transaction Fields (REQUIRED)
  vehicle_id: "vin"
  transaction_timestamp: "datetime"
  driver_name: "driver"
  merchant_name: "station_name"
  transaction_amount: "cost"
  fuel_volume_gallons: "volume"
  product_category: "fuel_type"

  # Entity Identifiers (REQUIRED)
  vehicle_index: "vinindex"
  driver_index: "driverindex"
  location_index: "locationindex"

  # ELD Fields (for MPG calculation)
  distance_miles: "distance"
  idle_duration_minutes: "idle_time"
  driving_duration_minutes: "driving_time"

# Analysis Target
analysis_target:
  location_number: 42
  location_name: "Chicago Branch"

# Output Settings
output:
  directory: "./forensic_reports"
  generate_visualizations: true
  save_report: true
  report_width: 100

# Logging
logging:
  level: "INFO"
  file: "argus.log"

# Performance
performance:
  n_bootstrap: 10000
  confidence_level: 0.95
  parallel_processing: true
```

### 2. Policy Configuration (policy.yaml)

```yaml
# Business Hours
business_hours:
  start_time: "06:00"
  end_time: "18:00"

# Statistical Settings
statistical_settings:
  significance_level: 0.05
  fdr_method: "benjamini_hochberg"
  confidence_level: 0.95
  min_sample_size: 30

# Risk Thresholds
risk_thresholds:
  critical: 3.0    # 3+ standard deviations
  high: 2.0
  medium: 1.0
  low: 0.5

# Data Requirements
data_requirements:
  min_transactions_risk: 10
  min_transactions_temporal: 20
  min_months: 3

# Risk Score Weights (must sum to 1.0)
risk_weights:
  volume_anomaly: 0.15
  cost_anomaly: 0.15
  frequency_anomaly: 0.10
  off_hours_rate: 0.10
  multi_fillup_rate: 0.15
  passenger_vehicle_rate: 0.10
  no_eld_match_rate: 0.10
  geographic_spread: 0.08
  rapid_succession_rate: 0.07

# Red Flag Weights (multi-fillup scoring)
red_flag_weights:
  low_cost: 1.0
  low_volume: 1.0
  non_diesel: 2.0
  multiple_fillups: 1.5
  multiple_stations: 2.0
  no_eld_match: 2.0
  rapid_succession: 2.5

# Effect Size Thresholds
effect_size:
  cramers_v:
    small: 0.1
    medium: 0.3
    large: 0.5
  cliffs_delta:
    small: 0.147
    medium: 0.330
    large: 0.474
```

### 3. Locale Configuration (english.yaml)

```yaml
# Number/Date Formatting
number_format:
  decimal_separator: "."
  thousands_separator: ","
  currency_symbol: "$"
  date_format: "%Y-%m-%d"

# Report Sections
header:
  title: "FUEL CARD FORENSIC ANALYSIS REPORT"
  subtitle: "Statistical Analysis and Risk Assessment"

methodology:
  title: "STATISTICAL METHODOLOGY"
  description: |
    This analysis employs rigorous statistical methods including...

# Risk Categories
risk_categories:
  critical: "CRITICAL RISK"
  high: "HIGH RISK"
  medium: "MEDIUM RISK"
  low: "LOW RISK"

# ... (1,300+ lines of text templates)
```

## 📊 Expected Data Format

Your input CSV files will be automatically mapped using the `column_mapping` section in your config.yaml. ARGUS is flexible and can adapt to your schema.

### Fuel Transaction Data

**Your columns can be named anything** - just map them in config.yaml:

```csv
datetime,vin,driver,station_name,cost,volume,fuel_type,branch,vinindex,driverindex,locationindex
2024-01-15 08:30:00,1HGCM82633A123456,John Doe,Shell Station,125.50,35.2,Diesel,Chicago,1001,5001,42
```

### ELD Telemetry Data (Optional but Recommended)

```csv
date,vin,distance,idle_time,driving_time,running_time
2024-01-15,1HGCM82633A123456,245.3,45,420,465
```

### Required Fields

After mapping, ARGUS needs these logical fields:

**Core Transaction Fields:**
- Transaction timestamp
- Vehicle ID
- Driver name
- Transaction amount
- Fuel volume
- Product type/category
- Location identifier

**Entity Identifiers:**
- Vehicle index (integer ID)
- Driver index (integer ID)
- Location index (integer ID)

**ELD Fields (for MPG calculation):**
- Distance traveled
- Idle duration
- Driving duration

## 📂 Project Structure

```
argus-suite/
 ┣ src/argus/
 ┃ ┣ models/                      [Data Models - 50+ Pydantic models]
 ┃ ┃ ┣ analysis/                 [Statistical test & risk models]
 ┃ ┃ ┃ ┣ driver_risk.py          [DriverRiskProfile]
 ┃ ┃ ┃ ┣ vehicle_risk.py         [VehicleRiskProfile]
 ┃ ┃ ┃ ┣ temporal_risk.py        [TemporalRiskProfile]
 ┃ ┃ ┃ ┣ statistical_test.py     [StatisticalTest]
 ┃ ┃ ┃ ┗ volume_stats.py         [VolumeStatistics]
 ┃ ┃ ┣ common/                   [Base models & validation]
 ┃ ┃ ┃ ┣ base.py                 [ArgusBaseModel]
 ┃ ┃ ┃ ┣ placeholders.py         [Template placeholders]
 ┃ ┃ ┃ ┗ placeholder_validation.py
 ┃ ┃ ┣ config/                   [Configuration models]
 ┃ ┃ ┃ ┣ root.py                 [FuelCardForensicsConfig]
 ┃ ┃ ┃ ┣ analysis_target.py      [AnalysisTarget]
 ┃ ┃ ┃ ┣ column_mapping.py       [ColumnMapping]
 ┃ ┃ ┃ ┣ data_sources.py         [DataSources]
 ┃ ┃ ┃ ┣ output.py               [OutputConfig]
 ┃ ┃ ┃ ┣ logging.py              [LoggingConfig]
 ┃ ┃ ┃ ┗ performance.py          [PerformanceConfig]
 ┃ ┃ ┣ context/                  [Analysis context]
 ┃ ┃ ┃ ┗ context_model.py        [AnalysisContext]
 ┃ ┃ ┣ locale/                   [17+ locale models]
 ┃ ┃ ┃ ┣ root_config.py          [LocaleConfig]
 ┃ ┃ ┃ ┣ executive_summary.py
 ┃ ┃ ┃ ┣ driver_analysis.py
 ┃ ┃ ┃ ┣ vehicle_analysis.py
 ┃ ┃ ┃ ┣ temporal.py
 ┃ ┃ ┃ ┗ ... [13 more]
 ┃ ┃ ┗ policy/                   [Policy/threshold models]
 ┃ ┃   ┣ root.py                 [PolicyConfig]
 ┃ ┃   ┣ statistical_settings.py
 ┃ ┃   ┣ risk_weights.py
 ┃ ┃   ┣ red_flag_weights.py
 ┃ ┃   ┗ ... [8 more]
 ┃ ┣ preprocessing/               [8-Stage Preprocessing Pipeline]
 ┃ ┃ ┣ pipeline.py               [PreprocessingPipeline]
 ┃ ┃ ┣ cleaning.py               [Data cleaning & validation]
 ┃ ┃ ┣ feature_engineering.py    [30+ derived features]
 ┃ ┃ ┣ eld_processing.py         [ELD integration]
 ┃ ┃ ┣ quality_assessment.py     [Quality metrics]
 ┃ ┃ ┗ data_splitter.py          [Target/peer splitting]
 ┃ ┣ formatting/                  [Report Formatting]
 ┃ ┃ ┣ report_formatter.py       [ReportFormatter]
 ┃ ┃ ┣ report_sections.py        [Section builders]
 ┃ ┃ ┣ safe_template.py          [SafeTemplate system]
 ┃ ┃ ┣ format_tools.py           [Formatting utilities]
 ┃ ┃ ┗ effect_size_mapping.py    [Effect size interpretation]
 ┃ ┣ config/                      [Configuration Loading]
 ┃ ┃ ┗ config_loader.py          [load_config()]
 ┃ ┣ locales/                     [Locale Files]
 ┃ ┃ ┗ english.yaml              [1,314 lines - English text]
 ┃ ┣ defaults/                    [Default Configurations]
 ┃ ┃ ┣ config.yaml               [318 lines - Default config]
 ┃ ┃ ┗ policy.yaml               [523 lines - Default policy]
 ┃ ┣ utils/                       [Utility Functions]
 ┃ ┃ ┣ stat_tools.py             [38KB - Statistical functions]
 ┃ ┃ ┣ temporal_tools.py         [31KB - Temporal analysis]
 ┃ ┃ ┣ risk_scoring.py           [22KB - Risk calculations]
 ┃ ┃ ┣ tail_test.py              [30KB - Distribution testing]
 ┃ ┃ ┗ ... [9 more utilities]
 ┃ ┣ categoricals.py              [Statistical Tests]
 ┃ ┣ pipeline.py                  [ForensicAnalysisPipeline]
 ┃ ┣ risk_analysis.py             [Risk Profiling]
 ┃ ┣ suspicious_patterns.py       [Pattern Detection]
 ┃ ┣ temporal.py                  [Temporal Analysis]
 ┃ ┣ visualizations.py            [Visualization Engine]
 ┃ ┣ output_formatter.py          [ForensicReportWriter]
 ┃ ┗ __init__.py
 ┣ examples/                       [Example Configurations]
 ┃ ┣ config.yaml                  [13KB - Complete example]
 ┃ ┣ policy.yaml                  [22KB - Policy example]
 ┃ ┗ english.yaml                 [58KB - Locale example]
 ┣ pyproject.toml                  [Project metadata & dependencies]
 ┣ README.md
 ┗ LICENSE
```

**Total:** 90+ Python files, sophisticated architecture

## 🧪 Statistical Methodology

ARGUS Suite employs rigorous statistical methods to ensure defensible conclusions:

### Hypothesis Testing
- All tests use appropriate methods (parametric when assumptions met, non-parametric otherwise)
- Multiple testing correction via Benjamini-Hochberg FDR control
- Confidence intervals provided for all effect sizes using Wilson, bootstrap, or analytical methods
- Both raw p-values and FDR-adjusted q-values reported

### Effect Sizes
- **Risk Ratio**: Relative risk between target and baseline with Wilson confidence intervals
- **Odds Ratio**: Strength of association with CIs
- **Cramér's V**: Chi-square effect size (0.1/0.3/0.5 thresholds)
- **Cliff's Delta**: Non-parametric effect size for continuous data (0.147/0.330/0.474 thresholds)
- **Cohen's d**: Parametric effect size when appropriate

### Temporal Analysis Methods
- **Mann-Kendall**: Monotonic trend detection (non-parametric)
- **CUSUM**: Cumulative sum control charts for change point detection
- **Bayesian Changepoint**: Probabilistic change detection using ruptures library
- **Segment Comparison**: Statistical comparison of time periods with Mann-Whitney U
- **Rolling Window**: Moving average-based anomaly detection
- **Autocorrelation**: Systematic temporal pattern identification

### Risk Scoring
- **Z-score Normalization**: Standardized scores across metrics
- **Composite Weighting**: Configurable weights for 10 risk components
- **Percentile-Based**: Risk categories based on distribution percentiles
- **Wilson Confidence Intervals**: Conservative rate estimation for low-count scenarios

## 📈 Output

The pipeline generates comprehensive forensic reports:

### 1. Text Report (`forensic_report_[location]_[timestamp].txt`)

**Sections:**
- **Header**: Report metadata, analysis period, location information
- **Methodology**: Statistical methods and validation approach
- **Data Preparation**: Preprocessing steps, cleaning actions, feature engineering
- **Data Quality Assessment**: Completeness, integrity, outlier analysis
- **Analysis Scope**: Target vs. baseline comparison, sample sizes, time periods
- **Statistical Findings**: Hypothesis tests with FDR correction, effect sizes, confidence intervals
- **Driver Risk Analysis**:
  - Aggregate comparison (target vs. peers)
  - Top N high-risk driver profiles
  - Individual focused analyses
  - Multi-fillup patterns per driver
- **Vehicle Risk Analysis**: Fleet-wide patterns, MPG analysis, top risky vehicles
- **Multi-Fillup Patterns**: Same-day multiple transactions with 7-flag scoring
- **Geographic Analysis**: Station-level anomalies and patterns
- **Temporal Analysis**:
  - Trend tests (Mann-Kendall)
  - Change point detection
  - Fraud pattern recognition
  - Period comparisons
  - Entity-level temporal profiles
- **Executive Summary**:
  - Key findings (top 5-10)
  - Risk assessment
  - Recommended actions
  - Statistical summary
- **Footer**: Disclaimer, report generation info

### 2. Visualizations (`forensic_dashboard_[location]_[timestamp].png`)

**8-Panel Executive Dashboard:**
- **Key Risk Indicators**: Target vs. Baseline comparison (bar chart)
- **Statistical Significance**: P-values and effect sizes (table)
- **Monthly Trends**: Time series of key metrics
- **Product Breakdown**: Diesel vs. Gasoline usage (pie charts)
- **Monthly Spend Analysis**: Cost trends over time
- **Top High-Risk Drivers**: Risk score ranking (horizontal bar)
- **Geographic Patterns**: Station usage distribution
- **Temporal Patterns**: Change points and anomalies

## 🧩 Advanced Features

### Preprocessing Pipeline

The 8-stage preprocessing pipeline transforms raw data into analysis-ready format:

1. **Data Cleaning**
   - Schema validation
   - Duplicate detection and removal
   - Incomplete month filtering
   - Constraint enforcement

2. **Temporal Feature Engineering**
   - Date/time component extraction (year, month, day, hour, weekday)
   - Business hours flags
   - Rush hour indicators
   - Time period categorization

3. **Transaction Feature Engineering**
   - Product standardization (diesel vs. gasoline)
   - Cost per gallon calculation
   - Transaction size categories
   - Multi-fillup detection
   - Same-day transaction grouping

4. **Vehicle Feature Engineering**
   - MPG calculation (miles per gallon)
   - Idle percentage
   - Driving percentage
   - ELD match validation

5. **ELD Processing**
   - Aggregation type detection
   - Activity flag creation
   - Duplicate distance handling
   - Temporal alignment with transactions

6. **Quality Assessment**
   - Completeness evaluation
   - Outlier detection
   - Integrity validation
   - Quality scoring

7. **Data Splitting**
   - Target location isolation
   - Peer group creation
   - Temporal period splitting
   - Metadata generation

8. **Documentation**
   - Preparation report generation
   - Quality metrics logging
   - Decision documentation

### SafeTemplate System

The SafeTemplate system ensures robust report generation:

- **Placeholder Validation**: Verifies all template variables are provided
- **Missing Detection**: Identifies unused or missing placeholders
- **Type Safety**: Pydantic-based validation of template data
- **Error Messages**: Detailed debugging information
- **Multi-Level Context**: Merges runtime, policy, and locale data

### Multi-Fillup Fraud Detection

Sophisticated same-day multiple transaction analysis:

**7 Red Flags:**
1. **LC (Low Cost)**: Transaction below threshold (policy-configured)
2. **LV (Low Volume)**: Volume below threshold
3. **ND (Non-Diesel)**: Gasoline on diesel vehicle
4. **MF (Multiple Fillups)**: >1 same-day transaction
5. **MS (Multiple Stations)**: Different stations same day
6. **NE (No ELD Match)**: Missing ELD data for date
7. **RS (Rapid Succession)**: Transactions within time window

**Scoring:**
- Each flag has configurable weight
- Composite suspicion score calculated
- Threshold-based categorization
- Driver-level and day-level aggregation

### Temporal Fraud Patterns

Four distinct patterns automatically detected:

1. **Off-Hours Concentration**: High rate of non-business-hour transactions
2. **Spike-and-Retreat**: Sudden metric increase followed by return to baseline
3. **Gradual Escalation**: Monotonic increasing trend in suspicious metrics
4. **Operational Anomalies**: Deviation from normal operational patterns

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run type checking with mypy and linting with ruff
4. Write tests for new functionality (when test suite is implemented)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone https://github.com/andrewjordan3/argus-suite.git
cd argus-suite

# Install with development dependencies
pip install -e ".[dev]"

# Run type checking
mypy src/argus

# Run linting
ruff check src/argus

# Format code
ruff format src/argus
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ✉️ Contact

Andrew Jordan - andrewjordan3@gmail.com

Project Link: [https://github.com/andrewjordan3/argus-suite](https://github.com/andrewjordan3/argus-suite)

## 🙏 Acknowledgments

- Statistical methods based on established practices in forensic accounting and auditing
- Temporal analysis inspired by statistical process control and quality monitoring literature
- Pattern detection techniques adapted from fraud investigation frameworks
- Change point detection implemented using the ruptures library
- Risk scoring methodology informed by actuarial science and operational risk management

## 🗺️ Roadmap

### Version 0.2.0 (In Progress)
- [x] YAML-based configuration system - **COMPLETED**
- [x] Pydantic data models - **COMPLETED**
- [x] Column mapping system - **COMPLETED**
- [x] Preprocessing pipeline - **COMPLETED**
- [x] SafeTemplate system - **COMPLETED**
- [ ] Command-line interface (CLI)
- [ ] Excel export functionality
- [ ] PDF report generation

### Version 0.3.0 (Planned)
- [ ] Comprehensive unit test suite
- [ ] Integration test framework
- [ ] Performance optimization with numba/Cython
- [ ] Interactive HTML reports
- [ ] Additional fraud patterns (velocity checks, geographic outliers)
- [ ] API documentation (Sphinx)

### Version 1.0.0 (Future)
- [ ] Web-based dashboard (FastAPI + React)
- [ ] Real-time streaming analysis mode
- [ ] Machine learning integration (anomaly detection models)
- [ ] Multi-location batch analysis
- [ ] Database integration (PostgreSQL, SQLite)
- [ ] REST API for programmatic access
- [ ] Docker containerization
- [ ] Cloud deployment templates (AWS, Azure, GCP)

## ⚠️ Disclaimer

This software is provided "as is" for investigative and analytical purposes only. Statistical significance does not necessarily imply fraud, wrongdoing, or policy violations. All findings should be:

- Investigated with appropriate operational context
- Reviewed by qualified personnel (fleet managers, auditors, legal counsel)
- Validated against business policies and procedures
- Used in conjunction with other investigation methods

Before taking any adverse action based on ARGUS findings, consult with relevant stakeholders and follow your organization's investigation and disciplinary procedures.

---

**ARGUS Suite** - *Bringing statistical rigor to operational risk analysis*
