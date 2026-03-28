from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from medsiglab import config, erp, filtering, io_utils, plotting, reporting
from scripts.pipeline import figures, shared


def run_part2_exp1() -> tuple[dict, dict]:
    fs = 1000.0
    wp, ws, gpass, gstop = 40.0, 60.0, 1.0, 50.0

    def lowpass_meets(model: filtering.FilterModel) -> bool:
        metrics = filtering.actual_lowpass_metrics(filtering.response_from_model(model), passband_end=wp, stopband_start=ws)
        return metrics["passband_ripple_db"] <= gpass and metrics["stopband_attenuation_db"] >= gstop

    # Each method is searched for the shortest odd tap length that still satisfies the same spec.
    window_model = filtering.search_min_odd_taps(
        lambda taps: filtering.fir_window(taps, cutoff=50.0, fs=fs, window="hamming"),
        lowpass_meets,
        start=31,
        max_taps=2001,
    )
    freq_model = filtering.search_min_odd_taps(
        lambda taps: filtering.fir_frequency_sampling(taps, fs=fs, freq=[0.0, wp, ws, fs / 2.0], gain=[1.0, 1.0, 0.0, 0.0]),
        lowpass_meets,
        start=3001,
        max_taps=7001,
    )
    eq_model = filtering.search_min_odd_taps(
        lambda taps: filtering.fir_equiripple_lowpass(taps, fs=fs, passband_end=wp, stopband_start=ws, rp_db=gpass, rs_db=gstop),
        lowpass_meets,
        start=31,
        max_taps=1001,
    )
    models = [("Window-Hamming", window_model), ("Frequency Sampling", freq_model), ("Equiripple", eq_model)]
    rows = []
    plot_items = []
    designs = []
    for label, model in models:
        response = filtering.response_from_model(model)
        metrics = filtering.actual_lowpass_metrics(response, passband_end=wp, stopband_start=ws)
        gd_samples = (model.numtaps - 1) / 2
        rows.append(
            {
                "方法": label,
                "最短taps": model.numtaps,
                "通带波纹/dB": metrics["passband_ripple_db"],
                "阻带衰减/dB": metrics["stopband_attenuation_db"],
                "固定群时延/样本": gd_samples,
                "固定群时延/ms": gd_samples * 1000.0 / fs,
            }
        )
        plot_items.append({"label": label, "response": response})
        designs.append({"label": label, "response": response})
    reporting.save_table(pd.DataFrame(rows), "part2-exp1-summary")
    figure_name = figures.render_part2_exp1(plot_items)
    return {
        "figure": figure_name,
        "table": shared.table_input_path("part2-exp1-summary"),
        "rows": rows,
    }, {"responses": designs}


