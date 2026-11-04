# ai_ace_development

AI-assisted development workspace for the Philips ACE ultrasound platform's
FPGA firmware project
([`SD-IGTD-ACE-FPGA`](https://github.com/philips-internal/SD-IGTD-ACE-FPGA)).

This repo holds the context, reference artifacts, tooling setup, and (as of
`firmware/`) the actual FPGA source an AI coding assistant or a new engineer
needs to work on the ACE Focus/ACE Image Virtex-6 FPGA sources.

## Contents

- [`CLAUDE.md`](CLAUDE.md) — the phased project plan: VM access, build
  automation, schematic/HDL analysis, and the bit-exact HDL-porting/testbench
  regression plan.
- [`docs/vm-ssh-sftp-setup.md`](docs/vm-ssh-sftp-setup.md) — reproducible
  runbook for giving an AI assistant SSH/SFTP access to the frozen ISE build
  VM, including a pitfall we hit (and how to avoid it) when installing SSH
  keys into an old guest console.
- `firmware/` — the real `SD-IGTD-ACE-FPGA` repo as a git submodule (its own
  history stays independent; this repo just tracks which commit applies),
  including its own nested submodules (`SD-ACE1-*-FPGA`, `SD-ACE2-*-FPGA`).
  Cloned over HTTPS, not SSH — see "Cloning this repo" below, since the
  upstream `.gitmodules` entries use `git@github.com:` URLs that most hosts
  won't have an authorized key for.
- `test_example/` — a self-contained proof-of-concept (not part of the real
  firmware) validating the whole AI-dev workflow: a Xilinx CoreGen FIR
  Compiler IP core generated/simulated on the VM via ISim, chirp-tested, and
  verified back on the host. See `test_example/README.md`.
- `scripts/deploy_to_vm.sh` — packages this whole repo (minus all `.git`
  metadata) and ships it to a fresh, timestamped directory under `/repos` on
  the VM, so the VM never needs its own GitHub credentials.
- Reference schematics and the ACE system block diagram (DigiPIM → ACE Card
  Focus/Image FPGAs → Host AUSIL pipeline).

## Cloning this repo

The nested FPGA submodules are registered with `git@github.com:...` (SSH)
URLs, which will hang or fail on any machine without an SSH key authorized
for them (we hit this cloning onto a Windows host and again testing from
the VM). Rewrite them to HTTPS first, scoped to just this clone:

```sh
git clone https://github.com/nelliott-philips/SD-IGTD-FPGA-ACE-AI-DEV.git
cd SD-IGTD-FPGA-ACE-AI-DEV
git config url."https://github.com/".insteadOf "git@github.com:"
git submodule update --init --recursive
```

If `git submodule update --init --recursive` still fails partway with
`Permission denied (publickey)` on an otherwise-successful run, it's a known
flaky interaction between the `insteadOf` rewrite and that command's
internal (possibly parallel) retry logic -- clone the stuck submodule(s)
directly instead:

```sh
git clone https://github.com/philips-internal/<name>.git firmware/<name>
git -C firmware/<name> checkout <pinned-sha-from-git-submodule-status>
git -C firmware submodule absorbgitdirs
```

## Why the build VM stays frozen

`SD-IGTD-ACE-FPGA` builds with Xilinx ISE 13.4/14.7 on an Oracle Linux 6.x VM.
That toolchain/OS combination is intentionally **not** upgraded: ISE's
placer/router is sensitive to tool and OS version, and builds must stay
bit-for-bit identical to already test-pattern-validated hardware. See
`docs/vm-ssh-sftp-setup.md` for how AI tooling reaches that VM without
touching it.

## Keeping the VM concurrent with GitHub

Changes flow one way: host -> GitHub -> VM. `scripts/vm_sync_from_github.sh`
runs on a cron schedule **on the VM** and keeps its checkout continuously
up to date with no manual or AI involvement per run -- see the comments at
the top of that script for the one-time interactive setup (clone + cache a
credential) and the cron entry to add afterward.

## Deploying a one-off snapshot to the VM

For a deliberate point-in-time snapshot instead of continuous sync (e.g. to
freeze a specific state for a build), `scripts/deploy_to_vm.sh` packages
this whole repo (no `.git` metadata) and ships it to a **new timestamped
directory** under `/repos` on the VM -- the VM never needs GitHub
credentials for this path, since the clone/push already happened on the
host:

```sh
./scripts/deploy_to_vm.sh
```
