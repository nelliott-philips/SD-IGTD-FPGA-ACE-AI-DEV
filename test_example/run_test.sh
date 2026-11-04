#!/bin/sh
# Run the full poc_bpf_fir CoreGen IP integration test from the VM command
# line: generate the core, compile it, simulate it, and check the results --
# one command, clear pass/fail at the end.
#
# Usage (from /repos/test_example on the VM):
#   ./run_test.sh
#
# Exit code 0 = PASS, non-zero = a step failed (see which step printed FAIL).

set -e
cd "$(dirname "$0")"

echo "=== [1/4] Sourcing ISE environment ==="
. /opt/Xilinx/13.4/ISE_DS/settings64.sh

echo "=== [2/4] Generating CoreGen IP (poc_bpf_fir) ==="
coregen -b ipcore_dir/poc_bpf_fir.xco -p ipcore_dir/coregen.cgp
if [ ! -f ipcore_dir/poc_bpf_fir.v ]; then
    echo "FAIL: CoreGen did not produce ipcore_dir/poc_bpf_fir.v"
    exit 1
fi

echo "=== [3/4] Compiling testbench with fuse ==="
fuse -intstyle "ise" -incremental \
     -lib "unisims_ver" -lib "unimacro_ver" -lib "xilinxcorelib_ver" -lib "secureip" \
     -o "sim_exe" -prj "sim.prj" "work.poc_bpf_tb" "work.glbl"

echo "=== [4/4] Running simulation ==="
./sim_exe -tclbatch run.tcl
if [ ! -f results.csv ]; then
    echo "FAIL: simulation did not produce results.csv"
    exit 1
fi

echo "=== Checking results ==="
if command -v python >/dev/null 2>&1; then
    python check_results.py results.csv
elif command -v python2 >/dev/null 2>&1; then
    python2 check_results.py results.csv
else
    echo "No python interpreter found on this VM -- pull results.csv back to"
    echo "the host and run: python check_results.py results.csv"
    exit 2
fi