def run_part2_exp2() -> tuple[dict, dict]:
    fs = 1000.0
    windows = ["bartlett", "hann", "hamming", "blackman"]
    rows_window = []
    plot_items_window = []
    for window in windows:
        # This block keeps the tap count fixed so only the window shape changes.
        model = filtering.fir_window(61, cutoff=50.0, fs=fs, window=window)
        response = filtering.response_from_model(model)
        metrics = filtering.actual_lowpass_metrics(response, passband_end=40.0, stopband_start=60.0)
        rows_window.append(
            {
                "窗函数": window,
                "通带波纹/dB": metrics["passband_ripple_db"],
                "阻带衰减/dB": metrics["stopband_attenuation_db"],
                "过渡带宽/Hz": metrics["transition_width_hz"],
                "固定群时延/样本": 30.0,
                "固定群时延/ms": 30.0,
            }
        )
        plot_items_window.append({"label": window, "response": response})
    reporting.save_table(pd.DataFrame(rows_window), "part2-exp2-window-summary")
    figure_window = figures.render_part2_exp2_window(plot_items_window)

    rows_length = []
    plot_items_length = []
    for numtaps in (31, 61, 121):
        # This block keeps the Hamming window fixed so only the implementation length changes.
        model = filtering.fir_window(numtaps, cutoff=50.0, fs=fs, window="hamming")
        response = filtering.response_from_model(model)
        metrics = filtering.actual_lowpass_metrics(response, passband_end=40.0, stopband_start=60.0)
        gd_samples = (numtaps - 1) / 2
        rows_length.append(
            {
                "taps": numtaps,
                "通带波纹/dB": metrics["passband_ripple_db"],
                "阻带衰减/dB": metrics["stopband_attenuation_db"],
                "过渡带宽/Hz": metrics["transition_width_hz"],
                "固定群时延/样本": gd_samples,
                "固定群时延/ms": gd_samples * 1000.0 / fs,
                "实现代价/乘加每样本": numtaps,
            }
        )
        plot_items_length.append({"label": f"{numtaps} taps", "response": response})
    reporting.save_table(pd.DataFrame(rows_length), "part2-exp2-length-summary")
    figure_length = figures.render_part2_exp2_length(plot_items_length)
    return {
        "figure_window": figure_window,
        "figure_length": figure_length,
        "table_window": shared.table_input_path("part2-exp2-window-summary"),
        "table_length": shared.table_input_path("part2-exp2-length-summary"),
        "window_rows": rows_window,
        "length_rows": rows_length,
    }, {}


