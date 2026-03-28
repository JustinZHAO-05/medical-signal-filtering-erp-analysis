from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "0 数据及例程"
SUB7A_PATH = DATA_DIR / "sub7A.mat"
LOC_PATH = DATA_DIR / "64-channels.loc"

OUTPUT_DIR = ROOT / "output"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"
REPORT_OUTPUT_DIR = OUTPUT_DIR / "report"
REPORT_MAIN_TEX = ROOT / "report" / "main.tex"
REPORT_BODY_TEX = REPORT_OUTPUT_DIR / "body.tex"
REPORT_PDF = REPORT_OUTPUT_DIR / "medical_signal_filter_report.pdf"
SUMMARY_PDF = REPORT_OUTPUT_DIR / "summary.pdf"
SUBMISSION_DIR = OUTPUT_DIR / "submission"

ORIGINAL_FS = 250.0
IIR_ERP_FS = 200.0
FIR_ERP_FS = 1000.0

EPOCH_TMIN = -0.2
EPOCH_TMAX = 0.8
BASELINE = (-0.2, 0.0)
REF_CHANS = ("TP7", "TP8")
FZ_NAME = "FZ"

PLOT_DPI = 170
PLOT_FMT = "pdf"
