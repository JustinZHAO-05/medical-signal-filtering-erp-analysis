from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from medsiglab import config, erp, filtering, io_utils, plotting, reporting
from scripts.pipeline import figures, shared


def run_part1_exp1() -> tuple[dict, dict]:
    fs = 1000.0
    wp, ws, gpass, gstop = 40.0, 60.0, 1.0, 40.0
    families = ["Butterworth", "Chebyshev-I", "Chebyshev-II", "Elliptic"]
    rows = []
    plot_items = []
    order_map = {}
    for family in families:
        # All four IIR families are evaluated under exactly the same amplitude specification.
        model = filtering.design_iir_lowpass(family, fs=fs, wp=wp, ws=ws, gpass=gpass, gstop=gstop)
        response = filtering.response_from_model(model)
        metrics = filtering.actual_lowpass_metrics(response, passband_end=wp, stopband_start=ws)
        pass_mask = filtering.passband_mask(response["freq_hz"], (0.0, wp))
        gd_ms = response["group_delay_ms"][pass_mask]
        rows.append(
            {
                "滤波器": family,
                "最低阶数": model.order,
                "通带波纹/dB": metrics["passband_ripple_db"],
                "阻带最小衰减/dB": metrics["stopband_attenuation_db"],
                "过渡带宽/Hz": metrics["transition_width_hz"],
                "通带群时延均值/ms": float(np.mean(gd_ms)),
                "通带群时延标准差/ms": float(np.std(gd_ms)),
            }
        )
        plot_items.append({"label": family, "response": response})
        order_map[family] = int(model.order)
    reporting.save_table(pd.DataFrame(rows), "part1-exp1-summary")
    figure_name = figures.render_part1_exp1(plot_items)
    return {
        "figure": figure_name,
        "table": shared.table_input_path("part1-exp1-summary"),
        "rows": rows,
        "orders": order_map,
    }, {"plot_items": plot_items}


def run_part1_exp2() -> tuple[dict, dict]:
    fs = 1000.0
    # A controlled 10 Hz + 50 Hz mixture makes both attenuation and phase distortion visible.
    time_s = np.arange(0.0, 3.0, 1.0 / fs)
    pure10 = np.sin(2.0 * np.pi * 10.0 * time_s)
    pure50 = np.sin(2.0 * np.pi * 50.0 * time_s)
    signal_in = pure10 + pure50
    model = filtering.butter_sos("lowpass", order=4, cutoff=20.0, fs=fs)

    causal_once = filtering.apply_model(model, signal_in, zero_phase=False)
    causal_twice = filtering.apply_model(model, causal_once, zero_phase=False)
    zero_phase = filtering.apply_model(model, signal_in, zero_phase=True)

    # Delay is estimated away from the edges so startup/ending artifacts do not dominate.
    center = slice(int(0.5 * fs), int(2.5 * fs))
    rows = []
    series = {
        "Single causal": causal_once,
        "Repeated causal": causal_twice,
        "Zero phase": zero_phase,
    }
    for label, signal_1d in series.items():
        amp10 = filtering.dominant_fft_amplitude(signal_1d, fs, 10.0)
        amp50 = filtering.dominant_fft_amplitude(signal_1d, fs, 50.0)
        rows.append(
            {
                "方式": label,
                "10 Hz幅值": amp10,
                "50 Hz幅值": amp50,
                "50 Hz抑制/dB": 20.0 * np.log10(max(amp50, 1e-12) / filtering.dominant_fft_amplitude(signal_in, fs, 50.0)),
                "相对10 Hz延迟/ms": filtering.estimate_delay_ms(pure10[center], signal_1d[center], fs),
            }
        )
    reporting.save_table(pd.DataFrame(rows), "part1-exp2-summary")
    spectra = {
        "Input": 2.0 * np.abs(np.fft.rfft(signal_in)) / signal_in.size,
        "Single causal": 2.0 * np.abs(np.fft.rfft(causal_once)) / causal_once.size,
        "Repeated causal": 2.0 * np.abs(np.fft.rfft(causal_twice)) / causal_twice.size,
        "Zero phase": 2.0 * np.abs(np.fft.rfft(zero_phase)) / zero_phase.size,
    }
    figure_name = figures.render_part1_exp2(
        time_s=time_s,
        signal_in=signal_in,
        pure10=pure10,
        causal_once=causal_once,
        causal_twice=causal_twice,
        zero_phase=zero_phase,
        spectra=spectra,
    )
    df = pd.DataFrame(rows)
    return {
        "figure": figure_name,
        "table": shared.table_input_path("part1-exp2-summary"),
        "rows": rows,
        "delay_single_ms": float(df.loc[df["方式"] == "Single causal", "相对10 Hz延迟/ms"].iloc[0]),
        "delay_twice_ms": float(df.loc[df["方式"] == "Repeated causal", "相对10 Hz延迟/ms"].iloc[0]),
        "delay_zero_ms": float(df.loc[df["方式"] == "Zero phase", "相对10 Hz延迟/ms"].iloc[0]),
    }, {
        "time": time_s,
        "pure10": pure10,
        "single": causal_once,
        "zero": zero_phase,
    }


