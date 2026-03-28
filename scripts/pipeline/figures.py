from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from medsiglab import config, plotting


def render_part1_exp1(plot_items: list[dict]) -> str:
    figure_name = "part1-exp1-iir-families.pdf"
    plotting.plot_filter_responses(
        plot_items,
        title="Part-I Experiment 1: IIR Lowpass Family Comparison",
        path=config.FIGURES_DIR / figure_name,
        xlim=(0.0, 120.0),
        group_delay_focus_band=(0.0, 45.0),
        group_delay_mag_floor_db=-20.0,
    )
    return figure_name


def render_part1_exp2(
    time_s: np.ndarray,
    signal_in: np.ndarray,
    pure10: np.ndarray,
    causal_once: np.ndarray,
    causal_twice: np.ndarray,
    zero_phase: np.ndarray,
    spectra: dict[str, np.ndarray],
) -> str:
    figure_name = "part1-exp2-causal-zero-phase.pdf"
    freq = np.fft.rfftfreq(time_s.size, d=time_s[1] - time_s[0])
    # Fix label-to-color mapping explicitly so the same signal keeps the same color in all panels.
    color_map = {
        "Input": plotting.COLORS[0],
        "Pure 10 Hz": plotting.COLORS[5],
        "Single causal": plotting.COLORS[3],
        "Repeated causal": plotting.COLORS[2],
        "Zero phase": plotting.COLORS[1],
    }
    plotting.plot_four_panel(
        [
            {
                "title": "Time domain: first 0.6 s",
                "x": time_s,
                "series": [
                    {"label": "Input", "y": signal_in, "color": color_map["Input"]},
                    {"label": "Single causal", "y": causal_once, "color": color_map["Single causal"]},
                    {"label": "Repeated causal", "y": causal_twice, "color": color_map["Repeated causal"]},
                    {"label": "Zero phase", "y": zero_phase, "color": color_map["Zero phase"]},
                ],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
                "xlim": (0.0, 0.6),
            },
            {
                "title": "Spectrum",
                "x": freq,
                "series": [
                    {"label": key, "y": value, "color": color_map[key]}
                    for key, value in spectra.items()
                ],
                "xlabel": "Frequency (Hz)",
                "ylabel": "Amplitude",
                "xlim": (0.0, 80.0),
            },
            {
                "title": "Start edge (0-0.2 s)",
                "x": time_s,
                "series": [
                    {"label": "Pure 10 Hz", "y": pure10, "color": color_map["Pure 10 Hz"], "linestyle": ":"},
                    {"label": "Single causal", "y": causal_once, "color": color_map["Single causal"]},
                    {"label": "Repeated causal", "y": causal_twice, "color": color_map["Repeated causal"]},
                    {"label": "Zero phase", "y": zero_phase, "color": color_map["Zero phase"]},
                ],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
                "xlim": (0.0, 0.2),
            },
            {
                "title": "End edge (2.8-3.0 s)",
                "x": time_s,
                "series": [
                    {"label": "Pure 10 Hz", "y": pure10, "color": color_map["Pure 10 Hz"], "linestyle": ":"},
                    {"label": "Single causal", "y": causal_once, "color": color_map["Single causal"]},
                    {"label": "Repeated causal", "y": causal_twice, "color": color_map["Repeated causal"]},
                    {"label": "Zero phase", "y": zero_phase, "color": color_map["Zero phase"]},
                ],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
                "xlim": (2.8, 3.0),
            },
        ],
        path=config.FIGURES_DIR / figure_name,
    )
    return figure_name


def render_part1_exp3_continuous(
    block1_time: np.ndarray,
    block2_time: np.ndarray,
    block1_raw: np.ndarray,
    block2_raw: np.ndarray,
    block1_filtered: np.ndarray,
    block2_filtered: np.ndarray,
) -> str:
    figure_name = "part1-exp3-continuous-drift.pdf"
    plotting.plot_four_panel(
        [
            {
                "title": "Block 1 raw Fz",
                "x": block1_time,
                "series": [{"label": "Raw Fz", "y": block1_raw, "color": plotting.COLORS[0]}],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude (μV)",
            },
            {
                "title": "Block 2 raw Fz",
                "x": block2_time,
                "series": [{"label": "Raw Fz", "y": block2_raw, "color": plotting.COLORS[0]}],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude (μV)",
            },
            {
                "title": "Block 1: first 30 s after 1 Hz HP",
                "x": block1_time,
                "series": [
                    {"label": "Raw", "y": block1_raw, "color": plotting.COLORS[2]},
                    {"label": "1 Hz HP", "y": block1_filtered, "color": plotting.COLORS[3]},
                ],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude (μV)",
                "xlim": (0.0, 30.0),
            },
            {
                "title": "Block 2: first 30 s after 1 Hz HP",
                "x": block2_time,
                "series": [
                    {"label": "Raw", "y": block2_raw, "color": plotting.COLORS[2]},
                    {"label": "1 Hz HP", "y": block2_filtered, "color": plotting.COLORS[3]},
                ],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude (μV)",
                "xlim": (0.0, 30.0),
            },
        ],
        path=config.FIGURES_DIR / figure_name,
    )
    return figure_name


