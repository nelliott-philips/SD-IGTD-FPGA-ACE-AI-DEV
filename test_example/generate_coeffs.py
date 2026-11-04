#!/usr/bin/env python3
"""Design POC bandpass FIR coefficients and write them as a CoreGen .coe file.

Windowed-sinc bandpass design (Hamming window), symmetric, quantized to
signed 16-bit integers for FIR Compiler's coefficient_width=16.
"""
import json
import math
from pathlib import Path

SAMPLE_RATE_MHZ = 100.0
PASSBAND_MIN_MHZ = 20.0
PASSBAND_MAX_MHZ = 31.0
STOPBAND_MIN_MHZ = 10.0
STOPBAND_MAX_MHZ = 41.0
NUM_TAPS = 21
COEFFICIENT_WIDTH = 16
DATA_WIDTH = 12
OUTPUT_WIDTH = 29  # FIR Compiler's computed full-precision width for these
                   # coefficients -- confirmed from the generated core, not
                   # guessed (see README "Lessons learned")

# Chirp stimulus (DDS phase accumulator in the testbench) -- sweeps from
# below the stopband to above it, through the passband, over CHIRP_LEN cycles.
CLOCK_HZ = SAMPLE_RATE_MHZ * 1e6
PHASE_BITS = 32
CHIRP_START_HZ = 5e6
CHIRP_END_HZ = 45e6
CHIRP_LEN = 5000
LATENCY_MARGIN_CYCLES = 300
SETTLE_CYCLES = 10

OUT_DIR = Path(__file__).parent


def phase_step_for_freq(freq_hz):
    return round(freq_hz * (2 ** PHASE_BITS) / CLOCK_HZ)


def design_bandpass(num_taps, fc1, fc2):
    """fc1/fc2 are cutoffs normalized as a fraction of the sample rate."""
    m = (num_taps - 1) / 2.0
    taps = []
    for n in range(num_taps):
        k = n - m
        if k == 0:
            ideal = 2 * (fc2 - fc1)
        else:
            ideal = (math.sin(2 * math.pi * fc2 * k) - math.sin(2 * math.pi * fc1 * k)) / (math.pi * k)
        window = 0.54 - 0.46 * math.cos(2 * math.pi * n / (num_taps - 1))
        taps.append(ideal * window)
    return taps


def quantize(taps, width):
    max_val = (1 << (width - 1)) - 1
    scale = (max_val * 0.9) / max(abs(t) for t in taps)
    return [round(t * scale) for t in taps]


def write_coe(path, coeffs):
    with open(path, "w", newline="\n") as f:
        f.write(f";# {path.name}\n")
        f.write(";# POC bandpass FIR coefficients -- contrived, not production data\n")
        f.write("radix = 10;\n")
        f.write("coefdata =\n")
        f.write(",\n".join(str(c) for c in coeffs))
        f.write(";\n")


def main():
    fc1 = PASSBAND_MIN_MHZ / SAMPLE_RATE_MHZ
    fc2 = PASSBAND_MAX_MHZ / SAMPLE_RATE_MHZ
    taps = design_bandpass(NUM_TAPS, fc1, fc2)
    coeffs = quantize(taps, COEFFICIENT_WIDTH)

    # Symmetric structure requires exact mirror -- enforce it after rounding.
    for i in range(NUM_TAPS // 2):
        coeffs[NUM_TAPS - 1 - i] = coeffs[i]

    coe_path = OUT_DIR / "ipcore_dir" / "poc_bpf_coeffs.coe"
    write_coe(coe_path, coeffs)

    step0 = phase_step_for_freq(CHIRP_START_HZ)
    step_end = phase_step_for_freq(CHIRP_END_HZ)
    step_inc = round((step_end - step0) / CHIRP_LEN)

    params = {
        "sample_rate_mhz": SAMPLE_RATE_MHZ,
        "passband_min_mhz": PASSBAND_MIN_MHZ,
        "passband_max_mhz": PASSBAND_MAX_MHZ,
        "stopband_min_mhz": STOPBAND_MIN_MHZ,
        "stopband_max_mhz": STOPBAND_MAX_MHZ,
        "num_taps": NUM_TAPS,
        "coefficient_width": COEFFICIENT_WIDTH,
        "data_width": DATA_WIDTH,
        "output_width": OUTPUT_WIDTH,
        "coefficients": coeffs,
        "clock_hz": CLOCK_HZ,
        "phase_bits": PHASE_BITS,
        "chirp_start_hz": CHIRP_START_HZ,
        "chirp_end_hz": CHIRP_END_HZ,
        "chirp_len_cycles": CHIRP_LEN,
        "latency_margin_cycles": LATENCY_MARGIN_CYCLES,
        "settle_cycles": SETTLE_CYCLES,
        "phase_step0": step0,
        "phase_step_inc": step_inc,
    }
    with open(OUT_DIR / "filter_params.json", "w") as f:
        json.dump(params, f, indent=2)

    print(f"Wrote {coe_path}")
    print(f"Wrote {OUT_DIR / 'filter_params.json'}")
    print("Coefficients:", coeffs)
    print("phase_step0 =", step0, " phase_step_inc =", step_inc)


if __name__ == "__main__":
    main()