def run_part1_exp3(dataset: io_utils.ERPDataset) -> tuple[dict, dict]:
    fs = config.IIR_ERP_FS
    # The real ERP blocks are first resampled to the Part-I sampling rate required by the task.
    resampled_blocks = [io_utils.resample_block(block, dataset.fs, fs) for block in dataset.blocks]
    fz_idx = io_utils.channel_index(dataset.channel_names, config.FZ_NAME)
    hp_model = filtering.butter_sos("highpass", order=4, cutoff=1.0, fs=fs)
    filtered_blocks = [filtering.apply_model(hp_model, block, zero_phase=True) for block in resampled_blocks]

    drift_rows = []
    for index, (raw_block, filtered_block) in enumerate(zip(resampled_blocks, filtered_blocks), start=1):
        raw_fz = raw_block[fz_idx]
        filtered_fz = filtered_block[fz_idx]
        # A 5 s trend estimate captures slow baseline wander without reacting to transient peaks.
        smooth_window = int(5.0 * fs)
        raw_slow = shared.moving_average(raw_fz, smooth_window)
        filtered_slow = shared.moving_average(filtered_fz, smooth_window)
        drift_rows.append(
            {
                "Block": f"Block {index}",
                "原始慢变范围/uV": float(np.ptp(raw_slow)),
                "高通后慢变范围/uV": float(np.ptp(filtered_slow)),
            }
        )
    reporting.save_table(pd.DataFrame(drift_rows), "part1-exp3-continuous")
    time_block1 = np.arange(resampled_blocks[0].shape[1]) / fs
    time_block2 = np.arange(resampled_blocks[1].shape[1]) / fs
    figure_cont = figures.render_part1_exp3_continuous(
        block1_time=time_block1,
        block2_time=time_block2,
        block1_raw=resampled_blocks[0][fz_idx],
        block2_raw=resampled_blocks[1][fz_idx],
        block1_filtered=filtered_blocks[0][fz_idx],
        block2_filtered=filtered_blocks[1][fz_idx],
    )

    # The synthetic example isolates drift suppression from all other biological variability.
    synth_fs = 1000.0
    synth_t = np.arange(0.0, 3.0, 1.0 / synth_fs)
    drift = np.sin(2.0 * np.pi * 0.2 * synth_t)
    pulse = 2.0 * np.exp(-((synth_t - 1.5) ** 2) / (2.0 * 0.02**2))
    signal_in = drift + pulse
    synth_rows = []
    synth_series = [{"label": "Unfiltered", "y": signal_in, "color": plotting.COLORS[0]}]
    for cutoff, color in zip((0.1, 0.5, 1.0), plotting.COLORS[1:4]):
        model = filtering.butter_sos("highpass", order=4, cutoff=cutoff, fs=synth_fs)
        filtered = filtering.apply_model(model, signal_in, zero_phase=True)
        peak_amp, peak_latency = shared.positive_peak(synth_t, filtered, (1.4, 1.6))
        undershoot, _ = shared.negative_peak(synth_t, filtered, (1.55, 1.9))
        synth_rows.append(
            {
                "截止频率/Hz": cutoff,
                "脉冲峰值/uV": peak_amp,
                "峰值潜伏期/ms": peak_latency,
                "后冲最小值/uV": undershoot,
            }
        )
        synth_series.append({"label": f"{cutoff:.1f} Hz HP", "y": filtered, "color": color})
    reporting.save_table(pd.DataFrame(synth_rows), "part1-exp3-synthetic")
    figure_synth = figures.render_part1_exp3_synthetic(synth_t=synth_t, synth_series=synth_series, drift=drift, pulse=pulse)
    return {
        "figure_continuous": figure_cont,
        "figure_synthetic": figure_synth,
        "table_continuous": shared.table_input_path("part1-exp3-continuous"),
        "table_synthetic": shared.table_input_path("part1-exp3-synthetic"),
        "drift_rows": drift_rows,
        "synthetic_rows": synth_rows,
    }, {"synthetic_time": synth_t, "synthetic_series": synth_series}