def render_part1_exp3_synthetic(synth_t: np.ndarray, synth_series: list[dict], drift: np.ndarray, pulse: np.ndarray) -> str:
    figure_name = "part1-exp3-highpass-cutoffs.pdf"
    plotting.plot_four_panel(
        [
            {
                "title": "Synthetic drift + pulse (full trace)",
                "x": synth_t,
                "series": synth_series,
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
            },
            {
                "title": "Synthetic pulse zoom",
                "x": synth_t,
                "series": synth_series,
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
                "xlim": (1.2, 1.9),
            },
            {
                "title": "Drift component",
                "x": synth_t,
                "series": [{"label": "0.2 Hz drift", "y": drift, "color": plotting.COLORS[4]}],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
            },
            {
                "title": "Gaussian pulse",
                "x": synth_t,
                "series": [{"label": "Pulse", "y": pulse, "color": plotting.COLORS[5]}],
                "xlabel": "Time (s)",
                "ylabel": "Amplitude",
            },
        ],
        path=config.FIGURES_DIR / figure_name,
    )
    return figure_name


def render_part1_exp4_cutoff(time_ms: np.ndarray, overlay_series: list[dict]) -> str:
    figure_name = "part1-exp4-cutoff-comparison.pdf"
    # The same time axis is reused for every cutoff condition so morphology can be compared directly.
    plotting.plot_signal_overlays(
        x=time_ms,
        series=overlay_series,
        title="Part-I Experiment 4: High-pass Cutoff Comparison at Fz",
        xlabel="Time (ms)",
        ylabel="Amplitude (μV)",
        path=config.FIGURES_DIR / figure_name,
        xlim=(-200.0, 800.0),
        vlines=[0.0],
    )
    return figure_name


def render_part1_exp4_order(time_ms: np.ndarray, overlay_series: list[dict]) -> str:
    figure_name = "part1-exp4-order-ringing.pdf"
    # Only the high-pass order changes here; all other ERP processing steps are kept fixed.
    plotting.plot_signal_overlays(
        x=time_ms,
        series=overlay_series,
        title="Part-I Experiment 4: High-pass Order and Temporal Distortion",
        xlabel="Time (ms)",
        ylabel="Amplitude (μV)",
        path=config.FIGURES_DIR / figure_name,
        xlim=(-200.0, 800.0),
        vlines=[0.0],
    )
    return figure_name


def render_part2_exp1(plot_items: list[dict]) -> str:
    figure_name = "part2-exp1-fir-methods.pdf"
    plotting.plot_filter_responses(
        plot_items,
        title="Part-II Experiment 1: FIR Design Method Comparison",
        path=config.FIGURES_DIR / figure_name,
        xlim=(0.0, 120.0),
        group_delay_focus_band=(0.0, 45.0),
        group_delay_mag_floor_db=-20.0,
    )
    return figure_name


def render_part2_exp2_window(plot_items_window: list[dict]) -> str:
    figure_name = "part2-exp2-window-comparison.pdf"
    plotting.plot_filter_responses(
        plot_items_window,
        title="Part-II Experiment 2.1: Window Function Comparison (61 taps)",
        path=config.FIGURES_DIR / figure_name,
        xlim=(0.0, 120.0),
        group_delay_focus_band=(0.0, 45.0),
        group_delay_mag_floor_db=-20.0,
    )
    return figure_name


def render_part2_exp2_length(plot_items_length: list[dict]) -> str:
    figure_name = "part2-exp2-length-comparison.pdf"
    plotting.plot_filter_responses(
        plot_items_length,
        title="Part-II Experiment 2.2: Hamming Length Comparison",
        path=config.FIGURES_DIR / figure_name,
        xlim=(0.0, 120.0),
        group_delay_focus_band=(0.0, 45.0),
        group_delay_mag_floor_db=-20.0,
    )
    return figure_name


