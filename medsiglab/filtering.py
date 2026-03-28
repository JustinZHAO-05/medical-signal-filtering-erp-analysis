from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import signal


EPS = 1e-12


@dataclass
class FilterModel:
    name: str
    fs: float
    kind: str
    mode: str
    order: int | None = None
    numtaps: int | None = None
    rp_db: float | None = None
    rs_db: float | None = None
    cutoff: tuple[float, ...] | None = None
    b: np.ndarray | None = None
    a: np.ndarray | None = None
    sos: np.ndarray | None = None


def mag_to_db(magnitude: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(magnitude), EPS))


def ripple_from_db(response_db: np.ndarray) -> float:
    return float(np.max(response_db) - np.min(response_db))


def attenuation_from_db(response_db: np.ndarray) -> float:
    return float(-np.max(response_db))


def response_from_model(model: FilterModel, worN: int = 16384) -> dict[str, np.ndarray]:
    if model.sos is not None:
        w, h = signal.sosfreqz(model.sos, worN=worN, fs=model.fs)
        phase = np.unwrap(np.angle(h))
        omega = 2.0 * np.pi * w / model.fs
    else:
        if model.b is None or model.a is None:
            raise ValueError("Either SOS or BA representation is required.")
        omega, h = signal.freqz(model.b, model.a, worN=worN)
        w = omega * model.fs / (2.0 * np.pi)
        phase = np.unwrap(np.angle(h))
    # Group delay is approximated from the numerical derivative of the unwrapped phase.
    group_delay_samples = -np.gradient(phase, omega)
    return {
        "freq_hz": w,
        "magnitude_db": mag_to_db(h),
        "phase_rad": phase,
        "group_delay_samples": group_delay_samples,
        "group_delay_ms": group_delay_samples * 1000.0 / model.fs,
    }


def passband_mask(freq_hz: np.ndarray, band: tuple[float, float]) -> np.ndarray:
    return (freq_hz >= band[0]) & (freq_hz <= band[1])


def lowpass_stop_mask(freq_hz: np.ndarray, stop_start: float) -> np.ndarray:
    return freq_hz >= stop_start


def highpass_stop_mask(freq_hz: np.ndarray, stop_end: float) -> np.ndarray:
    return freq_hz <= stop_end


def bandpass_stop_masks(
    freq_hz: np.ndarray,
    low_stop_end: float,
    high_stop_start: float,
) -> tuple[np.ndarray, np.ndarray]:
    return freq_hz <= low_stop_end, freq_hz >= high_stop_start


def actual_lowpass_metrics(
    response: dict[str, np.ndarray],
    passband_end: float,
    stopband_start: float,
) -> dict[str, float]:
    freq = response["freq_hz"]
    mag_db = response["magnitude_db"]
    pass_db = mag_db[passband_mask(freq, (0.0, passband_end))]
    stop_db = mag_db[lowpass_stop_mask(freq, stopband_start)]
    pass_last = np.where(mag_db >= -1.0)[0]
    stop_first = np.where((freq >= passband_end) & (mag_db <= -40.0))[0]
    transition_width = float(freq[stop_first[0]] - passband_end) if stop_first.size else float(stopband_start - passband_end)
    return {
        "passband_ripple_db": ripple_from_db(pass_db),
        "stopband_attenuation_db": attenuation_from_db(stop_db),
        "transition_width_hz": transition_width,
        "passband_max_db": float(np.max(pass_db)),
        "passband_min_db": float(np.min(pass_db)),
    }


def actual_bandpass_metrics(
    response: dict[str, np.ndarray],
    passband: tuple[float, float],
    low_stop_end: float,
    high_stop_start: float,
) -> dict[str, float]:
    freq = response["freq_hz"]
    mag_db = response["magnitude_db"]
    pass_db = mag_db[passband_mask(freq, passband)]
    low_stop_mask, high_stop_mask = bandpass_stop_masks(freq, low_stop_end, high_stop_start)
    low_stop_db = mag_db[low_stop_mask]
    high_stop_db = mag_db[high_stop_mask]
    return {
        "passband_ripple_db": ripple_from_db(pass_db),
        "low_stop_attenuation_db": attenuation_from_db(low_stop_db),
        "high_stop_attenuation_db": attenuation_from_db(high_stop_db),
        "group_delay_mean_ms": float(np.mean(response["group_delay_ms"][passband_mask(freq, passband)])),
        "group_delay_std_ms": float(np.std(response["group_delay_ms"][passband_mask(freq, passband)])),
    }