def run_part1_exp4(dataset: io_utils.ERPDataset) -> tuple[dict, dict]:
    fs = config.IIR_ERP_FS
    resampled_blocks = [io_utils.resample_block(block, dataset.fs, fs) for block in dataset.blocks]
    rescaled_triggers = io_utils.rescale_triggers(dataset.trigger_positions, dataset.fs, fs)

    # These four conditions reproduce the high-pass cutoff comparison requested in the task.
    configs = {
        "50 Hz LP only": {"model": filtering.butter_sos("lowpass", order=4, cutoff=50.0, fs=fs), "zero_phase": True},
        "0.1-15 Hz": {"model": filtering.butter_sos("bandpass", order=4, cutoff=(0.1, 15.0), fs=fs), "zero_phase": True},
        "0.5-15 Hz": {"model": filtering.butter_sos("bandpass", order=4, cutoff=(0.5, 15.0), fs=fs), "zero_phase": True},
        "1.0-15 Hz": {"model": filtering.butter_sos("bandpass", order=4, cutoff=(1.0, 15.0), fs=fs), "zero_phase": True},
    }
    cutoff_colors = {
        "50 Hz LP only": plotting.COLORS[0],
        "0.1-15 Hz": plotting.COLORS[1],
        "0.5-15 Hz": plotting.COLORS[2],
        "1.0-15 Hz": plotting.COLORS[3],
    }
    erp_results = {}
    overlay_series = []
    peak_rows = []
    for label, cfg in configs.items():
        # Each condition is processed blockwise so trigger bookkeeping stays aligned with filtering.
        result = erp.process_erp_blockwise(
            resampled_blocks,
            rescaled_triggers,
            dataset.class_labels,
            dataset.channel_names,
            fs=fs,
            tmin=config.EPOCH_TMIN,
            tmax=config.EPOCH_TMAX,
            baseline=config.BASELINE,
            ref_chans=config.REF_CHANS,
            fz_name=config.FZ_NAME,
            filter_fn=lambda _, block, model=cfg["model"], zero_phase=cfg["zero_phase"]: filtering.apply_model(model, block, zero_phase=zero_phase),
        )
        erp_results[label] = result
        overlay_series.append({"label": label, "y": result.fz_wave, "color": cutoff_colors[label]})
        late_amp, late_latency = shared.positive_peak(result.time_s, result.fz_wave, (0.25, 0.65))
        early_min, _ = shared.negative_peak(result.time_s, result.fz_wave, (0.0, 0.25))
        peak_rows.append(
            {
                "条件": label,
                "保留试次": result.total_kept,
                "Pe峰值/uV": late_amp,
                "Pe潜伏期/ms": late_latency,
                "早期最小值/uV": early_min,
                "300-700 ms面积": shared.area_under_curve(result.time_s, result.fz_wave, (0.3, 0.7)),
            }
        )
    reporting.save_table(pd.DataFrame(peak_rows), "part1-exp4-cutoff-summary")
    figure_cutoff = figures.render_part1_exp4_cutoff(
        time_ms=erp_results["50 Hz LP only"].time_s * 1000.0,
        overlay_series=overlay_series,
    )

    # For the order comparison, only the causal high-pass order changes; the 15 Hz lowpass stays fixed.
    lowpass_causal = filtering.butter_sos("lowpass", order=4, cutoff=15.0, fs=fs)
    hp2 = filtering.butter_sos("highpass", order=2, cutoff=2.5, fs=fs)
    hp8 = filtering.butter_sos("highpass", order=8, cutoff=2.5, fs=fs)
    order_models = {"2nd-order HP": hp2, "8th-order HP": hp8}
    order_colors = {"2nd-order HP": plotting.COLORS[0], "8th-order HP": plotting.COLORS[1]}
    order_results = {}
    order_rows = []
    reference_wave = erp_results["50 Hz LP only"].fz_wave
    reference_time = erp_results["50 Hz LP only"].time_s
    for label, hp_model in order_models.items():
        result = erp.process_erp_blockwise(
            resampled_blocks,
            rescaled_triggers,
            dataset.class_labels,
            dataset.channel_names,
            fs=fs,
            tmin=config.EPOCH_TMIN,
            tmax=config.EPOCH_TMAX,
            baseline=config.BASELINE,
            ref_chans=config.REF_CHANS,
            fz_name=config.FZ_NAME,
            filter_fn=lambda _, block, hp_model=hp_model: filtering.apply_model(
                lowpass_causal,
                filtering.apply_model(hp_model, block, zero_phase=False),
                zero_phase=False,
            ),
        )
        order_results[label] = result
        late_amp, late_latency = shared.positive_peak(result.time_s, result.fz_wave, (0.2, 0.6))
        early_negative, _ = shared.negative_peak(result.time_s, result.fz_wave, (0.1, 0.2))
        early_overshoot, _ = shared.positive_peak(result.time_s, result.fz_wave, (0.18, 0.25))
        early_mask = (result.time_s >= 0.0) & (result.time_s <= 0.25)
        # Early-window difference metrics quantify temporal distortion more robustly than a single extremum.
        diff_early = result.fz_wave[early_mask] - reference_wave[early_mask]
        order_rows.append(
            {
                "条件": label,
                "保留试次": result.total_kept,
                "正峰/uV": late_amp,
                "正峰潜伏期/ms": late_latency,
                "早期负偏转/uV": early_negative,
                "早期正过冲/uV": early_overshoot,
                "0-250 ms差异RMS/uV": float(np.sqrt(np.mean(diff_early * diff_early))),
                "0-250 ms差异绝对面积": shared.area_under_curve(reference_time, np.abs(result.fz_wave - reference_wave), (0.0, 0.25)),
            }
        )
    reporting.save_table(pd.DataFrame(order_rows), "part1-exp4-order-summary")
    figure_order = figures.render_part1_exp4_order(
        time_ms=next(iter(order_results.values())).time_s * 1000.0,
        overlay_series=[{"label": key, "y": value.fz_wave, "color": order_colors[key]} for key, value in order_results.items()],
    )
    return {
        "figure_cutoff": figure_cutoff,
        "figure_order": figure_order,
        "table_cutoff": shared.table_input_path("part1-exp4-cutoff-summary"),
        "table_order": shared.table_input_path("part1-exp4-order-summary"),
        "cutoff_rows": peak_rows,
        "order_rows": order_rows,
    }, {"cutoff_results": erp_results}


