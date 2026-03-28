from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import config


COLORS = [
    "#1F3A5F",
    "#E68613",
    "#7B3294",
    "#D7191C",
    "#2E8B57",
    "#8C564B",
]


def setup_style() -> None:
    # Keep a single visual style across all experiment figures and the final report.
    plt.rcParams.update(
        {
            "figure.dpi": config.PLOT_DPI,
            "savefig.dpi": config.PLOT_DPI,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "axes.facecolor": "#FAFAFA",
            "font.family": "DejaVu Sans",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
        }
    )


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _trim_group_delay(group_delay: np.ndarray) -> tuple[float, float]:
    finite = group_delay[np.isfinite(group_delay)]
    if finite.size == 0:
        return -1.0, 1.0
    minimum = float(np.min(finite))
    maximum = float(np.max(finite))
    span = maximum - minimum
    center = float(np.median(finite))
    scale = max(abs(center), 1.0)
    # Nearly constant-delay FIR curves need a fixed pad, otherwise matplotlib collapses the axis.
    if span < 1e-3 * scale:
        pad = max(1.0, 0.1 * scale)
        return center - pad, center + pad
    lower = minimum - max(1.0, 0.05 * span)
    upper = maximum + max(1.0, 0.08 * span)
    return lower, upper


def _focused_group_delay(
    response: dict[str, np.ndarray],
    focus_band: tuple[float, float] | None,
    mag_floor_db: float | None,
) -> np.ndarray:
    group_delay = np.asarray(response["group_delay_ms"], dtype=float).copy()
    mask = np.isfinite(group_delay)
    if focus_band is not None:
        freq = response["freq_hz"]
        mask &= (freq >= focus_band[0]) & (freq <= focus_band[1])
    if mag_floor_db is not None:
        # Group delay is only meaningful where the response magnitude is still in the effective band.
        mask &= response["magnitude_db"] >= mag_floor_db
    group_delay[~mask] = np.nan
    return group_delay


def _group_identical_curves(items: list[dict], curves: list[np.ndarray], atol: float = 1e-9, rtol: float = 1e-7) -> list[dict]:
    groups: list[dict] = []
    for item, curve in zip(items, curves):
        matched = False
        for group in groups:
            # Some FIR designs share the exact same constant delay curve and should be labeled once.
            if np.allclose(group["curve"], curve, equal_nan=True, atol=atol, rtol=rtol):
                group["labels"].append(item["label"])
                matched = True
                break
        if not matched:
            groups.append(
                {
                    "labels": [item["label"]],
                    "curve": curve,
                    "color": item.get("color"),
                }
            )
    return groups


def _is_constant_curve(curve: np.ndarray) -> tuple[bool, float]:
    finite = curve[np.isfinite(curve)]
    if finite.size == 0:
        return False, 0.0
    mean_value = float(np.mean(finite))
    span = float(np.max(finite) - np.min(finite))
    tolerance = max(0.5, 1e-3 * max(abs(mean_value), 1.0))
    return span <= tolerance, mean_value


