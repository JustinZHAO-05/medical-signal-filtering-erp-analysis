from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from medsiglab import config
OUTPUT_EN = ROOT / "output_en"
TABLES_EN = OUTPUT_EN / "tables"
REPORT_EN = OUTPUT_EN / "report"
BODY_EN = REPORT_EN / "body.tex"
SUMMARY_BODY_EN = REPORT_EN / "summary_body.tex"
PDF_EN = REPORT_EN / "medical_signal_filter_report_en.pdf"
SUMMARY_EN = REPORT_EN / "summary_en.pdf"
MAIN_TEX_EN = ROOT / "report_en" / "main.tex"
SUMMARY_TEX_EN = ROOT / "report_en" / "summary.tex"
SOURCE_METRICS = config.REPORT_OUTPUT_DIR / "metrics.json"


def paragraph(text: str) -> str:
    return text.strip() + "\n\n"


def qa_block(title: str, items: list[tuple[str, str]]) -> str:
    lines = [rf"\subsubsection*{{{title}}}", r"\begin{enumerate}[leftmargin=2em]"]
    for question, answer in items:
        lines.append(rf"\item \textbf{{{question}}}\par \hspace*{{2em}} {answer}")
    lines.append(r"\end{enumerate}")
    return "\n".join(lines) + "\n"


def figure_block(caption: str, path: str, width: str = "0.95\\linewidth", numbered: bool = True) -> str:
    caption_cmd = r"\caption" if numbered else r"\caption*"
    return (
        r"\begin{figure}[H]" "\n"
        r"\centering" "\n"
        rf"\includegraphics[width={width}]{{{path}}}" "\n"
        rf"{caption_cmd}{{{caption}}}" "\n"
        r"\end{figure}" "\n"
    )


def save_table(df: pd.DataFrame, stem: str, index: bool = False) -> str:
    TABLES_EN.mkdir(parents=True, exist_ok=True)
    csv_path = TABLES_EN / f"{stem}.csv"
    tex_path = TABLES_EN / f"{stem}.tex"
    df.to_csv(csv_path, index=index, encoding="utf-8-sig")
    latex = df.to_latex(index=index, escape=False, float_format=lambda x: f"{x:.3f}")
    latex = (
        r"\begingroup" "\n"
        r"\centering" "\n"
        r"\small" "\n"
        r"\renewcommand{\arraystretch}{1.08}" "\n"
        r"\setlength{\tabcolsep}{3pt}" "\n"
        r"\resizebox{\linewidth}{!}{%" "\n"
        f"{latex}"
        r"}" "\n"
        r"\endgroup" "\n"
    )
    tex_path.write_text(latex, encoding="utf-8")
    return f"output_en/tables/{stem}.tex"


def _pdf_page_count(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"Unable to determine page count for {path}")


def extract_pdf_page(input_pdf: Path, page_number: int, output_pdf: Path) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temp_pattern = output_pdf.with_name(f"{output_pdf.stem}-%d.pdf")
    subprocess.run(
        ["pdfseparate", "-f", str(page_number), "-l", str(page_number), str(input_pdf), str(temp_pattern)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    separated_pdf = output_pdf.with_name(f"{output_pdf.stem}-{page_number}.pdf")
    shutil.move(str(separated_pdf), str(output_pdf))


def compile_report() -> Path:
    REPORT_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-jobname=main_en",
        f"-output-directory={REPORT_EN}",
        str(MAIN_TEX_EN),
    ]
    for _ in range(2):
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    generated_pdf = REPORT_EN / "main_en.pdf"
    shutil.copyfile(generated_pdf, PDF_EN)
    return PDF_EN


def compile_summary() -> Path:
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-jobname=summary_en_build",
        f"-output-directory={REPORT_EN}",
        str(SUMMARY_TEX_EN),
    ]
    for _ in range(2):
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    generated_pdf = REPORT_EN / "summary_en_build.pdf"
    shutil.copyfile(generated_pdf, SUMMARY_EN)
    return SUMMARY_EN


