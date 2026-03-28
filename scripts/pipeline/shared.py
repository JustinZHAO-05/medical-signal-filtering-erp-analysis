from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from medsiglab import config, io_utils, reporting


def positive_peak(time_s: np.ndarray, waveform: np.ndarray, window: tuple[float, float]) -> tuple[float, float]:
    # Peak extraction is always windowed so the metric tracks the intended ERP component only.
    mask = (time_s >= window[0]) & (time_s <= window[1])
    segment = waveform[mask]
    segment_time = time_s[mask]
    index = int(np.argmax(segment))
    return float(segment[index]), float(segment_time[index] * 1000.0)


def negative_peak(time_s: np.ndarray, waveform: np.ndarray, window: tuple[float, float]) -> tuple[float, float]:
    # Negative extrema are measured with the same windowing rule for consistency across tables.
    mask = (time_s >= window[0]) & (time_s <= window[1])
    segment = waveform[mask]
    segment_time = time_s[mask]
    index = int(np.argmin(segment))
    return float(segment[index]), float(segment_time[index] * 1000.0)


def area_under_curve(time_s: np.ndarray, waveform: np.ndarray, window: tuple[float, float]) -> float:
    mask = (time_s >= window[0]) & (time_s <= window[1])
    return float(np.trapezoid(waveform[mask], time_s[mask]))


def moving_average(signal_1d: np.ndarray, window_samples: int) -> np.ndarray:
    # A long moving average is used only to visualize slow drift, not to create ERP results.
    kernel = np.ones(window_samples) / window_samples
    return np.convolve(signal_1d, kernel, mode="same")


def table_input_path(stem: str) -> str:
    return f"output/tables/{stem}.tex"


def save_metrics_json(metrics: dict, path: Path | None = None) -> Path:
    target = path or (config.REPORT_OUTPUT_DIR / "metrics.json")
    reporting.write_json(metrics, target)
    return target


def build_data_summary(dataset: io_utils.ERPDataset) -> tuple[dict, pd.DataFrame]:
    rows = []
    target_counts = []
    for block_index, block in enumerate(dataset.blocks):
        # The trigger-spacing mode provides a quick sanity check for the effective sampling rate.
        block_targets = int(np.sum(dataset.class_labels[block_index] == 1))
        target_counts.append(block_targets)
        rows.append(
            {
                "Block": f"Block {block_index + 1}",
                "原始长度/样本": int(block.shape[1]),
                "目标刺激数": block_targets,
                "非目标刺激数": int(np.sum(dataset.class_labels[block_index] == 2)),
                "触发间隔众数/样本": int(pd.Series(np.diff(dataset.trigger_positions[block_index])).mode().iloc[0]),
            }
        )
    summary = {
        "original_fs": dataset.fs,
        "n_channels": int(dataset.blocks[0].shape[0]),
        "block_lengths": [int(block.shape[1]) for block in dataset.blocks],
        "target_counts": target_counts,
        "total_targets": int(sum(target_counts)),
        "trigger_mode_samples": int(pd.Series(np.diff(dataset.trigger_positions[0])).mode().iloc[0]),
    }
    return summary, pd.DataFrame(rows)