def plot_filter_responses(
    items: list[dict],
    title: str,
    path: Path,
    xlim: tuple[float, float],
    mag_ylim: tuple[float, float] = (-120.0, 5.0),
    group_delay_focus_band: tuple[float, float] | None = None,
    group_delay_mag_floor_db: float | None = None,
    disable_offset_text: bool = True,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 10.0), sharex=True)
    focused_group_delays = []
    for index, item in enumerate(items):
        color = item.get("color", COLORS[index % len(COLORS)])
        response = item["response"]
        focused_group_delay = _focused_group_delay(
            response,
            focus_band=group_delay_focus_band,
            mag_floor_db=group_delay_mag_floor_db,
        )
        focused_group_delays.append(focused_group_delay)
        axes[0].plot(response["freq_hz"], response["magnitude_db"], color=color, linewidth=2.0, label=item["label"])
        axes[1].plot(response["freq_hz"], response["phase_rad"], color=color, linewidth=1.8, label=item["label"])
    axes[0].set_title(title)
    axes[0].set_ylabel("Magnitude (dB)")
    axes[0].set_ylim(*mag_ylim)
    axes[1].set_ylabel("Phase (rad)")
    axes[2].set_ylabel("Group Delay (ms)")
    axes[2].set_xlabel("Frequency (Hz)")
    axes[2].set_xlim(*xlim)
    lower, upper = _trim_group_delay(np.concatenate(focused_group_delays))
    axes[2].set_ylim(lower, upper)
    if disable_offset_text:
        axes[2].ticklabel_format(axis="y", style="plain", useOffset=False)
        formatter = axes[2].yaxis.get_major_formatter()
        if hasattr(formatter, "set_useOffset"):
            formatter.set_useOffset(False)
        if hasattr(formatter, "set_scientific"):
            formatter.set_scientific(False)
    for axis in axes[:2]:
        axis.legend(loc="best")

    grouped_curves = _group_identical_curves(items, focused_group_delays)
    handles = []
    labels = []
    annotation_levels: list[float] = []
    annotation_threshold = max(10.0, 0.06 * (upper - lower))
    for group in grouped_curves:
        curve = group["curve"]
        finite_mask = np.isfinite(curve)
        if not np.any(finite_mask):
            continue
        color = group["color"] or COLORS[len(handles) % len(COLORS)]
        group_label = " / ".join(group["labels"])
        if len(group["labels"]) > 1:
            group_label += " (overlap)"
        line, = axes[2].plot(
            items[0]["response"]["freq_hz"],
            curve,
            color=color,
            linewidth=2.2,
            label=group_label,
        )
        handles.append(line)
        labels.append(group_label)
        is_constant, mean_value = _is_constant_curve(curve)
        if is_constant:
            end_index = int(np.where(finite_mask)[0][-1])
            x_end = float(items[0]["response"]["freq_hz"][end_index])
            if len(group["labels"]) > 1:
                annotation = f"{len(group['labels'])} curves overlap at {mean_value:.0f} ms"
            else:
                annotation = f"{mean_value:.0f} ms"
            nearby_levels = [existing for existing in annotation_levels if abs(mean_value - existing) < annotation_threshold]
            close_count = len(nearby_levels)
            y_offset = 0
            if close_count:
                if any(existing > mean_value for existing in nearby_levels):
                    y_offset = -10 * close_count
                else:
                    y_offset = 10 * close_count
            annotation_levels.append(mean_value)
            axes[2].annotate(
                annotation,
                xy=(x_end, mean_value),
                xytext=(6, y_offset),
                textcoords="offset points",
                color=color,
                fontsize=9,
                va="center",
            )
    if handles:
        axes[2].legend(handles, labels, loc="best")
    save_figure(fig, path)


def plot_signal_overlays(
    x: np.ndarray,
    series: list[dict],
    title: str,
    xlabel: str,
    ylabel: str,
    path: Path,
    xlim: tuple[float, float] | None = None,
    vlines: list[float] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    for index, item in enumerate(series):
        ax.plot(x, item["y"], linewidth=2.0, color=item.get("color", COLORS[index % len(COLORS)]), label=item["label"])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xlim is not None:
        ax.set_xlim(*xlim)
    if vlines:
        for value in vlines:
            ax.axvline(value, color="#666666", linestyle="--", linewidth=1.0)
    ax.legend(loc="best")
    save_figure(fig, path)


def plot_four_panel(
    panels: list[dict],
    path: Path,
    figsize: tuple[float, float] = (12.0, 8.5),
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    for axis, panel in zip(axes.flatten(), panels):
        for index, item in enumerate(panel["series"]):
            axis.plot(
                panel["x"],
                item["y"],
                linewidth=item.get("linewidth", 2.0),
                color=item.get("color", COLORS[index % len(COLORS)]),
                linestyle=item.get("linestyle", "-"),
                label=item["label"],
            )
        axis.set_title(panel["title"])
        axis.set_xlabel(panel["xlabel"])
        axis.set_ylabel(panel["ylabel"])
        if panel.get("xlim") is not None:
            axis.set_xlim(*panel["xlim"])
        if panel.get("ylim") is not None:
            axis.set_ylim(*panel["ylim"])
        for value in panel.get("vlines", []):
            axis.axvline(value, color="#666666", linestyle="--", linewidth=1.0)
        if panel.get("legend", True):
            axis.legend(loc=panel.get("legend_loc", "best"))
    save_figure(fig, path)