def build_english_tables(metrics: dict) -> dict[str, str]:
    paths: dict[str, str] = {}

    data_rows = []
    for i, block_len in enumerate(metrics["data"]["block_lengths"]):
        data_rows.append(
            {
                "Block": f"Block {i + 1}",
                "Length / samples": block_len,
                "Target stimuli": metrics["data"]["target_counts"][i],
                "Non-target stimuli": 4000 - metrics["data"]["target_counts"][i],
            }
        )
    paths["data"] = save_table(pd.DataFrame(data_rows), "data-summary-en")

    p1e1 = pd.DataFrame(metrics["part1"]["exp1"]["rows"]).rename(
        columns={
            "滤波器": "Filter",
            "最低阶数": "Min. order",
            "通带波纹/dB": "PB ripple (dB)",
            "阻带最小衰减/dB": "SB atten. (dB)",
            "过渡带宽/Hz": "Trans. width (Hz)",
            "通带群时延均值/ms": "Mean GD (ms)",
            "通带群时延标准差/ms": "GD std (ms)",
        }
    )
    paths["p1e1"] = save_table(p1e1, "part1-exp1-summary-en")

    p1e2 = pd.DataFrame(metrics["part1"]["exp2"]["rows"]).rename(
        columns={
            "方式": "Method",
            "10 Hz幅值": "10 Hz amp.",
            "50 Hz幅值": "50 Hz amp.",
            "50 Hz抑制/dB": "50 Hz supp. (dB)",
            "相对10 Hz延迟/ms": "Delay vs 10 Hz (ms)",
        }
    )
    paths["p1e2"] = save_table(p1e2, "part1-exp2-summary-en")

    p1e3_cont = pd.DataFrame(metrics["part1"]["exp3"]["drift_rows"]).rename(
        columns={
            "Block": "Block",
            "原始慢变范围/uV": "Raw drift range (uV)",
            "高通后慢变范围/uV": "After HP range (uV)",
        }
    )
    paths["p1e3_cont"] = save_table(p1e3_cont, "part1-exp3-continuous-en")

    p1e3_syn = pd.DataFrame(metrics["part1"]["exp3"]["synthetic_rows"]).rename(
        columns={
            "截止频率/Hz": "Cutoff (Hz)",
            "脉冲峰值/uV": "Pulse peak (uV)",
            "峰值潜伏期/ms": "Peak latency (ms)",
            "后冲最小值/uV": "Undershoot min. (uV)",
        }
    )
    paths["p1e3_syn"] = save_table(p1e3_syn, "part1-exp3-synthetic-en")

    p1e4_cut = pd.DataFrame(metrics["part1"]["exp4"]["cutoff_rows"]).rename(
        columns={
            "条件": "Condition",
            "保留试次": "Kept epochs",
            "Pe峰值/uV": "Pe peak (uV)",
            "Pe潜伏期/ms": "Pe latency (ms)",
            "早期最小值/uV": "Early minimum (uV)",
            "300-700 ms面积": "Area 300-700 ms",
        }
    )
    paths["p1e4_cut"] = save_table(p1e4_cut, "part1-exp4-cutoff-summary-en")

    p1e4_ord = pd.DataFrame(metrics["part1"]["exp4"]["order_rows"]).rename(
        columns={
            "条件": "Condition",
            "保留试次": "Kept epochs",
            "正峰/uV": "Positive peak (uV)",
            "正峰潜伏期/ms": "Peak latency (ms)",
            "早期负偏转/uV": "Early neg. defl. (uV)",
            "早期正过冲/uV": "Early pos. overshoot (uV)",
            "0-250 ms差异RMS/uV": "0-250 ms diff. RMS (uV)",
            "0-250 ms差异绝对面积": "0-250 ms absolute difference area",
        }
    )
    paths["p1e4_ord"] = save_table(p1e4_ord, "part1-exp4-order-summary-en")

    p2e1 = pd.DataFrame(metrics["part2"]["exp1"]["rows"]).rename(
        columns={
            "方法": "Method",
            "最短taps": "Min. taps",
            "通带波纹/dB": "PB ripple (dB)",
            "阻带衰减/dB": "SB atten. (dB)",
            "固定群时延/样本": "Delay (samples)",
            "固定群时延/ms": "Delay (ms)",
        }
    )
    paths["p2e1"] = save_table(p2e1, "part2-exp1-summary-en")

    p2e2_win = pd.DataFrame(metrics["part2"]["exp2"]["window_rows"]).rename(
        columns={
            "窗函数": "Window",
            "通带波纹/dB": "PB ripple (dB)",
            "阻带衰减/dB": "SB atten. (dB)",
            "过渡带宽/Hz": "Trans. width (Hz)",
            "固定群时延/样本": "Delay (samples)",
            "固定群时延/ms": "Delay (ms)",
        }
    )
    paths["p2e2_win"] = save_table(p2e2_win, "part2-exp2-window-summary-en")

    p2e2_len = pd.DataFrame(metrics["part2"]["exp2"]["length_rows"]).rename(
        columns={
            "taps": "Taps",
            "通带波纹/dB": "PB ripple (dB)",
            "阻带衰减/dB": "SB atten. (dB)",
            "过渡带宽/Hz": "Trans. width (Hz)",
            "固定群时延/样本": "Delay (samples)",
            "固定群时延/ms": "Delay (ms)",
            "实现代价/乘加每样本": "MACs per sample",
        }
    )
    paths["p2e2_len"] = save_table(p2e2_len, "part2-exp2-length-summary-en")

    p2e3_filter = pd.read_csv(config.TABLES_DIR / "part2-exp3-filter-summary.csv")
    p2e3_filter.columns = [
        "Filter",
        "Taps / order",
        "Fixed delay (samples)",
        "GD metric (ms)",
        "PB ripple (dB)",
        "Low-stop atten. (dB)",
        "High-stop atten. (dB)",
    ]
    paths["p2e3_filter"] = save_table(p2e3_filter, "part2-exp3-filter-summary-en")

    p2e3_erp = pd.read_csv(config.TABLES_DIR / "part2-exp3-erp-summary.csv")
    p2e3_erp.columns = ["Waveform", "Kept epochs", "Peak (uV)", "Peak latency (ms)"]
    paths["p2e3_erp"] = save_table(p2e3_erp, "part2-exp3-erp-summary-en")

    return paths


