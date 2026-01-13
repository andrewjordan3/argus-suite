# ARGUS (Analytics & Risk Governance Utility Suite)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Comprehensive forensic analysis toolkit for fuel card fraud detection and operational risk assessment**

ARGUS is a Python-based statistical analysis framework designed to identify suspicious patterns, detect fraud, and assess operational risks in fuel card transaction data. It combines rigorous statistical testing, temporal analysis, and risk profiling to provide actionable intelligence for fraud investigation and compliance.

## 🎯 Key Features

### Statistical Analysis
- **Categorical Tests**: Two-proportion z-tests, chi-square tests, Fisher's exact test
- **Risk Metrics**: Risk ratios, odds ratios, confidence intervals
- **Effect Sizes**: Cramér's V, Cliff's Delta
- **Multiple Testing Correction**: Benjamini-Hochberg False Discovery Rate (FDR) control
- **Non-parametric Tests**: Mann-Whitney U, Mann-Kendall trend test

### Risk Identification
- **Driver Risk Profiling**: Z-score-based risk scoring across multiple indicators
- **Vehicle Risk Assessment**: Fleet-wide anomaly detection
- **Focused Analysis**: Deep-dive investigations of high-risk entities
- **Automated Prioritization**: Identifies top suspicious drivers/vehicles automatically

### Pattern Detection
- **Multi-fillup Analysis**: Detects same-day multiple transactions with fraud indicators
- **Passenger Vehicle Fraud**: Identifies gasoline purchases suggesting personal vehicle use
- **Geographic Anomalies**: Station-level pattern analysis
- **Temporal Patterns**: Change point detection and trend analysis

### Temporal Analysis
- **Fraud Emergence Detection**: Identifies when suspicious behavior began
- **Trend Analysis**: Statistical testing of metric trends over time
- **Change Point Detection**: CUSUM-based identification of behavior changes
- **Period Comparison**: Early vs. late period statistical comparison

### Professional Reporting
- **Executive Summaries**: Clear, non-technical findings for decision-makers
- **Statistical Details**: Full methodology and test results
- **Visualizations**: Publication-ready charts and dashboards
- **Formatted Output**: Professional text reports with structured sections

## 📋 Requirements

- Python 3.9 or higher
- pandas >= 2.0.0
- numpy >= 1.24.0
- scipy >= 1.10.0
- matplotlib >= 3.7.0 (for visualizations)

## 🚀 Installation

### Basic Installation
```bash
pip install -e .
```

### Development Installation
```bash
pip install -e ".[dev]"
```

## 📖 Quick Start

### Basic Usage
```python
import pandas as pd
from ARGUS.pipeline import ForensicAnalysisPipeline, create_default_config

# Load your data
df = pd.read_csv('fuel_card_data.csv')

# Create configuration
config = create_default_config(
    target_location_number=42,
    target_location_name='Chicago Branch'
)

# Run analysis
pipeline = ForensicAnalysisPipeline(config)
results = pipeline.run(df)
```

### Custom Configuration
```python
config = create_default_config(
    target_location_number=42,
    target_location_name='Chicago Branch',
    confidence_level=0.99,  # More stringent statistical threshold
    top_n_entities=15,      # Show top 15 instead of 10
    generate_visualizations=True,
    save_report=True,
    output_directory='./forensic_reports'
)

pipeline = ForensicAnalysisPipeline(config)
results = pipeline.run(df)
```

### Analyzing Specific Drivers
```python
# Investigate specific drivers by name
results = pipeline.run(
    df,
    highlight_drivers=['John Doe', 'Jane Smith']
)
```

## 📊 Expected Data Format

Your input DataFrame should contain the following columns:

### Required Columns
- `datetime`: Timestamp of fuel transaction
- `LocationIndex`: Branch/location identifier (integer)
- `Driver`: Driver name
- `VIN`: Vehicle identification number
- `VINIndex`: Vehicle identifier (integer)
- `cost`: Transaction amount
- `volume`: Fuel volume purchased
- `product_description`: Product type (e.g., "Diesel", "Gasoline")
- `Station Name`: Name of fuel station
- `Date`: Date field for ELD data
- `Distance`: Distance traveled (from ELD)

### Example Data Structure
```csv
datetime,LocationIndex,Driver,VIN,VINIndex,cost,volume,product_description,Station Name,Date,Distance
2024-01-15 08:30:00,42,John Doe,1HGCM82633A123456,1001,125.50,35.2,Diesel,Shell Station,2024-01-15,245.3
```

