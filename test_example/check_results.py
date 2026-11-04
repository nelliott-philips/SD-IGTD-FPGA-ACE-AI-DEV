#!/usr/bin/env python
"""Verify results.csv from the poc_bpf_fir ISim run.

Classifies each logged cycle by the chirp's instantaneous frequency at that
cycle (recomputed from the same phase-accumulator constants the testbench
uses, sourced from filter_params.json) and checks that the core's output
is measurably larger inside the designed passband than outside it.

Portable to Python 2.6+ (the VM only has 2.6.6) as well as Python 3, so it
can be run directly on the VM without pulling results.csv back to the host.
"""
from __future__ import division, print_function

import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PASS_MARGIN = 2.0  # require in-band RMS >= this multiple of out-of-band RMS


def freq_hz_at_cycle(cycle, params):
    step = params["phase_step0"] + cycle * params["phase_step_inc"]
    return step * params["clock_hz"] / (2 ** params["phase_bits"])


def main():
    results_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results.csv")
    with open(os.path.join(HERE, "filter_params.json")) as f:
        params = json.load(f)

    passband_min_hz = params["passband_min_mhz"] * 1e6
    passband_max_hz = params["passband_max_mhz"] * 1e6
    stopband_min_hz = params["stopband_min_mhz"] * 1e6
    stopband_max_hz = params["stopband_max_mhz"] * 1e6
    chirp_len = params["chirp_len_cycles"]

    with open(results_path) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("FAIL: {0} is empty".format(results_path))
        sys.exit(1)

    expected_rows = params["chirp_len_cycles"] + params["latency_margin_cycles"]
    if len(rows) != expected_rows:
        print("WARNING: expected {0} rows, got {1}".format(expected_rows, len(rows)))

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
            "FAIL: not enough valid samples (in-band={0}, out-of-band={1}) "
            "-- check rdy/latency assumptions".format(len(in_band_sq), len(out_band_sq))
        )
        sys.exit(1)

    in_band_rms = math.sqrt(sum(in_band_sq) / len(in_band_sq))
    out_band_rms = math.sqrt(sum(out_band_sq) / len(out_band_sq))
    ratio = in_band_rms / out_band_rms if out_band_rms else float("inf")

    print("in-band samples:     {0}".format(len(in_band_sq)))
    print("out-of-band samples: {0}".format(len(out_band_sq)))
    print("in-band RMS dout:     {0:.1f}".format(in_band_rms))
    print("out-of-band RMS dout: {0:.1f}".format(out_band_rms))
    print("ratio (in-band / out-of-band): {0:.2f}x".format(ratio))

    if ratio >= PASS_MARGIN:
        print("PASS: passband is attenuated by less than out-of-band (ratio >= {0}x)".format(PASS_MARGIN))
        sys.exit(0)
    else:
        print("FAIL: insufficient attenuation (ratio < {0}x)".format(PASS_MARGIN))
        sys.exit(1)


if __name__ == "__main__":
    main()