def render_part2_exp3_filter_response(fir_response: dict, iir_response: dict) -> str:
    figure_name = "part2-exp3-filter-response.pdf"
    plotting.plot_filter_responses(
        [{"label": "FIR", "response": fir_response}, {"label": "IIR", "response": iir_response}],
        title="Part-II Experiment 3: FIR vs IIR Bandpass Responses",
        path=config.FIGURES_DIR / figure_name,
        xlim=(0.0, 80.0),
        group_delay_focus_band=(1.0, 40.0),
        group_delay_mag_floor_db=-20.0,
    )
    return figure_name


def render_part2_exp3_erp(
    time_ms: np.ndarray,
    fir_uncomp_wave: np.ndarray,
    fir_comp_time_ms: np.ndarray,
    fir_comp_wave: np.ndarray,
    iir_wave: np.ndarray,
    fir_comp_peak_latency_ms: float,
    iir_peak_latency_ms: float,
) -> str:
    figure_name = "part2-exp3-erp-comparison.pdf"
    plotting.plot_four_panel(
        [
            {
                "title": "Uncompensated ERP comparison",
                "x": time_ms,
                "series": [
                    {"label": "FIR uncompensated", "y": fir_uncomp_wave, "color": plotting.COLORS[0]},
                    {"label": "IIR causal", "y": iir_wave, "color": plotting.COLORS[3]},
                ],
                "xlabel": "Time (ms)",
                "ylabel": "Amplitude (μV)",
                "xlim": (-200.0, 800.0),
                "vlines": [0.0],
            },
            {
                "title": "Delay-compensated FIR vs IIR",
                "x": fir_comp_time_ms,
                "series": [
                    {"label": "FIR compensated", "y": fir_comp_wave, "color": plotting.COLORS[1]},
                    {"label": "IIR causal", "y": iir_wave, "color": plotting.COLORS[3]},
                ],
                "xlabel": "Time (ms)",
                "ylabel": "Amplitude (μV)",
                "xlim": (-200.0, 800.0),
                "vlines": [0.0],
            },
            {
                "title": "FIR only: before vs after compensation",
                "x": time_ms,
                "series": [
                    {"label": "Uncompensated", "y": fir_uncomp_wave, "color": plotting.COLORS[0]},
                    {"label": "Compensated", "y": fir_comp_wave, "color": plotting.COLORS[1]},
                ],
                "xlabel": "Time (ms)",
                "ylabel": "Amplitude (μV)",
                "xlim": (-200.0, 800.0),
                "vlines": [0.0],
            },
            {
                "title": "Peak latency markers",
                "x": fir_comp_time_ms,
                "series": [
                    {"label": "FIR compensated", "y": fir_comp_wave, "color": plotting.COLORS[1]},
                    {"label": "IIR causal", "y": iir_wave, "color": plotting.COLORS[3]},
                ],
                "xlabel": "Time (ms)",
                "ylabel": "Amplitude (μV)",
                "xlim": (100.0, 700.0),
                "vlines": [fir_comp_peak_latency_ms, iir_peak_latency_ms],
            },
        ],
        path=config.FIGURES_DIR / figure_name,
    )
    return figure_name