def design_iir_lowpass(
    family: str,
    fs: float,
    wp: float,
    ws: float,
    gpass: float,
    gstop: float,
) -> FilterModel:
    # Each family uses its own order estimator so all designs satisfy the same amplitude spec.
    if family == "Butterworth":
        order, wn = signal.buttord(wp, ws, gpass, gstop, fs=fs)
        sos = signal.butter(order, wn, btype="lowpass", fs=fs, output="sos")
    elif family == "Chebyshev-I":
        order, wn = signal.cheb1ord(wp, ws, gpass, gstop, fs=fs)
        sos = signal.cheby1(order, gpass, wn, btype="lowpass", fs=fs, output="sos")
    elif family == "Chebyshev-II":
        order, wn = signal.cheb2ord(wp, ws, gpass, gstop, fs=fs)
        sos = signal.cheby2(order, gstop, wn, btype="lowpass", fs=fs, output="sos")
    elif family == "Elliptic":
        order, wn = signal.ellipord(wp, ws, gpass, gstop, fs=fs)
        sos = signal.ellip(order, gpass, gstop, wn, btype="lowpass", fs=fs, output="sos")
    else:
        raise ValueError(f"Unsupported IIR family: {family}")
    return FilterModel(
        name=family,
        fs=fs,
        kind="lowpass",
        mode="iir",
        order=int(order),
        rp_db=gpass,
        rs_db=gstop,
        cutoff=(float(wp), float(ws)),
        sos=sos,
    )


def butter_sos(kind: str, order: int, cutoff: float | tuple[float, float], fs: float) -> FilterModel:
    sos = signal.butter(order, cutoff, btype=kind, fs=fs, output="sos")
    return FilterModel(
        name=f"Butterworth {kind}",
        fs=fs,
        kind=kind,
        mode="iir",
        order=order,
        cutoff=(cutoff,) if np.isscalar(cutoff) else tuple(float(x) for x in cutoff),
        sos=sos,
    )


def fir_window(numtaps: int, cutoff: float, fs: float, window: str) -> FilterModel:
    b = signal.firwin(numtaps, cutoff, fs=fs, window=window, pass_zero="lowpass")
    return FilterModel(
        name=f"{window.title()} Window",
        fs=fs,
        kind="lowpass",
        mode="fir",
        numtaps=numtaps,
        cutoff=(cutoff,),
        b=b,
        a=np.array([1.0]),
    )


def fir_frequency_sampling(numtaps: int, fs: float, freq: list[float], gain: list[float]) -> FilterModel:
    b = signal.firwin2(numtaps, freq, gain, fs=fs)
    return FilterModel(
        name="Frequency Sampling",
        fs=fs,
        kind="lowpass",
        mode="fir",
        numtaps=numtaps,
        cutoff=(float(freq[1]), float(freq[2])),
        b=b,
        a=np.array([1.0]),
    )


def fir_equiripple_lowpass(
    numtaps: int,
    fs: float,
    passband_end: float,
    stopband_start: float,
    rp_db: float,
    rs_db: float,
) -> FilterModel:
    # Convert ripple/attenuation in dB into linear-domain deviations for remez weighting.
    delta_p = (10.0 ** (rp_db / 20.0) - 1.0) / (10.0 ** (rp_db / 20.0) + 1.0)
    delta_s = 10.0 ** (-rs_db / 20.0)
    weights = [1.0 / delta_p, 1.0 / delta_s]
    b = signal.remez(numtaps, [0.0, passband_end, stopband_start, fs / 2.0], [1.0, 0.0], weight=weights, fs=fs)
    return FilterModel(
        name="Equiripple",
        fs=fs,
        kind="lowpass",
        mode="fir",
        numtaps=numtaps,
        rp_db=rp_db,
        rs_db=rs_db,
        cutoff=(passband_end, stopband_start),
        b=b,
        a=np.array([1.0]),
    )


def fir_equiripple_highpass(
    numtaps: int,
    fs: float,
    stopband_end: float,
    passband_start: float,
    rp_db: float,
    rs_db: float,
) -> FilterModel:
    # Highpass weighting swaps passband/stopband emphasis relative to the lowpass case.
    delta_p = (10.0 ** (rp_db / 20.0) - 1.0) / (10.0 ** (rp_db / 20.0) + 1.0)
    delta_s = 10.0 ** (-rs_db / 20.0)
    weights = [1.0 / delta_s, 1.0 / delta_p]
    b = signal.remez(numtaps, [0.0, stopband_end, passband_start, fs / 2.0], [0.0, 1.0], weight=weights, fs=fs)
    return FilterModel(
        name="Equiripple Highpass",
        fs=fs,
        kind="highpass",
        mode="fir",
        numtaps=numtaps,
        rp_db=rp_db,
        rs_db=rs_db,
        cutoff=(stopband_end, passband_start),
        b=b,
        a=np.array([1.0]),
    )


