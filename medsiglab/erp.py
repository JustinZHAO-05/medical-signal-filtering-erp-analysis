from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .io_utils import channel_index


@dataclass
class ERPResult:
    # Aggregated ERP output plus bookkeeping about how many epochs survived preprocessing.
    epochs: np.ndarray
    mean_erp: np.ndarray
    time_s: np.ndarray
    fz_wave: np.ndarray
    total_kept: int
    total_dropped: int
    block_counts: list[dict[str, int]]


def epoch_targets(
    data: np.ndarray,
    triggers: np.ndarray,
    labels: np.ndarray,
    fs: float,
    tmin: float,
    tmax: float,
    target_label: int = 1,
) -> tuple[np.ndarray, int, int]:
    pre = int(round(abs(tmin) * fs))
    post = int(round(tmax * fs))
    target_triggers = triggers[labels == target_label]
    segments: list[np.ndarray] = []
    dropped = 0
    for sample in target_triggers:
        start = int(sample - pre)
        stop = int(sample + post)
        # Epochs that cross the recording boundary are excluded and counted explicitly.
        if start < 0 or stop > data.shape[1]:
            dropped += 1
            continue
        segments.append(data[:, start:stop])
    if not segments:
        shape = (0, data.shape[0], pre + post)
        return np.empty(shape), 0, dropped
    epochs = np.stack(segments, axis=0)
    return epochs, epochs.shape[0], dropped


def rereference_epochs(epochs: np.ndarray, channel_names: np.ndarray, ref_chans: tuple[str, ...]) -> np.ndarray:
    ref_indices = [channel_index(channel_names, ref) for ref in ref_chans]
    # The lab uses the average of TP7/TP8 as the mastoid reference.
    ref_mean = np.mean(epochs[:, ref_indices, :], axis=1, keepdims=True)
    return epochs - ref_mean


def baseline_correct_epochs(epochs: np.ndarray, fs: float, tmin: float, baseline: tuple[float, float]) -> np.ndarray:
    start = int(round((baseline[0] - tmin) * fs))
    stop = int(round((baseline[1] - tmin) * fs))
    # Baseline subtraction is done per epoch and per channel before averaging.
    baseline_mean = np.mean(epochs[:, :, start:stop], axis=-1, keepdims=True)
    return epochs - baseline_mean


def process_erp(
    filtered_blocks: list[np.ndarray],
    trigger_positions: np.ndarray,
    class_labels: np.ndarray,
    channel_names: np.ndarray,
    fs: float,
    tmin: float,
    tmax: float,
    baseline: tuple[float, float],
    ref_chans: tuple[str, ...],
    fz_name: str,
) -> ERPResult:
    epoch_batches: list[np.ndarray] = []
    counts: list[dict[str, int]] = []
    for block_index, block in enumerate(filtered_blocks):
        # Triggers and labels are still kept blockwise until all valid target epochs are collected.
        epochs, kept, dropped = epoch_targets(
            block,
            trigger_positions[block_index],
            class_labels[block_index],
            fs=fs,
            tmin=tmin,
            tmax=tmax,
        )
        if kept:
            epochs = rereference_epochs(epochs, channel_names, ref_chans)
            epochs = baseline_correct_epochs(epochs, fs=fs, tmin=tmin, baseline=baseline)
            epoch_batches.append(epochs)
        counts.append({"kept": kept, "dropped": dropped})
    if not epoch_batches:
        raise RuntimeError("No epochs survived preprocessing.")
    epochs_all = np.concatenate(epoch_batches, axis=0)
    mean_erp = np.mean(epochs_all, axis=0)
    n_time = mean_erp.shape[1]
    time_s = np.arange(n_time) / fs + tmin
    fz_wave = mean_erp[channel_index(channel_names, fz_name)]
    return ERPResult(
        epochs=epochs_all,
        mean_erp=mean_erp,
        time_s=time_s,
        fz_wave=fz_wave,
        total_kept=int(sum(item["kept"] for item in counts)),
        total_dropped=int(sum(item["dropped"] for item in counts)),
        block_counts=counts,
    )


def process_erp_blockwise(
    blocks: list[np.ndarray],
    trigger_positions: np.ndarray,
    class_labels: np.ndarray,
    channel_names: np.ndarray,
    fs: float,
    tmin: float,
    tmax: float,
    baseline: tuple[float, float],
    ref_chans: tuple[str, ...],
    fz_name: str,
    filter_fn,
) -> ERPResult:
    epoch_batches: list[np.ndarray] = []
    counts: list[dict[str, int]] = []
    for block_index, block in enumerate(blocks):
        # Some experiments compare multiple filters on the same raw data, so filtering is injected
        # as a callback rather than hard-coded here.
        filtered = filter_fn(block_index, block)
        epochs, kept, dropped = epoch_targets(
            filtered,
            trigger_positions[block_index],
            class_labels[block_index],
            fs=fs,
            tmin=tmin,
            tmax=tmax,
        )
        if kept:
            epochs = rereference_epochs(epochs, channel_names, ref_chans)
            epochs = baseline_correct_epochs(epochs, fs=fs, tmin=tmin, baseline=baseline)
            epoch_batches.append(epochs)
        counts.append({"kept": kept, "dropped": dropped})
    if not epoch_batches:
        raise RuntimeError("No epochs survived preprocessing.")
    epochs_all = np.concatenate(epoch_batches, axis=0)
    mean_erp = np.mean(epochs_all, axis=0)
    n_time = mean_erp.shape[1]
    time_s = np.arange(n_time) / fs + tmin
    fz_wave = mean_erp[channel_index(channel_names, fz_name)]
    return ERPResult(
        epochs=epochs_all,
        mean_erp=mean_erp,
        time_s=time_s,
        fz_wave=fz_wave,
        total_kept=int(sum(item["kept"] for item in counts)),
        total_dropped=int(sum(item["dropped"] for item in counts)),
        block_counts=counts,
    )