## 🔧 Configuration Options

### Analysis Parameters
- `target_location_number`: Branch ID to investigate (required)
- `target_location_name`: Branch name (required)
- `confidence_level`: Statistical confidence (default: 0.95)
- `n_bootstrap`: Bootstrap iterations (default: 10000)
- `min_transactions_risk`: Minimum transactions for risk analysis (default: 10)
- `min_transactions_temporal`: Minimum for temporal analysis (default: 20)
- `top_n_entities`: Number of top entities to display (default: 10)
- `auto_analyze_top_drivers`: Auto-analyze top N drivers (default: 3)

### Output Options
- `generate_visualizations`: Create charts (default: True)
- `save_report`: Save text report (default: True)
- `save_visualizations`: Save charts to file (default: True)
- `output_directory`: Directory for outputs (default: './output')
- `output_width`: Report width in characters (default: 100)

## 📈 Output

The pipeline generates:

1. **Text Report** (`forensic_report_[location]_[timestamp].txt`)
   - Executive summary of findings
   - Statistical test results with FDR correction
   - Risk profiles for drivers and vehicles
   - Suspicious pattern analysis
   - Temporal trend analysis
   - Data quality assessment

2. **Visualizations** (`forensic_dashboard_[location]_[timestamp].png`)
   - Key risk indicators comparison
   - Statistical significance panel
   - Monthly trend analysis
   - Product breakdown
   - Monthly spend analysis
   - Top high-risk drivers

## 🧪 Statistical Methodology

ARGUS employs rigorous statistical methods to ensure defensible conclusions:

### Hypothesis Testing
- All tests use appropriate statistical methods (parametric/non-parametric)
- Multiple testing correction via Benjamini-Hochberg FDR
- Confidence intervals provided for all effect sizes
- Both raw p-values and FDR-adjusted q-values reported

### Effect Sizes
- **Risk Ratio**: Relative risk between target and baseline
- **Odds Ratio**: Strength of association
- **Cramér's V**: Chi-square effect size
- **Cliff's Delta**: Non-parametric effect size for continuous data

### Temporal Analysis
- **Mann-Kendall**: Monotonic trend detection
- **CUSUM**: Change point detection
- **Segment Comparison**: Statistical comparison of time periods

## 📂 Project Structure
```
ARGUS
 ┣ schemas
 ┃ ┣ schemas.py
 ┃ ┗ __init__.py
 ┣ templates
 ┃ ┗ report_config.yaml
 ┣ utils
 ┃ ┣ config_loader.py
 ┃ ┣ format_tools.py
 ┃ ┣ old_config_loader.py
 ┃ ┣ report_formatter.py
 ┃ ┣ safe_template.py
 ┃ ┣ stat_tools.py
 ┃ ┣ tail_test.py
 ┃ ┣ temporal_tools.py
 ┃ ┗ __init__.py
 ┣ categoricals.py
 ┣ generate_visualizations.py
 ┣ old_output_formatter.py
 ┣ output_formatter.py
 ┣ pipeline.py
 ┣ preprocessor.py
 ┣ report_summary.py
 ┣ risk_analysis.py
 ┣ suspicious_patterns.py
 ┣ temporal.py
 ┣ visualizations.py
 ┗ __init__.py
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and type checking
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ✉️ Contact

Andrew Jordan - andrewjordan3@gmail.com

## 🙏 Acknowledgments

- Statistical methods based on established practices in forensic accounting
- Temporal analysis inspired by quality control and process monitoring literature
- Pattern detection techniques adapted from fraud investigation frameworks

## 🗺️ Roadmap

### Version 0.2.0 (Planned)
- [ ] Command-line interface (CLI)
- [ ] Excel export functionality
- [ ] PDF report generation
- [ ] Configuration file support (YAML/JSON)

### Version 0.3.0 (Planned)
- [ ] Unit test suite
- [ ] Performance optimization with numba
- [ ] Interactive HTML reports
- [ ] Additional fraud patterns

### Version 1.0.0 (Future)
- [ ] Web-based dashboard
- [ ] Real-time analysis mode
- [ ] Machine learning integration
- [ ] Multi-location batch analysis

## ⚠️ Disclaimer

This software is provided "as is" for investigative and analytical purposes. Statistical significance does not necessarily imply fraud or wrongdoing. All findings should be investigated with appropriate context and in consultation with relevant stakeholders before drawing final conclusions or taking action.

---

**ARGUS** - *Bringing clarity to complex operational data*