def run_suite(dataset: io_utils.ERPDataset | None = None, experiment: str = "all") -> tuple[dict, dict]:
    selected = ["exp1", "exp2", "exp3", "exp4"] if experiment == "all" else [experiment]
    metrics: dict[str, dict] = {}
    artifacts: dict[str, dict] = {}
    for key in selected:
        if key == "exp1":
            metrics[key], artifacts[key] = run_part1_exp1()
        elif key == "exp2":
            metrics[key], artifacts[key] = run_part1_exp2()
        elif key == "exp3":
            if dataset is None:
                raise ValueError("Part-I experiment 3 requires the ERP dataset.")
            metrics[key], artifacts[key] = run_part1_exp3(dataset)
        elif key == "exp4":
            if dataset is None:
                raise ValueError("Part-I experiment 4 requires the ERP dataset.")
            metrics[key], artifacts[key] = run_part1_exp4(dataset)
        else:
            raise ValueError(f"Unsupported Part-I experiment: {key}")
    return metrics, artifacts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run Part-I experiments only.")
    parser.add_argument("--experiment", choices=["all", "exp1", "exp2", "exp3", "exp4"], default="all")
    args = parser.parse_args(argv)

    io_utils.ensure_output_dirs()
    plotting.setup_style()
    dataset = io_utils.load_sub7a_dataset() if args.experiment in {"all", "exp3", "exp4"} else None
    metrics, _ = run_suite(dataset=dataset, experiment=args.experiment)
    payload: dict[str, dict] = {"part1": metrics}
    if dataset is not None:
        payload["data"], _ = shared.build_data_summary(dataset)
    json_path = config.REPORT_OUTPUT_DIR / ("part1_metrics.json" if args.experiment == "all" else f"part1_{args.experiment}_metrics.json")
    reporting.write_json(payload, json_path)
    print(json.dumps({"metrics_json": str(json_path), "experiments": list(metrics.keys())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
