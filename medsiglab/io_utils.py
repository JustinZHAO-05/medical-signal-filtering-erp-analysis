from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy import io, signal

from . import config


@dataclass
class ERPDataset:
    # Two continuous EEG blocks plus their trigger/label annotations.
    blocks: list[np.ndarray]
    class_labels: np.ndarray
    trigger_positions: np.ndarray
    channel_names: np.ndarray
    fs: float


def ensure_output_dirs() -> None:
    for path in (
        config.OUTPUT_DIR,
        config.FIGURES_DIR,
        config.TABLES_DIR,
        config.REPORT_OUTPUT_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def read_loc_file(filepath: Path) -> np.ndarray:
    channel_names: list[str] = []
    with filepath.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) >= 4:
                # The provided .loc file stores the channel name in the 4th column.
                channel_names.append(parts[3])
    return np.asarray(channel_names)


def load_sub7a_dataset(
    mat_path: Path | None = None,
    loc_path: Path | None = None,
    fs: float = config.ORIGINAL_FS,
) -> ERPDataset:
    mat_path = mat_path or config.SUB7A_PATH
    loc_path = loc_path or config.LOC_PATH
    raw = io.loadmat(mat_path)
    # The dataset is distributed as two continuous blocks rather than pre-cut epochs.
    blocks = [np.asarray(raw["EEGdata1"], dtype=float), np.asarray(raw["EEGdata2"], dtype=float)]
    labels = np.asarray(raw["class_labels"], dtype=int)
    triggers = np.asarray(raw["trigger_positions"], dtype=int)
    channel_names = read_loc_file(loc_path)
    return ERPDataset(
        blocks=blocks,
        class_labels=labels,
        trigger_positions=triggers,
        channel_names=channel_names,
        fs=fs,
    )


def resample_block(data: np.ndarray, old_fs: float, new_fs: float) -> np.ndarray:
    if old_fs == new_fs:
        return np.asarray(data, dtype=float)
    # Polyphase resampling keeps the ERP pipeline numerically stable and efficient.
    ratio = Fraction(str(new_fs / old_fs)).limit_denominator()
    return signal.resample_poly(np.asarray(data, dtype=float), ratio.numerator, ratio.denominator, axis=-1)


def rescale_triggers(triggers: np.ndarray, old_fs: float, new_fs: float) -> np.ndarray:
    if old_fs == new_fs:
        return np.asarray(triggers, dtype=int)
    # Trigger indices must be rescaled with the same sampling-rate ratio as the signal.
    scaled = np.rint(np.asarray(triggers, dtype=float) * new_fs / old_fs).astype(int)
    return np.maximum(scaled, 0)


def channel_index(channel_names: np.ndarray, name: str) -> int:
    indices = np.where(channel_names == name)[0]
    if indices.size == 0:
        raise KeyError(f"Channel {name!r} not found in montage.")
    return int(indices[0])
