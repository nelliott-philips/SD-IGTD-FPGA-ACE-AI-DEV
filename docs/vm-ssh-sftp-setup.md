# Setting up SSH/SFTP access to an ISE build VM

This is a generalized, reproducible runbook for giving an AI coding assistant (or
yourself) command-line/file access to a VirtualBox VM used for Xilinx ISE FPGA
builds, without exposing it to the network and without ever needing to know the
guest account's login password.

## Why this approach

The ISE 13.4/14.7 toolchain and the Oracle Linux 6.x guest OS are frozen on
purpose: FPGA placer/router behavior is sensitive to tool and OS version, and
this project's builds must stay bit-for-bit identical to already
test-pattern-validated hardware. So the VM stays a dumb, frozen "build
appliance" — all source analysis, HDL editing, and orchestration happens on a
modern host, and the VM is only used to run the actual
synthesize/map/place-and-route/bitgen step and report results back.

See [`project_ace_fpga_overview`](../CLAUDE.md) for the project-level context.

## Prerequisites

- VirtualBox installed on the host, with `VBoxManage` available (on Windows
  it's often not on `PATH` — the full path is typically
  `C:\Program Files\Oracle\VirtualBox\VBoxManage.exe`).
- The target VM already exists (e.g. a clone of a known-good ISE VM), has
  VirtualBox Guest Additions installed, and uses a **NAT** network adapter
  (the default `localhost-reachable=true` NAT setup is all that's needed —
  no bridged/host-only networking required).
- A non-root guest user account to connect as (this project uses `ise`).
- A VirtualBox **shared folder** already mounted in the guest (used below to
  transfer files byte-for-byte — avoids a nasty terminal-paste pitfall, see
  Step 4).

## Steps

### 1. Identify the VM and confirm its networking

```sh
VBoxManage list vms
VBoxManage showvminfo "<VM NAME>" --machinereadable | grep -iE "CfgFile|nic1|macaddress1|SharedFolder"
```

Confirm `nic1="nat"` and note the `SharedFolderPathMachineMapping` for later.

### 2. Generate a dedicated SSH keypair on the host

Use **RSA**, not `ed25519`, if the guest's OpenSSH predates version 6.5 (true
for EL6/RHEL6-era guests and older) — `ed25519` support wasn't added until
OpenSSH 6.5.

```sh
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_<vmname> -N "" -C "<label>"
```

No passphrase — this key is for automation, not personal login, and should
not be reused as anyone's personal key.

### 3. Add a loopback-only NAT port-forward

This works on an **already-running** VM, no reboot required:

```sh
VBoxManage controlvm "<VM NAME>" natpf1 "ssh,tcp,127.0.0.1,<HOST_PORT>,,22"
```

Verify:

```sh
VBoxManage showvminfo "<VM NAME>" --machinereadable | grep -i forwarding
```

Keep the forward bound to `127.0.0.1` unless you specifically need the VM
reachable from other machines on the LAN — don't default to `0.0.0.0`.

### 4. Install the public key into the guest — via the shared folder, not by pasting

**Pitfall we hit in practice:** pasting a long base64 SSH public key directly
into a VM console terminal (e.g. via `echo '<key>' >> ~/.ssh/authorized_keys`)
can silently corrupt it. In our case, the terminal's line-wrapping inserted
two stray spaces into the key blob at the visual wrap points. The file length
was off by exactly those extra bytes, and `sshd` logged
`key_from_blob: can't read rsa key` — but the symptom from the client side was
just a confusing fall-through to a password prompt (which nobody could answer,
since the automation account's password is intentionally unknown).

**Fix: use a shared folder to move the file byte-for-byte instead of typing it.**

On the host, copy the `.pub` file into the shared folder:

```sh
cp ~/.ssh/id_rsa_<vmname>.pub "<host-shared-folder-path>/claude_ssh_key.pub"
md5sum "<host-shared-folder-path>/claude_ssh_key.pub"
```

In the guest console, copy it into place (this is a short command with no
long literal string to mistype or mis-wrap):

```sh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cp ~/<shared-folder-mountpoint>/claude_ssh_key.pub ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
md5sum ~/.ssh/authorized_keys   # compare against the host md5sum above
```

If the checksums don't match, something mangled the transfer — don't proceed
to testing SSH until they do.

Clean up the temp file from the shared folder once confirmed:

```sh
rm ~/<shared-folder-mountpoint>/claude_ssh_key.pub
```

### 5. Confirm sshd is running in the guest

EL6/older RHEL-family (SysV init, no `systemctl`):

```sh
sudo service sshd status
# if not running:
sudo service sshd start && sudo chkconfig sshd on
```

Newer systemd-based guests: `sudo systemctl status sshd` /
`sudo systemctl enable --now sshd`.

### 6. Test SSH from the host

```sh
ssh -p <HOST_PORT> -i ~/.ssh/id_rsa_<vmname> <user>@127.0.0.1 'echo ok'
```

If you get:

```
Unable to negotiate with 127.0.0.1 port <HOST_PORT>: no matching host key type found. Their offer: ssh-rsa,ssh-dss
```

the guest's OpenSSH is old enough that modern clients refuse its algorithms by
default. Allow them **for this connection only** (don't weaken global client
defaults):

```sh
ssh -p <HOST_PORT> -i ~/.ssh/id_rsa_<vmname> \
  -o HostKeyAlgorithms=+ssh-rsa \
  -o PubkeyAcceptedAlgorithms=+ssh-rsa \
  <user>@127.0.0.1 'echo ok'
```

### 7. Verify SFTP the same way

```sh
sftp -P <HOST_PORT> -i ~/.ssh/id_rsa_<vmname> \
  -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa \
  <user>@127.0.0.1
```

### 8. Add a permanent SSH client alias

Append to the host's `~/.ssh/config`:

```
Host <alias>
    HostName 127.0.0.1
    Port <HOST_PORT>
    User <user>
    IdentityFile ~/.ssh/id_rsa_<vmname>
    HostKeyAlgorithms +ssh-rsa
    PubkeyAcceptedAlgorithms +ssh-rsa
    IdentitiesOnly yes
```

From then on: `ssh <alias> '<command>'`, `sftp <alias>`, `scp file <alias>:path`.

### 9. Diagnosing failures

- Guest-side auth log: `/var/log/secure` on EL6/RHEL6-family guests
  (`journalctl -u sshd` on systemd guests).
- Re-check `md5sum`/`wc -c` of `authorized_keys` against the source `.pub` any
  time pubkey auth unexpectedly fails — transfer corruption is the first
  thing to rule out.

## Security notes

- One dedicated key per VM, no passphrase, never reused as a personal key.
- Port forward bound to loopback only — nothing exposed on the network.
- No guest account password is ever known to, stored by, or transmitted to
  the automation tooling. Password auth is not relied on anywhere in this
  flow — only public-key auth.

## Applied example — this project's VM

| Item | Value |
|---|---|
| VM name | `Xilinx ISE Github` |
| Guest OS | Oracle Linux 6.x, ISE 13.4/14.7 |
| Guest user | `ise` |
| Host port | `2222` |
| Host key file | `~/.ssh/id_rsa_xilinx_ise_github` |
| SSH alias | `xilinx-ise-github` |
| Shared folder used for key transfer | `Xilinx_Share` (host `C:\VMs\Xilinx ISE\Xilinx_Share`, guest `/home/ise/Xilinx_Share`) |
