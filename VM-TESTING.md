# Verify a complete installation

The [VM installation check](https://github.com/agammann/kali-installer/actions/workflows/install-test.yml) workflow downloads an existing multipart release, verifies and reconstructs its ISO, installs it to a new 64 GiB virtual disk, and boots that disk with the installation media removed.

Select **Run workflow** and enter the release tag. The workflow checks password login for the account created during installation, the Kali operating-system identity, the installed root filesystem, the selected Xfce desktop and default Kali packages, package consistency, desktop service startup, DNS, and an outbound HTTPS request. Its evidence artifact contains the ISO checksum, result details, serial logs, and a screenshot of the graphical login screen. It does not contain the VM disk or temporary account credentials.

This test uses SeaBIOS. The installer starts from the kernel and initrd extracted from the ISO, with the original ISO attached as installation media. The subsequent boot uses the installed disk's bootloader with no ISO or externally supplied kernel. It does not test the ISO's interactive boot menu, UEFI installation, every installation option, or physical hardware.

## Run locally with Docker and KVM

The commands below target a Linux shell with Docker and KVM access. Use the GitHub workflow if your local Docker environment does not expose `/dev/kvm`.

Docker must be able to access `/dev/kvm`, with at least 4 GiB of memory available for the guest and at least 25 GiB of free storage for the installed system and temporary files, in addition to the ISO. The VM has a new sparse 64 GiB disk and receives no host disks. The script refuses to overwrite an existing test disk. QEMU's SSH forwarding and the temporary preseed server listen only on loopback inside the container; no container ports are published.

After building the installer and its Docker builder image with `scripts/rebuild-from-github.sh`:

```sh
docker build -t kali-installer-vm-test:local -f tests/Dockerfile.vm .
digest=$(head -1 rebuild-output/SHA256SUMS | cut -d ' ' -f 1)
docker run --rm --device /dev/kvm \
  --mount "type=bind,source=$PWD/rebuild-output,target=/out" \
  --mount "type=bind,source=$PWD/tests,target=/tests,readonly" \
  kali-installer-vm-test:local python3 /tests/vm_install.py \
  --iso /out/kali-linux-rolling-installer-amd64.iso \
  --output /out/vm-test --expected-sha256 "$digest"
```

The test creates a random password for its disposable account, applies installation answers through an external preseed, and enables SSH for verification in that VM. It does not modify the ISO. The virtual disk is a test artifact, not a distributable image. Keep only the logs and results you need after testing, and remove the disposable disk when finished.

An exit status of zero means every recorded check passed. A timeout, missing package, failed login, inconsistent package state, failed desktop service, or network error fails the run. Inspect `rebuild-output/vm-test/` and the workflow logs for failures. Use a different empty `--output` directory for a fresh attempt.