def fir_equiripple_bandpass(
    numtaps: int,
    fs: float,
    low_stop: float,
    low_pass: float,
    high_pass: float,
    high_stop: float,
    rp_db: float,
    rs_db: float,
) -> FilterModel:
    # Extremely narrow low-frequency transitions can make remez numerically fragile, so the
    # design is retried with denser grids before giving up.
    delta_p = (10.0 ** (rp_db / 20.0) - 1.0) / (10.0 ** (rp_db / 20.0) + 1.0)
    delta_s = 10.0 ** (-rs_db / 20.0)
    weights = [1.0 / delta_s, 1.0 / delta_p, 1.0 / delta_s]
    bands = [0.0, low_stop, low_pass, high_pass, high_stop, fs / 2.0]
    desired = [0.0, 1.0, 0.0]
    last_error: Exception | None = None
    b: np.ndarray | None = None
    for grid_density, maxiter in ((16, 200), (32, 1000), (64, 1000)):
        try:
            b = signal.remez(
                numtaps,
                bands,
                desired,
                weight=weights,
                fs=fs,
                maxiter=maxiter,
                grid_density=grid_density,
            )
            break
        except ValueError as exc:
            last_error = exc
    if b is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError("Bandpass equiripple design failed without a captured exception.")
    return FilterModel(
        name="Equiripple FIR Bandpass",
        fs=fs,
        kind="bandpass",
        mode="fir",
        numtaps=numtaps,
        rp_db=rp_db,
        rs_db=rs_db,
        cutoff=(low_pass, high_pass),
        b=b,
        a=np.array([1.0]),
    )


def fir_from_coefficients(name: str, fs: float, kind: str, coefficients: np.ndarray) -> FilterModel:
    return FilterModel(
        name=name,
        fs=fs,
        kind=kind,
        mode="fir",
        numtaps=int(coefficients.size),
        b=np.asarray(coefficients, dtype=float),
        a=np.array([1.0]),
    )


def apply_model(model: FilterModel, data: np.ndarray, zero_phase: bool = False) -> np.ndarray:
    if model.sos is not None:
        if zero_phase:
            return signal.sosfiltfilt(model.sos, data, axis=-1)
        return signal.sosfilt(model.sos, data, axis=-1)
    if model.b is None or model.a is None:
        raise ValueError("Filter coefficients are missing.")
    if zero_phase:
        return signal.filtfilt(model.b, model.a, data, axis=-1)
    return signal.lfilter(model.b, model.a, data, axis=-1)


def search_min_odd_taps(
    design_fn: Callable[[int], FilterModel],
    meets_spec_fn: Callable[[FilterModel], bool],
    start: int = 11,
    max_taps: int = 10001,
) -> FilterModel:
    cache: dict[int, tuple[FilterModel | None, bool]] = {}

    def evaluate(numtaps: int) -> tuple[FilterModel | None, bool]:
        if numtaps not in cache:
            try:
                candidate = design_fn(numtaps)
                is_valid = meets_spec_fn(candidate)
            except Exception:
                candidate = None
                is_valid = False
            cache[numtaps] = (candidate, is_valid)
        return cache[numtaps]

    # Linear-phase FIR designs are searched only on odd tap counts so the delay is centered on
    # an integer number of samples.
    current = start if start % 2 == 1 else start + 1
    lower_fail = current - 2
    upper_success: int | None = None
    best_model: FilterModel | None = None
    # First expand upward quickly until a feasible design is found.
    while current <= max_taps:
        candidate, is_valid = evaluate(current)
        if is_valid and candidate is not None:
            upper_success = current
            best_model = candidate
            break
        lower_fail = current
        current = int(max(current + 2, current * 2.0))
        if current % 2 == 0:
            current += 1
    if upper_success is None or best_model is None:
        raise RuntimeError(f"Failed to find a valid odd tap count up to {max_taps}.")
    lo = lower_fail + 2
    hi = upper_success
    # Then shrink back with a binary search to locate the shortest valid odd length.
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if mid % 2 == 0:
            mid += 1
        if mid > hi:
            break
        candidate, is_valid = evaluate(mid)
        if is_valid and candidate is not None:
            best_model = candidate
            hi = mid - 2
        else:
            lo = mid + 2
    return best_model


def dominant_fft_amplitude(signal_1d: np.ndarray, fs: float, target_hz: float) -> float:
    # The experiments compare one-sided amplitude spectra, so the FFT magnitude is doubled.
    spectrum = np.fft.rfft(signal_1d)
    freqs = np.fft.rfftfreq(signal_1d.size, d=1.0 / fs)
    index = int(np.argmin(np.abs(freqs - target_hz)))
    return float(2.0 * np.abs(spectrum[index]) / signal_1d.size)


def estimate_delay_ms(reference: np.ndarray, target: np.ndarray, fs: float, max_lag_s: float = 0.5) -> float:
    # Delay is estimated on a bounded lag window to avoid spurious matches at far-away cycles.
    max_lag = int(fs * max_lag_s)
    corr = signal.correlate(target - np.mean(target), reference - np.mean(reference), mode="full")
    lags = signal.correlation_lags(target.size, reference.size, mode="full")
    mask = np.abs(lags) <= max_lag
    lag = lags[mask][int(np.argmax(corr[mask]))]
    return float(lag * 1000.0 / fs)