def run_part2_exp3(dataset: io_utils.ERPDataset) -> tuple[dict, dict]:
    fs = config.FIR_ERP_FS
    resampled_blocks = [io_utils.resample_block(block, dataset.fs, fs) for block in dataset.blocks]
    scaled_triggers = io_utils.rescale_triggers(dataset.trigger_positions, dataset.fs, fs)
    # The FIR bandpass is assembled from narrow high-pass and low-pass equiripple stages, which is
    # numerically more stable here than a single direct design with the same low cutoff.
    fir_hp_model = filtering.fir_equiripple_highpass(
        3601,
        fs=fs,
        stopband_end=0.5,
        passband_start=1.0,
        rp_db=1.0,
        rs_db=40.0,
    )
    fir_lp_model = filtering.fir_equiripple_lowpass(
        201,
        fs=fs,
        passband_end=40.0,
        stopband_start=50.0,
        rp_db=1.0,
        rs_db=40.0,
    )
    fir_model = filtering.fir_from_coefficients(
        "Equiripple FIR Bandpass",
        fs=fs,
        kind="bandpass",
        coefficients=np.convolve(fir_hp_model.b, fir_lp_model.b),
    )
    iir_model = filtering.butter_sos("bandpass", order=4, cutoff=(1.0, 40.0), fs=fs)
    fir_response = filtering.response_from_model(fir_model, worN=16384)
    iir_response = filtering.response_from_model(iir_model, worN=16384)
    fir_metrics = filtering.actual_bandpass_metrics(fir_response, passband=(1.0, 40.0), low_stop_end=0.5, high_stop_start=50.0)
    iir_metrics = filtering.actual_bandpass_metrics(iir_response, passband=(1.0, 40.0), low_stop_end=0.5, high_stop_start=50.0)
    if not (
        fir_metrics["passband_ripple_db"] <= 1.0
        and fir_metrics["low_stop_attenuation_db"] >= 40.0
        and fir_metrics["high_stop_attenuation_db"] >= 40.0
    ):
        raise RuntimeError(
            "Part-II Experiment 3 FIR bandpass failed the composite 1 dB / 40 dB specification: "
            f"{fir_metrics}"
        )
    # Both filters are applied causally because this experiment compares delay behavior explicitly.
    fir_filtered_blocks = [filtering.apply_model(fir_model, block, zero_phase=False) for block in resampled_blocks]
    iir_filtered_blocks = [filtering.apply_model(iir_model, block, zero_phase=False) for block in resampled_blocks]
    delay_samples = int((fir_model.numtaps - 1) / 2)
    delay_ms = delay_samples * 1000.0 / fs
    # FIR delay compensation is implemented by shifting the epoch trigger, not by relabeling the x-axis.
    shifted_triggers = np.asarray(scaled_triggers, dtype=int) + delay_samples

    fir_erp = erp.process_erp(
        fir_filtered_blocks,
        scaled_triggers,
        dataset.class_labels,
        dataset.channel_names,
        fs=fs,
        tmin=config.EPOCH_TMIN,
        tmax=config.EPOCH_TMAX,
        baseline=config.BASELINE,
        ref_chans=config.REF_CHANS,
        fz_name=config.FZ_NAME,
    )
    fir_comp_erp = erp.process_erp(
        fir_filtered_blocks,
        shifted_triggers,
        dataset.class_labels,
        dataset.channel_names,
        fs=fs,
        tmin=config.EPOCH_TMIN,
        tmax=config.EPOCH_TMAX,
        baseline=config.BASELINE,
        ref_chans=config.REF_CHANS,
        fz_name=config.FZ_NAME,
    )
    iir_erp = erp.process_erp(
        iir_filtered_blocks,
        scaled_triggers,
        dataset.class_labels,
        dataset.channel_names,
        fs=fs,
        tmin=config.EPOCH_TMIN,
        tmax=config.EPOCH_TMAX,
        baseline=config.BASELINE,
        ref_chans=config.REF_CHANS,
        fz_name=config.FZ_NAME,
    )

    fir_peak_amp, fir_peak_latency = shared.positive_peak(fir_erp.time_s, fir_erp.fz_wave, (0.25, 0.65))
    fir_comp_peak_amp, fir_comp_peak_latency = shared.positive_peak(fir_comp_erp.time_s, fir_comp_erp.fz_wave, (0.25, 0.65))
    iir_peak_amp, iir_peak_latency = shared.positive_peak(iir_erp.time_s, iir_erp.fz_wave, (0.25, 0.65))
    reporting.save_table(
        pd.DataFrame(
            [
                {
                    "滤波器": "FIR Equiripple",
                    "taps/阶数": fir_model.numtaps,
                    "固定延迟/样本(FIR)": delay_samples,
                    "群时延指标/ms": delay_ms,
                    "通带波纹/dB": fir_metrics["passband_ripple_db"],
                    "低端阻带衰减/dB": fir_metrics["low_stop_attenuation_db"],
                    "高端阻带衰减/dB": fir_metrics["high_stop_attenuation_db"],
                },
                {
                    "滤波器": "IIR Butterworth",
                    "taps/阶数": iir_model.order,
                    "固定延迟/样本(FIR)": "--",
                    "群时延指标/ms": f"{iir_metrics['group_delay_mean_ms']:.3f} ± {iir_metrics['group_delay_std_ms']:.3f}",
                    "通带波纹/dB": iir_metrics["passband_ripple_db"],
                    "低端阻带衰减/dB": iir_metrics["low_stop_attenuation_db"],
                    "高端阻带衰减/dB": iir_metrics["high_stop_attenuation_db"],
                },
            ]
        ),
        "part2-exp3-filter-summary",
    )
    reporting.save_table(
        pd.DataFrame(
            [
                {"波形": "FIR uncompensated", "保留试次": fir_erp.total_kept, "峰值/uV": fir_peak_amp, "峰值潜伏期/ms": fir_peak_latency},
                {"波形": "FIR compensated", "保留试次": fir_comp_erp.total_kept, "峰值/uV": fir_comp_peak_amp, "峰值潜伏期/ms": fir_comp_peak_latency},
                {"波形": "IIR causal", "保留试次": iir_erp.total_kept, "峰值/uV": iir_peak_amp, "峰值潜伏期/ms": iir_peak_latency},
            ]
        ),
        "part2-exp3-erp-summary",
    )
    figure_response = figures.render_part2_exp3_filter_response(fir_response, iir_response)
    figure_erp = figures.render_part2_exp3_erp(
        time_ms=fir_erp.time_s * 1000.0,
        fir_uncomp_wave=fir_erp.fz_wave,
        fir_comp_time_ms=fir_comp_erp.time_s * 1000.0,
        fir_comp_wave=fir_comp_erp.fz_wave,
        iir_wave=iir_erp.fz_wave,
        fir_comp_peak_latency_ms=fir_comp_peak_latency,
        iir_peak_latency_ms=iir_peak_latency,
    )
    return {
        "figure_response": figure_response,
        "figure_erp": figure_erp,
        "table_filter": shared.table_input_path("part2-exp3-filter-summary"),
        "table_erp": shared.table_input_path("part2-exp3-erp-summary"),
        "fir_numtaps": fir_model.numtaps,
        "fir_hp_numtaps": fir_hp_model.numtaps,
        "fir_lp_numtaps": fir_lp_model.numtaps,
        "fir_delay_samples": delay_samples,
        "fir_delay_ms": delay_ms,
        "iir_group_delay_mean_ms": iir_metrics["group_delay_mean_ms"],
        "iir_group_delay_std_ms": iir_metrics["group_delay_std_ms"],
        "fir_peak_latency_ms": fir_peak_latency,
        "fir_comp_peak_latency_ms": fir_comp_peak_latency,
        "fir_uncomp_kept": fir_erp.total_kept,
        "fir_uncomp_dropped": fir_erp.total_dropped,
        "fir_comp_kept": fir_comp_erp.total_kept,
        "fir_comp_dropped": fir_comp_erp.total_dropped,
        "iir_kept": iir_erp.total_kept,
        "iir_dropped": iir_erp.total_dropped,
        "iir_peak_latency_ms": iir_peak_latency,
    }, {
        "time_ms": fir_comp_erp.time_s * 1000.0,
        "fir_uncomp_wave": fir_erp.fz_wave,
        "fir_comp_wave": fir_comp_erp.fz_wave,
        "iir_wave": iir_erp.fz_wave,
        "fir_comp_peak_latency_ms": fir_comp_peak_latency,
        "iir_peak_latency_ms": iir_peak_latency,
    }


