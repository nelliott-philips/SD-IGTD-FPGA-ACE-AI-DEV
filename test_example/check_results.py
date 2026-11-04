#!/usr/bin/env python3
"""Verify results.csv from the poc_bpf_fir ISim run.

Classifies each logged cycle by the chirp's instantaneous frequency at that
cycle (recomputed from the same phase-accumulator constants the testbench
uses, sourced from filter_params.json) and checks that the core's output
is measurably larger inside the designed passband than outside it.
"""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
PASS_MARGIN = 2.0  # require in-band RMS >= this multiple of out-of-band RMS


def freq_hz_at_cycle(cycle, params):
    step = params["phase_step0"] + cycle * params["phase_step_inc"]
    return step * params["clock_hz"] / (2 ** params["phase_bits"])


def main():
    results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results.csv"
    params = json.loads((HERE / "filter_params.json").read_text())

    passband_min_hz = params["passband_min_mhz"] * 1e6
    passband_max_hz = params["passband_max_mhz"] * 1e6
    stopband_min_hz = params["stopband_min_mhz"] * 1e6
    stopband_max_hz = params["stopband_max_mhz"] * 1e6
    chirp_len = params["chirp_len_cycles"]

    rows = list(csv.DictReader(results_path.open()))
    if not rows:
        print(f"FAIL: {results_path} is empty")
        sys.exit(1)

    expected_rows = params["chirp_len_cycles"] + params["latency_margin_cycles"]
    if len(rows) != expected_rows:
        print(f"WARNING: expected {expected_rows} rows, got {len(rows)}")

    in_band_sq = []
    out_band_sq = []

    for row in rows:
        cycle = int(row["cycle"])
        rdy = int(row["rdy"])
        if not rdy or cycle >= chirp_len:
            continue
        freq = freq_hz_at_cycle(cycle, params)
        dout = int(row["dout"])
        if passband_min_hz <= freq <= passband_max_hz:
            in_band_sq.append(dout * dout)
        elif freq <= stopband_min_hz or freq >= stopband_max_hz:
            out_band_sq.append(dout * dout)
        # else: transition band, not scored

    if not in_band_sq or not out_band_sq:
        print(
            f"FAIL: not enough valid samples (in-band={len(in_band_sq)}, "
            f"out-of-band={len(out_band_sq)}) -- check rdy/latency assumptions"
        )
        sys.exit(1)

    in_band_rms = math.sqrt(sum(in_band_sq) / len(in_band_sq))
    out_band_rms = math.sqrt(sum(out_band_sq) / len(out_band_sq))
    ratio = in_band_rms / out_band_rms if out_band_rms else float("inf")

    print(f"in-band samples:     {len(in_band_sq)}")
    print(f"out-of-band samples: {len(out_band_sq)}")
    print(f"in-band RMS dout:     {in_band_rms:.1f}")
    print(f"out-of-band RMS dout: {out_band_rms:.1f}")
    print(f"ratio (in-band / out-of-band): {ratio:.2f}x")

    if ratio >= PASS_MARGIN:
        print(f"PASS: passband is attenuated by less than out-of-band (ratio >= {PASS_MARGIN}x)")
        sys.exit(0)
    else:
        print(f"FAIL: insufficient attenuation (ratio < {PASS_MARGIN}x)")
        sys.exit(1)


if __name__ == "__main__":
    main()