def build_summary_section(metrics: dict) -> str:
    p1e1 = metrics["part1"]["exp1"]
    p1e2 = metrics["part1"]["exp2"]
    p1e4 = metrics["part1"]["exp4"]
    p2e3 = metrics["part2"]["exp3"]
    p1e1_rows = {row["滤波器"]: row for row in p1e1["rows"]}
    cutoff_rows = {row["条件"]: row for row in p1e4["cutoff_rows"]}
    text = ""
    text += paragraph(r"\section*{Summary}")
    text += paragraph(
        "Clinical question: why can the same EEG recording produce different peak timing, different waveform shape, and even different interpretation after changing the filter settings?"
    )
    text += paragraph(
        "The four panels below correspond to four key questions: whether the same cutoff goal implies the same cost, whether peak latency can be preserved reliably, whether aggressive highpass filtering can rewrite late ERP morphology, and whether delay can be compensated equally well for FIR and IIR designs."
    )
    text += paragraph(r"{\captionsetup{font=footnotesize}")
    text += figure_block(
        "Summary figure: A shows the minimum order and passband group delay of four IIR designs under the same 40/60 Hz target; B shows the timing effect of causal versus zero-phase lowpass filtering on the 10 Hz component; C shows the late ERP difference between the 0.1-15 Hz and 1.0-15 Hz conditions at Fz; D shows the compensated FIR and causal IIR ERP waveforms and their peak latency difference.",
        metrics["summary_figure"],
        width="0.85\\linewidth",
        numbered=False,
    )
    text += paragraph(r"}")
    text += (
        r"{\small" "\n"
        r"\begin{itemize}[label=--,leftmargin=1.3em,itemsep=0.10em,topsep=0.15em,parsep=0pt]" "\n"
        r"\item \textbf{Panel A: different filters are not interchangeable.} Under the same 40/60 Hz target, Butterworth requires 13th order while Elliptic requires only 5th order, yet both satisfy the spectral specification. Their temporal cost is different as well, with passband group delay around 37 ms versus 20 ms." "\n"
        r"\item \textbf{Panel B: zero-phase filtering protects peak timing.} In Experiment 2, single causal lowpass filtering delayed the main oscillation by about 22 ms, repeated causal filtering by about 43 ms, while zero-phase filtering kept the delay essentially at 0 ms. For latency-based interpretation, this difference is clinically meaningful." "\n"
        r"\item \textbf{Panel C: a flatter baseline is not necessarily a truer result.} Raising the highpass from 0.1-15 Hz to 1.0-15 Hz reduced the late positive peak at Fz from 11.89 uV to 7.05 uV and shrank the 300-700 ms area from 2.420 to 0.765. A visually cleaner baseline may therefore come at the cost of erasing genuine late ERP structure." "\n"
        r"\item \textbf{Panel D: FIR and IIR differ in whether their delay can be interpreted.} The FIR design introduces a fixed 1900 ms delay that can be compensated globally, bringing its main peak back to about 479 ms. The IIR delay is smaller on average but frequency dependent, so its ERP peak still appears near 399 ms and cannot be fully corrected with a single shift." "\n"
        r"\end{itemize}" "\n"
        r"}" "\n"
    )
    text += paragraph(
        r"{\small \textbf{Clinical reminder:} filtering does not create disease information out of nothing, but it does change how peak amplitude, latency, and slow-wave strength appear. When reading ERP, evoked potential, or other bioelectric results, one should always check the cutoff frequencies, filter family, whether zero-phase processing was used, and whether delay compensation was applied. If these parameters are aggressive or insufficiently documented, it is safer to inspect the raw waveform, a milder-parameter result, and the compensated versus uncompensated comparison before drawing a clinical conclusion.}"
    )
    return text


