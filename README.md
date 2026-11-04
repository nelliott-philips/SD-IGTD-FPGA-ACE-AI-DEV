# ai_ace_development

AI-assisted development workspace for the Philips ACE ultrasound platform's
FPGA firmware project
([`SD-IGTD-ACE-FPGA`](https://github.com/philips-internal/SD-IGTD-ACE-FPGA)).

This repo holds the context, reference artifacts, and tooling setup an AI
coding assistant (or a new engineer) needs to work on the ACE Focus/ACE Image
Virtex-6 FPGA sources — it does **not** contain the FPGA source itself yet.

## Contents

- [`CLAUDE.md`](CLAUDE.md) — the phased project plan: VM access, build
  automation, schematic/HDL analysis, and the bit-exact HDL-porting/testbench
  regression plan.
- [`docs/vm-ssh-sftp-setup.md`](docs/vm-ssh-sftp-setup.md) — reproducible
  runbook for giving an AI assistant SSH/SFTP access to the frozen ISE build
  VM, including a pitfall we hit (and how to avoid it) when installing SSH
  keys into an old guest console.
- Reference schematics and the ACE system block diagram (DigiPIM → ACE Card
  Focus/Image FPGAs → Host AUSIL pipeline).

## Why the build VM stays frozen

`SD-IGTD-ACE-FPGA` builds with Xilinx ISE 13.4/14.7 on an Oracle Linux 6.x VM.
That toolchain/OS combination is intentionally **not** upgraded: ISE's
placer/router is sensitive to tool and OS version, and builds must stay
bit-for-bit identical to already test-pattern-validated hardware. See
`docs/vm-ssh-sftp-setup.md` for how AI tooling reaches that VM without
touching it.

## Planned structure

Pending review of this repo's contents, `SD-IGTD-ACE-FPGA` will be added here
as a **git submodule** (not a subtree or untracked clone), so its history
stays independent while this repo tracks which commit of it the AI
development setup/docs apply to:

```sh
git submodule add https://github.com/philips-internal/SD-IGTD-ACE-FPGA.git firmware
```

Not yet done — awaiting sign-off.
