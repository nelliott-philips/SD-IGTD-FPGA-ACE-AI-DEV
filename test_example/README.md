# test_example: Xilinx CoreGen IP integration proof-of-concept

Validates that the AI-development workflow can integrate a real **Xilinx
CORE Generator IP core** (FIR Compiler v5.0), not just hand-written HDL:
generate the core on the frozen ISE VM, simulate it with ISim, and verify
the results back on the host. See `../docs/vm-ssh-sftp-setup.md` for the
underlying SSH/SFTP access this relies on.

Everything here is throwaway/contrived (coefficients, naming, passband) --
it mirrors the real project's CoreGen FIR usage pattern without touching
any production files or data.

## Contents

- `generate_coeffs.py` -- host-side, stdlib-only. Designs a 21-tap
  windowed-sinc bandpass filter (~20-31MHz passband at a 100MHz sample
  rate) and the chirp sweep's phase-accumulator constants. Writes
  `ipcore_dir/poc_bpf_coeffs.coe` and `filter_params.json` (single source
  of truth, also read by `check_results.py`).
- `ipcore_dir/coregen.cgp`, `ipcore_dir/poc_bpf_fir.xco` -- CoreGen project
  settings and IP parameterization, modeled on an existing FIR Compiler
  core already in this repo's real project (`bp_fir_cf.xco`).
- `poc_bpf_tb.v` -- testbench: DDS chirp generator (~5MHz to ~45MHz sweep,
  sine lookup table), drives `poc_bpf_fir`, logs every cycle
  (`cycle,din,dout,rfd,rdy`) to `results.csv`.
- `sim.prj`, `run.tcl` -- ISim batch compile/run files.
- `check_results.py` -- checker: recomputes each cycle's instantaneous
  chirp frequency, splits samples into in-band/out-of-band by the filter's
  designed passband/stopband, and asserts the core's output is measurably
  larger in-band than out-of-band. Runs on either the host (Python 3) or
  directly on the VM (Python 2.6.6 -- that's all the VM has, so this is
  deliberately 2.6-compatible: no f-strings, no `pathlib`).
- `run_test.sh` -- **the one command to run on the VM** to regenerate,
  compile, simulate, and check everything, with clear step-by-step output
  and a final PASS/FAIL.
- `plot_results.py` -- host-side (needs numpy + matplotlib, not run on the
  VM). Plots `results.csv` as a 2x2 grid: time domain in the left column
  (input over output), frequency domain (FFT magnitude, dB by default) in
  the right column (input over output), with the designed passband shaded
  on both frequency panels. Input is blue, output is orange, consistently
  across all four panels.

## Running it

On the host, after editing the filter/chirp design in `generate_coeffs.py`:
```sh
python generate_coeffs.py
```

Push everything (including `check_results.py` -- it runs on the VM too
now) to the VM's `/repos/test_example`, then from the VM command line:
```sh
./run_test.sh
```
That's it -- it sources the ISE environment, runs CoreGen, compiles with
`fuse`, runs the ISim simulation, and checks the results, printing PASS or
FAIL. Exit code is 0 on PASS, non-zero otherwise, so it's safe to script.

If you'd rather run the steps individually (e.g. to debug a failure), or
run the check back on the host instead:
```sh
source /opt/Xilinx/13.4/ISE_DS/settings64.sh
coregen -b ipcore_dir/poc_bpf_fir.xco -p ipcore_dir/coregen.cgp
fuse -intstyle "ise" -incremental \
     -lib "unisims_ver" -lib "unimacro_ver" -lib "xilinxcorelib_ver" -lib "secureip" \
     -o "sim_exe" -prj "sim.prj" "work.poc_bpf_tb" "work.glbl"
./sim_exe -tclbatch run.tcl
python check_results.py results.csv   # or: python2 check_results.py results.csv
```

To visualize the run after pulling `results.csv` back to the host:
```sh
python plot_results.py results.csv            # opens an interactive window
python plot_results.py results.csv --save plot.png --no-show   # headless/scripted
```

## Lessons learned

- **`output_width` is computed by CoreGen from the actual coefficients, not
  a value you can just copy from another core.** Copying `bp_fir_cf`'s
  `output_width=28` into `poc_bpf_fir.xco` was wrong for this filter's
  (larger-magnitude) coefficients -- CoreGen recalculated it to 29 bits at
  generation time and printed a `WARNING:sim:597` saying so. Always check
  the generated module's actual port declaration (`grep -A8 "^module" ipcore_dir/<core>.v`)
  rather than assuming widths carried over from a similar core.
- The `CoefficientVector` field in a `COE_File`-sourced `.xco` is cosmetic/
  disabled -- CoreGen genuinely reads coefficients from the referenced
  `.coe` file (confirmed here because the computed `output_width` changed
  to match *this* filter's coefficients, not the template default's).
- `glbl.v` (`$XILINX/ISE_DS/ISE/verilog/src/glbl.v`) must be in `sim.prj`
  and passed to `fuse` as `work.glbl` any time Xilinx primitives are in the
  simulation -- easy to forget, confirmed required by inspecting a working
  `fuseRelaunch.cmd` from an existing project.
