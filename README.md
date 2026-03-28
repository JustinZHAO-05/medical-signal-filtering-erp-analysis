# Medical Signal Filtering for ERP Analysis

This repository presents a complete signal-processing project on **IIR/FIR filter design and ERP analysis** using real EEG data. It was developed as a course laboratory project and is organized as a reproducible Python workflow with final reports in both Chinese and English.

The project is intended to showcase practical work in:

- digital filter design and comparison
- EEG/ERP preprocessing
- time-domain and frequency-domain interpretation
- reproducible computational reporting

**Author:** Yanzhe Zhao  
**Institution:** School of Future Technology, Tianjin University

## Project Highlights

- Designed and compared four classic IIR low-pass families: Butterworth, Chebyshev-I, Chebyshev-II, and Elliptic.
- Compared causal filtering, repeated causal filtering, and zero-phase filtering to show how latency interpretation can change.
- Analyzed baseline drift suppression and the risks of overly aggressive high-pass filtering for ERP studies.
- Designed FIR filters with three methods: window design, frequency sampling, and equiripple approximation.
- Compared FIR and IIR band-pass filtering on real ERP data, including delay compensation and its impact on waveform interpretation.
- Produced polished Chinese and English PDF reports plus one-page summaries for presentation purposes.

## Visual Preview

### Clinical Summary Figure

![Clinical summary](https://raw.githubusercontent.com/JustinZHAO-05/medical-signal-filtering-erp-analysis/main/assets/clinical-summary.png)

### FIR vs IIR ERP Comparison

![ERP comparison](https://raw.githubusercontent.com/JustinZHAO-05/medical-signal-filtering-erp-analysis/main/assets/erp-comparison.png)

## Reports

- Chinese full report: [`output/report/medical_signal_filter_report.pdf`](output/report/medical_signal_filter_report.pdf)
- Chinese one-page summary: [`output/report/summary.pdf`](output/report/summary.pdf)
- English full report: [`output_en/report/medical_signal_filter_report_en.pdf`](output_en/report/medical_signal_filter_report_en.pdf)
- English summary: [`output_en/report/summary_en.pdf`](output_en/report/summary_en.pdf)

## Repository Structure

```text
.
├── 0 数据及例程/               # Original EEG data, channel locations, and reference example
├── medsiglab/                 # Core data I/O, filtering, ERP, plotting, and reporting utilities
├── scripts/                   # Entry points and experiment/report pipelines
├── report/                    # Chinese LaTeX template
├── report_en/                 # English LaTeX templates
├── output/                    # Chinese figures, tables, and final PDFs
├── output_en/                 # English tables and final PDFs
├── assets/                    # README preview images
├── 1 实验任务书.pdf            # Original assignment brief
├── 2 脑电数据介绍及例程.pdf    # EEG data description and reference workflow
└── requirements.txt           # Python dependencies
```

## Reproducibility

### Environment

```bash
pip install -r requirements.txt
```

### Run the full Chinese workflow

```bash
python3 scripts/run_all.py
```

### Rebuild the Chinese report only

```bash
python3 scripts/build_report.py
```

### Rebuild the English report only

```bash
python3 scripts/build_report_en.py
```

## Key Technical Content

### Part I: IIR Filter Design

1. Low-pass family comparison under matched amplitude specifications
2. Causal vs repeated-causal vs zero-phase processing
3. High-pass filtering for slow-drift suppression
4. ERP distortion caused by cutoff choice and high-pass order

### Part II: FIR Filter Design

1. FIR design method comparison
2. Window-function and filter-length comparison
3. FIR vs IIR band-pass filtering on ERP waveforms

## Why This Project Matters

This project is not only about designing filters that satisfy frequency-domain specifications. It also demonstrates a key methodological point in biomedical signal processing:

> the choice of filter can directly change waveform amplitude, latency, slow-wave morphology, and therefore the interpretation of clinically meaningful events.

For ERP analysis, this means that filter selection is part of the scientific result, not just a preprocessing detail.

## Notes

- The repository includes the original course documents and data used in the project.
- Final reports are kept in the repository for direct viewing and evaluation.
- Intermediate caches, temporary screenshots, and compiler residue are intentionally excluded from version control.