def build_clinical_summary_figure(
    exp1_artifacts: dict,
    exp2_artifacts: dict,
    exp4_artifacts: dict,
    exp23_artifacts: dict,
    exp1_metrics: dict,
    exp2_metrics: dict,
    exp4_metrics: dict,
    exp23_metrics: dict,
) -> str:
    figure_name = "clinical-summary.pdf"
    # The summary page reuses the strongest quantitative examples from the main experiments.
    exp1_rows = {row["滤波器"]: row for row in exp1_metrics["rows"]}
    time = exp2_artifacts["time"]
    pure10 = exp2_artifacts["pure10"]
    single = exp2_artifacts["single"]
    zero = exp2_artifacts["zero"]
    cutoff_results = exp4_artifacts["cutoff_results"]
    reference = cutoff_results["50 Hz LP only"]
    cutoff_rows = {row["条件"]: row for row in exp4_metrics["cutoff_rows"]}

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.8))

    ax = axes[0, 0]
    families = ["Butterworth", "Chebyshev-I", "Chebyshev-II", "Elliptic"]
    x = np.arange(len(families))
    orders = [exp1_rows[name]["最低阶数"] for name in families]
    colors = [plotting.COLORS[i % len(plotting.COLORS)] for i in range(len(families))]
    bars = ax.bar(x, orders, color=colors, width=0.65)
    ax.set_title("(A) Same cutoff goal, different filters")
    ax.set_ylabel("Minimum order")
    ax.set_xticks(x)
    ax.set_xticklabels(["Butter", "Cheb-I", "Cheb-II", "Ellip"])
    for bar, name in zip(bars, families):
        gd = exp1_rows[name]["通带群时延均值/ms"]
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.25,
            f"{int(bar.get_height())}th\n{gd:.0f} ms",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    ax.text(
        0.98,
        0.96,
        "Same amplitude target,\nbut different delay cost.",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.92, "edgecolor": "#BBBBBB"},
    )

    ax = axes[0, 1]
    ax.plot(time, pure10, color=plotting.COLORS[2], linestyle=":", linewidth=2.0, label="Pure 10 Hz")
    ax.plot(time, single, color=plotting.COLORS[3], linewidth=2.0, label="Single causal")
    ax.plot(time, zero, color=plotting.COLORS[1], linewidth=2.0, label="Zero phase")
    ax.set_title("(B) Zero-phase keeps peak timing")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_xlim(0.0, 0.35)
    ax.legend(loc="upper right")
    ax.text(
        0.03,
        0.96,
        f"Causal delay: {exp2_metrics['delay_single_ms']:.0f} ms\nRepeated causal: {exp2_metrics['delay_twice_ms']:.0f} ms\nZero-phase: {exp2_metrics['delay_zero_ms']:.0f} ms",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.92, "edgecolor": "#BBBBBB"},
    )

    ax = axes[1, 0]
    time_ms = reference.time_s * 1000.0
    ax.plot(time_ms, cutoff_results["50 Hz LP only"].fz_wave, color=plotting.COLORS[0], linewidth=2.0, label="50 Hz LP only")
    ax.plot(time_ms, cutoff_results["0.1-15 Hz"].fz_wave, color=plotting.COLORS[1], linewidth=2.0, label="0.1-15 Hz")
    ax.plot(time_ms, cutoff_results["1.0-15 Hz"].fz_wave, color=plotting.COLORS[4], linewidth=2.0, label="1.0-15 Hz")
    ax.axvline(0.0, color="#666666", linestyle="--", linewidth=1.0)
    ax.set_title("(C) High-pass can erase late ERP")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude (μV)")
    ax.set_xlim(-200.0, 800.0)
    ax.legend(loc="lower left")
    ax.text(
        0.03,
        0.86,
        f"Pe amplitude: {cutoff_rows['0.1-15 Hz']['Pe峰值/uV']:.2f} → {cutoff_rows['1.0-15 Hz']['Pe峰值/uV']:.2f} μV\n"
        f"Area 300-700 ms: {cutoff_rows['0.1-15 Hz']['300-700 ms面积']:.3f} → {cutoff_rows['1.0-15 Hz']['300-700 ms面积']:.3f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.92, "edgecolor": "#BBBBBB"},
    )

    ax = axes[1, 1]
    ax.plot(exp23_artifacts["time_ms"], exp23_artifacts["fir_comp_wave"], color=plotting.COLORS[1], linewidth=2.0, label="FIR compensated")
    ax.plot(exp23_artifacts["time_ms"], exp23_artifacts["iir_wave"], color=plotting.COLORS[3], linewidth=2.0, label="IIR causal")
    ax.axvline(0.0, color="#666666", linestyle="--", linewidth=1.0)
    ax.axvline(exp23_artifacts["fir_comp_peak_latency_ms"], color=plotting.COLORS[1], linestyle=":", linewidth=1.3)
    ax.axvline(exp23_artifacts["iir_peak_latency_ms"], color=plotting.COLORS[3], linestyle=":", linewidth=1.3)
    ax.set_title("(D) FIR delay can be corrected; IIR cannot")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude (μV)")
    ax.set_xlim(-200.0, 800.0)
    ax.legend(loc="lower right")
    ax.text(
        0.03,
        0.96,
        f"FIR fixed delay: {exp23_metrics['fir_delay_ms']:.0f} ms\n"
        f"Compensated FIR peak: {exp23_metrics['fir_comp_peak_latency_ms']:.0f} ms\n"
        f"IIR peak: {exp23_metrics['iir_peak_latency_ms']:.0f} ms",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.92, "edgecolor": "#BBBBBB"},
    )

    plotting.save_figure(fig, config.FIGURES_DIR / figure_name)
    return figure_name