def run_suite(dataset: io_utils.ERPDataset | None = None, experiment: str = "all") -> tuple[dict, dict]:
    selected = ["exp1", "exp2", "exp3"] if experiment == "all" else [experiment]
    metrics: dict[str, dict] = {}
    artifacts: dict[str, dict] = {}
    for key in selected:
        if key == "exp1":
            metrics[key], artifacts[key] = run_part2_exp1()
        elif key == "exp2":
            metrics[key], artifacts[key] = run_part2_exp2()
        elif key == "exp3":
            if dataset is None:
                raise ValueError("Part-II experiment 3 requires the ERP dataset.")
            metrics[key], artifacts[key] = run_part2_exp3(dataset)
        else:
            raise ValueError(f"Unsupported Part-II experiment: {key}")
    return metrics, artifacts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run Part-II experiments only.")
    parser.add_argument("--experiment", choices=["all", "exp1", "exp2", "exp3"], default="all")
    args = parser.parse_args(argv)

    io_utils.ensure_output_dirs()
    plotting.setup_style()
    dataset = io_utils.load_sub7a_dataset() if args.experiment in {"all", "exp3"} else None
    metrics, _ = run_suite(dataset=dataset, experiment=args.experiment)
    payload: dict[str, dict] = {"part2": metrics}
    if dataset is not None:
        payload["data"], _ = shared.build_data_summary(dataset)
    json_path = config.REPORT_OUTPUT_DIR / ("part2_metrics.json" if args.experiment == "all" else f"part2_{args.experiment}_metrics.json")
    reporting.write_json(payload, json_path)
    print(json.dumps({"metrics_json": str(json_path), "experiments": list(metrics.keys())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