def build_report_body(metrics: dict, tables: dict[str, str]) -> str:
    p1e1 = metrics["part1"]["exp1"]
    p1e2 = metrics["part1"]["exp2"]
    p1e3 = metrics["part1"]["exp3"]
    p1e4 = metrics["part1"]["exp4"]
    p2e1 = metrics["part2"]["exp1"]
    p2e2 = metrics["part2"]["exp2"]
    p2e3 = metrics["part2"]["exp3"]

    orders = p1e1["orders"]
    p1e1_rows = {row["滤波器"]: row for row in p1e1["rows"]}
    cutoff_rows = {row["条件"]: row for row in p1e4["cutoff_rows"]}
    order_rows = {row["条件"]: row for row in p1e4["order_rows"]}
    exp2_rows = {row["方式"]: row for row in p1e2["rows"]}
    p2_method_rows = {row["方法"]: row for row in p2e1["rows"]}
    p1e3_drift = {row["Block"]: row for row in p1e3["drift_rows"]}
    p1e3_syn = {row["截止频率/Hz"]: row for row in p1e3["synthetic_rows"]}
    p2_window_rows = {row["窗函数"]: row for row in p2e2["window_rows"]}
    p2_length_rows = {row["taps"]: row for row in p2e2["length_rows"]}

    text = ""
    text += paragraph(r"\section{Experimental Setup and Data Description}")
    text += paragraph(
        "This report covers both the IIR and FIR parts of the medical signal filtering lab. "
        "All signal processing, filter design, metric extraction, and figure generation were completed in Python, "
        "and the report is organized according to methods, results, analysis, and discussion."
    )
    text += paragraph(
        f"The real ERP dataset is \\texttt{{sub7A.mat}}. Its original sampling rate can be verified as {metrics['data']['original_fs']:.0f} Hz from the trigger spacing and the provided example code. "
        "For consistency with the assignment wording, all ERP experiments in Part-I were first resampled to 200 Hz, and Part-II Experiment 3 was resampled to 1000 Hz. "
        "All ERP analyses used target trials from the two continuous blocks; filtering and epoching were first performed blockwise and then averaged across blocks."
    )
    text += paragraph(
        f"Unified ERP preprocessing settings were: epoch window {config.EPOCH_TMIN * 1000:.0f} ms to {config.EPOCH_TMAX * 1000:.0f} ms, "
        f"baseline interval {config.BASELINE[0] * 1000:.0f} ms to {config.BASELINE[1] * 1000:.0f} ms, reference channels TP7/TP8, and the main observation channel Fz. "
        "Trigger positions followed the indexing convention of the provided example code and were not shifted by an additional $-1$."
    )
    text += paragraph(r"\subsection*{Data Overview}")
    text += paragraph(rf"\input{{{tables['data']}}}")

    text += paragraph(r"\section{Part-I IIR Filter Design, Implementation, and Distortion Evaluation}")
    text += paragraph(r"\subsection{Experiment 1: Four IIR Lowpass Families Under a Unified Specification}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "The design specification was $f_s=1000$ Hz, passband edge 40 Hz, stopband edge 60 Hz, maximum passband ripple 1 dB, and minimum stopband attenuation 40 dB. "
        "Butterworth, Chebyshev-I, Chebyshev-II, and Elliptic lowpass filters were designed, and the minimum valid order for each family was determined automatically."
    )
    text += paragraph(
        "For each family, the frequency response was computed on a common grid and used to extract passband ripple, minimum stopband attenuation, transition width, and the mean and standard deviation of passband group delay. "
        "This makes it possible to compare not only spectral compliance, but also the temporal cost associated with each design."
    )
    text += figure_block("Magnitude, phase, and group-delay comparison of four IIR lowpass families.", p1e1["figure"])
    text += paragraph(rf"\input{{{tables['p1e1']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"Figure 1 and the table show that all four IIR filters satisfy the same 40/60 Hz amplitude specification, but they do so with clearly different costs. "
        f"Butterworth needs order {orders['Butterworth']}, Chebyshev-I order {orders['Chebyshev-I']}, Chebyshev-II order {orders['Chebyshev-II']}, and Elliptic only order {orders['Elliptic']}. "
        f"Elliptic also gives the narrowest transition band, about {p1e1_rows['Elliptic']['过渡带宽/Hz']:.2f} Hz, whereas Butterworth remains more gradual."
    )
    text += paragraph(
        f"The passband group delay is also quite different. Butterworth shows a mean passband delay of about {p1e1_rows['Butterworth']['通带群时延均值/ms']:.2f} ms, "
        f"while Chebyshev-II is lower at about {p1e1_rows['Chebyshev-II']['通带群时延均值/ms']:.2f} ms. "
        "This confirms that stronger frequency selectivity does not automatically imply better temporal fidelity."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why can the required order differ so much across filters under the same specification?",
                f"Because the four families distribute approximation error differently. In this experiment Butterworth required order {orders['Butterworth']}, Chebyshev-I {orders['Chebyshev-I']}, Chebyshev-II {orders['Chebyshev-II']}, and Elliptic only {orders['Elliptic']}. The Elliptic filter achieved the tightest transition by allowing ripple on both sides."
            ),
            (
                "Which family emphasizes passband flatness and which emphasizes transition sharpness?",
                f"Butterworth emphasizes passband flatness; Elliptic emphasizes transition sharpness. This can be seen directly in Figure 1 and in the transition width values, where Elliptic reaches about {p1e1_rows['Elliptic']['过渡带宽/Hz']:.2f} Hz."
            ),
            (
                "Why is the phase of IIR filters usually nonlinear?",
                "Because IIR filters are rational transfer functions with poles and zeros that generally do not satisfy the symmetry condition required for linear phase. Their group delay therefore varies with frequency."
            ),
            (
                "Why is group delay more informative than the phase curve alone in biomedical signals?",
                f"Because group delay directly describes how much peaks and envelopes are shifted in time. For example, Butterworth shows about {p1e1_rows['Butterworth']['通带群时延均值/ms']:.2f} ms mean delay in the passband, which is immediately interpretable in latency-sensitive biomedical signals."
            ),
        ],
    )

    text += paragraph(r"\subsection{Experiment 2: Filtering Effect, Phase Distortion, and Repeated Filtering}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "The artificial signal was $x(t)=\sin(2\pi 10 t)+\sin(2\pi 50 t)$. A 4th-order Butterworth 20 Hz lowpass was applied in three ways: single causal filtering, repeated causal filtering, and zero-phase filtering. "
        "Relative delay was estimated by cross-correlation against the ideal 10 Hz component over the central time segment."
    )
    text += figure_block("Comparison of single causal, repeated causal, and zero-phase lowpass processing in the time domain, frequency domain, and at the record boundaries.", p1e2["figure"])
    text += paragraph(rf"\input{{{tables['p1e2']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"All three methods attenuate the 50 Hz interference strongly, but their temporal costs are different. Single causal filtering suppresses 50 Hz by about {abs(exp2_rows['Single causal']['50 Hz抑制/dB']):.2f} dB, repeated causal filtering by about {abs(exp2_rows['Repeated causal']['50 Hz抑制/dB']):.2f} dB, and zero-phase filtering retains nearly zero delay."
    )
    text += paragraph(
        f"The estimated latency shift is about {p1e2['delay_single_ms']:.2f} ms for single causal filtering, {p1e2['delay_twice_ms']:.2f} ms for repeated causal filtering, and {p1e2['delay_zero_ms']:.2f} ms for zero-phase filtering. "
        "Therefore, improved attenuation through repeated filtering comes with extra phase distortion, whereas zero-phase filtering preserves timing but introduces edge artifacts and cannot be used in real-time settings."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why does repeated causal filtering improve attenuation but worsen temporal distortion?",
                f"Because the magnitude response is effectively squared, which strengthens attenuation, but the phase response is also accumulated. In this experiment the delay increased from about {p1e2['delay_single_ms']:.2f} ms to {p1e2['delay_twice_ms']:.2f} ms after repeated filtering."
            ),
            (
                "Why can zero-phase filtering remove phase distortion?",
                f"Because forward-backward filtering cancels the net phase shift. In this experiment the estimated delay after zero-phase filtering was about {p1e2['delay_zero_ms']:.2f} ms."
            ),
            (
                "Why are boundary artifacts emphasized when discussing zero-phase filtering?",
                "Because zero-phase filtering uses future and past samples, so the beginning and end of the record are handled differently from the interior. The boundary zoom in Figure 2 makes this visible."
            ),
            (
                "Is zero-phase filtering suitable for all biomedical signal processing scenarios?",
                "No. It is excellent for offline analysis of morphology and latency, but it is noncausal and therefore unsuitable for real-time monitoring, closed-loop systems, or alarm pipelines."
            ),
        ],
    )

    text += paragraph(r"\subsection{Experiment 3: Highpass Filters, Slow Drift, and Time Constants}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "For the real data, the continuous ERP recordings were resampled to 200 Hz and the Fz channel was compared before and after zero-phase 1 Hz highpass filtering. "
        "For the synthetic example, a 0.2 Hz drift plus a Gaussian pulse was filtered with a 4th-order highpass while the cutoff was varied across 0.1, 0.5, and 1.0 Hz."
    )
    text += figure_block("Slow drift in continuous Fz, and its suppression after 1 Hz highpass filtering.", p1e3["figure_continuous"])
    text += paragraph(rf"\input{{{tables['p1e3_cont']}}}")
    text += figure_block("Baseline recovery and morphology distortion of a drift-plus-pulse signal under different highpass cutoffs.", p1e3["figure_synthetic"])
    text += paragraph(rf"\input{{{tables['p1e3_syn']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"In the real data, 1 Hz highpass filtering strongly reduced the slow trend. For Block 1, the slow-drift range decreased from {p1e3_drift['Block 1']['原始慢变范围/uV']:.2f} uV to {p1e3_drift['Block 1']['高通后慢变范围/uV']:.2f} uV; for Block 2, it decreased from {p1e3_drift['Block 2']['原始慢变范围/uV']:.2f} uV to {p1e3_drift['Block 2']['高通后慢变范围/uV']:.2f} uV."
    )
    text += paragraph(
        f"The synthetic example shows the tradeoff more clearly: as the cutoff increases from 0.1 to 1.0 Hz, the pulse peak drops from {p1e3_syn[0.1]['脉冲峰值/uV']:.2f} uV to {p1e3_syn[1.0]['脉冲峰值/uV']:.2f} uV, while the undershoot becomes more pronounced. "
        "Thus, faster baseline recovery is obtained at the cost of distorting slow components."
    )
    text += paragraph(
        "This is especially important in ERP averaging: slow drift affects the prestimulus baseline estimate for individual epochs, and trial-to-trial baseline offsets increase the variance of the average and contaminate late slow components."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why is a highpass filter not just a tool for removing the DC component?",
                "Because it suppresses an entire low-frequency range, not only the 0 Hz point. Late ERP components, baseline drift, and slow recovery processes all occupy that range."
            ),
            (
                "Why does a higher cutoff restore baseline faster but also weaken slow useful components?",
                f"Because more low-frequency energy is treated as unwanted. In the synthetic example, increasing the cutoff from 0.1 to 1.0 Hz reduced the pulse peak from {p1e3_syn[0.1]['脉冲峰值/uV']:.2f} uV to {p1e3_syn[1.0]['脉冲峰值/uV']:.2f} uV."
            ),
            (
                "What is the unavoidable conflict between drift removal and slow-wave preservation in ERP research?",
                "The same frequency region contains both unwanted drift and meaningful slow ERP components. Improving one necessarily risks harming the other."
            ),
        ],
    )

    text += paragraph(r"\subsection{Experiment 4: How Filter Choice Changes ERP Interpretation}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "All target trials from both blocks were used. For the cutoff comparison, zero-phase Butterworth filters were used: 50 Hz lowpass only, 0.1-15 Hz, 0.5-15 Hz, and 1.0-15 Hz. "
        "For the order comparison, the highpass was fixed at 2.5 Hz and the lowpass at 15 Hz, while the causal highpass order was changed from 2 to 8."
    )
    text += figure_block("Average Fz ERP under different highpass cutoff settings.", p1e4["figure_cutoff"])
    text += paragraph(rf"\input{{{tables['p1e4_cut']}}}")
    text += figure_block("Causal filtering results with identical cutoff frequencies but different highpass orders.", p1e4["figure_order"])
    text += paragraph(rf"\input{{{tables['p1e4_ord']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"Increasing the highpass cutoff directly reshapes the late ERP. Under 0.1-15 Hz, the Pe peak is about {cutoff_rows['0.1-15 Hz']['Pe峰值/uV']:.2f} uV and the 300-700 ms area is {cutoff_rows['0.1-15 Hz']['300-700 ms面积']:.3f}; under 1.0-15 Hz, the Pe peak drops to {cutoff_rows['1.0-15 Hz']['Pe峰值/uV']:.2f} uV and the area shrinks to {cutoff_rows['1.0-15 Hz']['300-700 ms面积']:.3f}."
    )
    text += paragraph(
        f"When only the causal highpass order is changed, the waveform also changes substantially. The 2nd-order filter gives a positive peak of about {order_rows['2nd-order HP']['正峰/uV']:.2f} uV at {order_rows['2nd-order HP']['正峰潜伏期/ms']:.0f} ms, while the 8th-order filter shifts the peak to {order_rows['8th-order HP']['正峰潜伏期/ms']:.0f} ms and increases the 0-250 ms difference RMS from {order_rows['2nd-order HP']['0-250 ms差异RMS/uV']:.3f} to {order_rows['8th-order HP']['0-250 ms差异RMS/uV']:.3f} uV."
    )
    text += paragraph(
        "This means that ERP filter settings are not merely preprocessing details; they become part of the scientific conclusion itself. Cutoff, order, causality, and delay behavior must therefore be reported explicitly."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why can increasing the highpass cutoff from 0.1 Hz to 1 Hz severely damage late ERP morphology?",
                f"Because the late positive ERP is itself a low-frequency, wide-duration component. In this experiment the Pe peak dropped from {cutoff_rows['0.1-15 Hz']['Pe峰值/uV']:.2f} uV to {cutoff_rows['1.0-15 Hz']['Pe峰值/uV']:.2f} uV."
            ),
            (
                "Why is a 'cleaner' baseline not necessarily a more truthful result?",
                "Because the same operation that removes drift may also remove genuine late components and change peak shape and area."
            ),
            (
                "Why can a steeper causal highpass create stronger temporal artifacts?",
                f"Because stronger phase curvature and sharper transitions amplify waveform distortion. Here the 8th-order condition produced larger early-window distortion metrics than the 2nd-order condition."
            ),
            (
                "Why should filtering parameters be documented as part of the ERP result itself?",
                "Because different parameter choices can change peak amplitude, latency, and morphology enough to affect interpretation."
            ),
        ],
    )

    text += paragraph(r"\section{Part-II FIR Filter Design}")
    text += paragraph(r"\subsection{Experiment 1: Comparison of Three FIR Design Methods}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "At 1000 Hz, three FIR lowpass design methods were compared under the same 40/60 Hz specification: Hamming-window design, frequency-sampling design, and equiripple approximation. "
        "For each method, the shortest odd tap length that satisfied the specification was searched automatically."
    )
    text += figure_block("Magnitude, phase, and group-delay comparison of three FIR lowpass design methods.", p2e1["figure"])
    text += paragraph(rf"\input{{{tables['p2e1']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"All three methods met the amplitude specification, but their lengths differed greatly. Equiripple required only {p2_method_rows['Equiripple']['最短taps']:.0f} taps, Hamming-window design required {p2_method_rows['Window-Hamming']['最短taps']:.0f} taps, and frequency sampling required {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps with a fixed delay of {p2_method_rows['Frequency Sampling']['固定群时延/ms']:.0f} ms."
    )
    text += paragraph(
        f"In Figure 7, the dense yellow 'stacking' near the stopband onset of the frequency-sampling method is not a plotting mistake. Because the design had to grow to {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps to meet the same specification, its stopband contains extremely dense zeros and ripple oscillations, which visually merge into a thick colored band after scaling."
    )
    text += paragraph(
        "This comparison shows that FIR methods differ not only in being linear phase, but in how efficiently they allocate approximation error. Equiripple uses the available tolerance most efficiently, while the frequency-sampling solution becomes very long and therefore very costly in delay."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why can three linear-phase methods still need very different tap lengths under the same specification?",
                f"Because they optimize different criteria. In this experiment Hamming-window design required {p2_method_rows['Window-Hamming']['最短taps']:.0f} taps, frequency sampling {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps, and equiripple only {p2_method_rows['Equiripple']['最短taps']:.0f} taps."
            ),
            (
                "Why can equiripple often achieve the shortest valid design?",
                f"Because it follows a minimax strategy and uses the allowed error almost completely. Here it reached about {p2_method_rows['Equiripple']['阻带衰减/dB']:.2f} dB stopband attenuation with only {p2_method_rows['Equiripple']['最短taps']:.0f} taps."
            ),
            (
                "Why is the frequency-sampling method still educationally useful even if it is not the most economical here?",
                f"Because it reveals directly how sampled spectral constraints map into an FIR response. However, in this experiment it required {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps and therefore a very large fixed delay."
            ),
            (
                "Does linear phase automatically mean small delay?",
                "No. Linear phase means constant delay, not necessarily short delay. A very long FIR can still be perfectly linear phase while introducing a very large fixed delay."
            ),
        ],
    )

    text += paragraph(r"\subsection{Experiment 2: Effects of Window Type and Filter Length}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "This experiment was divided into two parts. First, the tap length was fixed at 61 and the Bartlett, Hann, Hamming, and Blackman windows were compared. "
        "Second, the window was fixed to Hamming and the tap lengths 31, 61, and 121 were compared."
    )
    text += figure_block("FIR lowpass comparison across different window functions at 61 taps.", p2e2["figure_window"])
    text += paragraph(rf"\input{{{tables['p2e2_win']}}}")
    text += figure_block("FIR lowpass comparison across different Hamming tap lengths.", p2e2["figure_length"])
    text += paragraph(rf"\input{{{tables['p2e2_len']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"At 61 taps, the window choice mainly trades transition width against stopband leakage. Blackman yields the strongest attenuation among the four, whereas Bartlett shows the widest transition. "
        "All four share the same fixed delay because the tap count is identical."
    )
    text += paragraph(
        f"With a fixed Hamming window, increasing the length from 31 to 121 taps reduces stopband leakage and narrows the transition region, but the fixed delay increases from {p2_length_rows[31]['固定群时延/ms']:.0f} ms to {p2_length_rows[121]['固定群时延/ms']:.0f} ms."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why does the group delay remain identical across different windows when the tap count is fixed?",
                "Because a linear-phase FIR with the same length always has delay $(L-1)/2$, independent of the window shape."
            ),
            (
                "Why do different windows mainly change the stopband and transition behavior?",
                "Because the window modifies the side-lobe and main-lobe structure of the truncated impulse response."
            ),
            (
                "Why does increasing the tap length improve spectral performance but increase implementation cost?",
                f"Because more coefficients provide more freedom in the frequency domain, but also increase delay and multiply-accumulate cost. Here the delay rose from {p2_length_rows[31]['固定群时延/ms']:.0f} ms to {p2_length_rows[121]['固定群时延/ms']:.0f} ms."
            ),
            (
                "How should one choose between shorter and longer FIR implementations in practice?",
                "The choice depends on whether sharper spectral separation or shorter delay and lower computational cost is more important in the target application."
            ),
        ],
    )

    text += paragraph(r"\subsection{Experiment 3: FIR and IIR Bandpass Filtering of ERP Signals}")
    text += paragraph(r"\subsubsection*{Methods}")
    text += paragraph(
        "The ERP data were resampled to 1000 Hz. A causal equiripple FIR bandpass and a 4th-order causal Butterworth IIR bandpass were then applied to the continuous signal. "
        "ERP averages were first compared without compensation, and then the FIR result was compensated by its fixed delay of $(L-1)/2$ samples."
    )
    text += figure_block("Frequency-response, phase, and group-delay comparison between the FIR and IIR bandpass filters.", p2e3["figure_response"])
    text += paragraph(rf"\input{{{tables['p2e3_filter']}}}")
    text += figure_block("ERP comparison before compensation and after fixed-delay FIR compensation.", p2e3["figure_erp"])
    text += paragraph(rf"\input{{{tables['p2e3_erp']}}}")
    text += paragraph(r"\subsubsection*{Analysis and Discussion}")
    text += paragraph(
        f"The FIR design used {p2e3['fir_numtaps']:.0f} taps and therefore a fixed delay of {p2e3['fir_delay_ms']:.0f} ms. "
        f"After compensation, the FIR peak appears at about {p2e3['fir_comp_peak_latency_ms']:.0f} ms. "
        f"The IIR mean group delay is much smaller, about {p2e3['iir_group_delay_mean_ms']:.2f} ms, but its ERP peak still appears at about {p2e3['iir_peak_latency_ms']:.0f} ms because the delay is frequency dependent and cannot be removed by a single global shift."
    )
    text += paragraph(
        "This experiment shows why FIR delay can be explained and compensated when phase is linear, whereas IIR delay is harder to interpret even when its average is shorter."
    )
    text += qa_block(
        "Answers to Discussion Questions",
        [
            (
                "Why can the compensated FIR and the IIR still produce different ERP waveforms even if both nominally preserve 1-40 Hz?",
                f"Because the difference is not determined by magnitude alone. Here the compensated FIR peak is around {p2e3['fir_comp_peak_latency_ms']:.0f} ms, whereas the IIR peak remains around {p2e3['iir_peak_latency_ms']:.0f} ms."
            ),
            (
                "Why can FIR be compensated by a global shift but IIR cannot?",
                "Because the FIR used here is linear phase and therefore has constant delay across the band, whereas the IIR delay varies with frequency."
            ),
            (
                "Why does an ERP bandpass FIR become very long in the high-sampling-rate, low-cutoff setting?",
                f"Because the low-frequency transition is extremely narrow. Here the FIR needed {p2e3['fir_numtaps']} taps and therefore a fixed delay of {p2e3['fir_delay_ms']:.0f} ms."
            ),
            (
                "Which filter type is preferable for offline analysis, real-time monitoring, and embedded implementation?",
                f"FIR is preferable for offline analysis when interpretable delay compensation matters; IIR is preferable for real-time low-latency monitoring and often for embedded systems where computational cost is tightly constrained."
            ),
        ],
    )

    text += paragraph(r"\section{Appendix}")
    text += paragraph(
        r'The final submission package contains three parts: the complete report \path{medical_signal_filter_report.pdf}, the one-page conclusion summary \path{summary.pdf}, and the source-code directory \path{code/}.'
    )
    text += paragraph(
        r'Inside \path{code/}, \path{scripts/} provides the experiment entry points and workflow scripts; \path{medsiglab/} provides the lower-level functions for data loading, filter design, ERP processing, plotting, and export; and \path{requirements.txt} lists the required Python dependencies.'
    )
    text += paragraph(
        r'To reproduce the project, place the provided course dataset directory at the project root so that it contains \path{sub7A.mat}, \path{64-channels.loc}, and the example script. Then enter \path{code/} and run:'
    )
    text += paragraph(r"\noindent\hspace*{2em}\texttt{pip install -r requirements.txt}")
    text += paragraph(r"To reproduce all figures, tables, and the PDF report, run:")
    text += paragraph(r"\noindent\hspace*{2em}\texttt{python3 scripts/run\_all.py}")
    text += paragraph(r"To rebuild only the report, run:")
    text += paragraph(r"\noindent\hspace*{2em}\texttt{python3 scripts/build\_report.py}")
    text += paragraph(r"To rebuild the final submission package, run:")
    text += paragraph(r"\noindent\hspace*{2em}\texttt{python3 scripts/package\_submission.py}")

    text += paragraph(r"\clearpage")
    text += build_summary_section(metrics)
    return text


def main() -> None:
    OUTPUT_EN.mkdir(parents=True, exist_ok=True)
    TABLES_EN.mkdir(parents=True, exist_ok=True)
    REPORT_EN.mkdir(parents=True, exist_ok=True)

    metrics = json.loads(SOURCE_METRICS.read_text(encoding="utf-8"))
    tables = build_english_tables(metrics)
    BODY_EN.write_text(build_report_body(metrics, tables), encoding="utf-8")
    SUMMARY_BODY_EN.write_text(build_summary_section(metrics), encoding="utf-8")
    pdf_path = compile_report()
    summary_path = compile_summary()
    print(
        json.dumps(
            {
                "report_pdf_en": str(pdf_path),
                "summary_pdf_en": str(summary_path),
                "tables_dir_en": str(TABLES_EN),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
