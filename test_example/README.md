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
- `check_results.py` -- host-side checker: recomputes each cycle's
  instantaneous chirp frequency, splits samples into in-band/out-of-band
  by the filter's designed passband/stopband, and asserts the core's
  output is measurably larger in-band than out-of-band.

## Running it

On the host:
```sh
python generate_coeffs.py
```

Push everything except `check_results.py` to the VM (`/repos/test_example`),
then on the VM:
```sh
source /opt/Xilinx/13.4/ISE_DS/settings64.sh
coregen -b ipcore_dir/poc_bpf_fir.xco -p ipcore_dir/coregen.cgp
fuse -intstyle "ise" -incremental \
     -lib "unisims_ver" -lib "unimacro_ver" -lib "xilinxcorelib_ver" -lib "secureip" \
     -o "sim_exe" -prj "sim.prj" "work.poc_bpf_tb" "work.glbl"
./sim_exe -tclbatch run.tcl
```

Pull `results.csv` back to the host, then:
```sh
python check_results.py results.csv
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
