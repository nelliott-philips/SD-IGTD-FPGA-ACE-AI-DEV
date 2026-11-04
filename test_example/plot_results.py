#!/usr/bin/env python3
"""Plot the poc_bpf_fir chirp input/output in time and frequency domain.

Layout is a 2x2 grid: time domain in the left column (input over output),
frequency domain in the right column (input over output), so each pair is
directly comparable top-to-bottom and the two domains are side by side.

Runs on the host (needs numpy + matplotlib -- not the VM's Python 2.6).

Usage:
    python plot_results.py [results.csv] [--params filter_params.json]
                            [--save out.png] [--no-show] [--linear]
"""
import argparse
import csv
import json
import os

import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# dataviz skill's validated default categorical palette, slots 1/2 (adjacent,
# colorblind-safe pair) -- blue for input, orange for output, used consistently
# across all four panels so color encodes "input vs output" throughout.
COLOR_INPUT = "#2a78d6"
COLOR_OUTPUT = "#eb6834"
COLOR_SURFACE = "#fcfcfb"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_TEXT_SECONDARY = "#52514e"
COLOR_MUTED = "#898781"


def load_results(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    cycle = np.array([int(r["cycle"]) for r in rows])
    din = np.array([int(r["din"]) for r in rows], dtype=float)
    dout = np.array([int(r["dout"]) for r in rows], dtype=float)
    rdy = np.array([int(r["rdy"]) for r in rows])
    return cycle, din, dout, rdy


def spectrum_db(signal, clock_hz):
    mag = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / clock_hz)
    peak = max(mag.max(), 1e-9)
    mag_db = 20 * np.log10(np.maximum(mag, 1e-9) / peak)
    return freqs, mag_db


def spectrum_linear(signal, clock_hz):
    mag = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / clock_hz)
    return freqs, mag


def style_axes(ax):
    ax.set_facecolor(COLOR_SURFACE)
    ax.grid(True, color=COLOR_GRID, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color(COLOR_AXIS)
    ax.tick_params(colors=COLOR_TEXT_SECONDARY)
    ax.title.set_color(COLOR_TEXT_PRIMARY)
    ax.xaxis.label.set_color(COLOR_TEXT_SECONDARY)
    ax.yaxis.label.set_color(COLOR_TEXT_SECONDARY)


def mark_passband(ax, params):
    ax.axvspan(params["passband_min_mhz"], params["passband_max_mhz"],
               color=COLOR_MUTED, alpha=0.15, lw=0)
    ymin, ymax = ax.get_ylim()
    # Label near the bottom of the axes -- the passband is where the curve
    # peaks (near the top), so this keeps the label clear of the data.
    ax.text((params["passband_min_mhz"] + params["passband_max_mhz"]) / 2,
             ymin + 0.05 * (ymax - ymin), "passband",
             ha="center", va="bottom", color=COLOR_TEXT_SECONDARY, fontsize=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="?", default=os.path.join(HERE, "results.csv"),
                         help="Path to results.csv (default: ./results.csv)")
    parser.add_argument("--params", default=os.path.join(HERE, "filter_params.json"),
                         help="Path to filter_params.json (default: ./filter_params.json)")
    parser.add_argument("--save", default=None, help="Save the figure to this path (e.g. plot.png)")
    parser.add_argument("--no-show", action="store_true", help="Don't open an interactive window")
    parser.add_argument("--linear", action="store_true", help="Plot linear magnitude instead of dB")
    args = parser.parse_args()

    with open(args.params) as f:
        params = json.load(f)

    cycle, din, dout, rdy = load_results(args.results)
    clock_hz = params["clock_hz"]
    time_us = cycle / clock_hz * 1e6

    # Mask pipeline-fill samples (rdy=0) in the output time-domain trace --
    # shows the core's known fixed latency as a visual gap rather than
    # plotting meaningless pre-fill values. For the spectrum, zero them
    # instead (NaN would break the FFT).
    dout_display = dout.copy()
    dout_display[rdy == 0] = np.nan
    dout_fft = dout.copy()
    dout_fft[rdy == 0] = 0.0

    spectrum = spectrum_linear if args.linear else spectrum_db
    freq_in, mag_in = spectrum(din, clock_hz)
    freq_out, mag_out = spectrum(dout_fft, clock_hz)
    mag_label = "Magnitude (linear)" if args.linear else "Magnitude (dB)"

    fig, ((ax_in_t, ax_in_f), (ax_out_t, ax_out_f)) = plt.subplots(2, 2, figsize=(12, 7), sharex="col")
    fig.patch.set_facecolor(COLOR_SURFACE)

    ax_in_t.plot(time_us, din, color=COLOR_INPUT, linewidth=1.0)
    ax_in_t.set_title("Input (time domain)")
    ax_in_t.set_ylabel("Amplitude (LSB)")

    ax_out_t.plot(time_us, dout_display, color=COLOR_OUTPUT, linewidth=1.0)
    ax_out_t.set_title("Output (time domain)")
    ax_out_t.set_ylabel("Amplitude (LSB)")
    ax_out_t.set_xlabel("Time (µs)")

    ax_in_f.plot(freq_in / 1e6, mag_in, color=COLOR_INPUT, linewidth=1.0)
    ax_in_f.set_title("Input (frequency domain)")
    ax_in_f.set_ylabel(mag_label)
    mark_passband(ax_in_f, params)

    ax_out_f.plot(freq_out / 1e6, mag_out, color=COLOR_OUTPUT, linewidth=1.0)
    ax_out_f.set_title("Output (frequency domain)")
    ax_out_f.set_ylabel(mag_label)
    ax_out_f.set_xlabel("Frequency (MHz)")
    mark_passband(ax_out_f, params)

    for ax in (ax_in_t, ax_out_t, ax_in_f, ax_out_f):
        style_axes(ax)

    fig.suptitle("poc_bpf_fir -- chirp input/output, time & frequency domain", color=COLOR_TEXT_PRIMARY)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    if args.save:
        fig.savefig(args.save, dpi=150, facecolor=COLOR_SURFACE)
        print("Saved figure to {0}".format(args.save))
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
