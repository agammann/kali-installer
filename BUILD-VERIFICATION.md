# Full installer build verification

The published images meet this repository's deployment criteria: a successful full build, checksum-verified public download, complete BIOS and UEFI VM installations, and a first disk boot with installation media removed. Use BIOS or UEFI with Secure Boot disabled. Physical-PC compatibility testing is optional follow-up and is not claimed by these results.

An [independent rebuild and installation of the unmodified GitLab source](UPSTREAM-COMPARISON.md) also passed. Installer configuration, package files, and boot executables match the fork; differences in generated files were checked and traced to timestamps and archive metadata. The reference VM passed the same 15 checks, with matching installed-system identity, package versions, filesystem layout, and startup state.

On 2026-09-20, `./scripts/rebuild-from-github.sh` completed successfully in Git Bash on Windows with Docker Desktop 29.8.0. The script cloned the public GitHub repository inside a Kali Linux container and checked out source commit `aab5c047300bb3150732be370dc494581f278325`. No GitLab checkout was used for this run.

The container started from `kalilinux/kali-rolling@sha256:30399bd65187e06525008dd13eecc2b3439d26a82b2c6b0ba32dee72bd843117` and installed the build packages from Kali's rolling package mirror. The exact build-package versions are saved in `rebuild-output/BUILD_PACKAGES` by the script.

```text
cpio 2.15+dfsg-2.1
debian-cd 3.2.3
dosfstools 4.2-1.2
isolinux 3:6.04~git20190206.bf6db5b4+dfsg1-3.2
mtools 4.0.49-1
simple-cdd 0.6.10
xorriso 1.5.8.pl02-2
```

| Check | Result |
| --- | --- |
| Full `amd64` installer build | Passed (exit 0) |
| Package consistency check | 0 broken packages |
| ISO size | 5,047,031,808 bytes |
| ISO SHA-256 | `c104e3f427d074f5fda666bf10f24ace9c9dd52f857ed0dcf4d95ced7a6ac026` |
| Copied ISO checksum | Passed with `sha256sum -c SHA256SUMS`; host SHA-256 matched |
| Boot records | El Torito BIOS and UEFI entries present; isohybrid MBR and GPT reported |
| Normal ISO boot in BIOS and UEFI modes | Passed; both boot menus reached the graphical installer's language-selection screen |
| Complete VM installation (SeaBIOS) | Passed to a new 64 GiB virtual disk |
| First boot without ISO (SeaBIOS) | Passed; root filesystem `/dev/vda1` on ext4 |
| Complete VM installation and first boot (OVMF UEFI) | Passed; ISO removed, root `/dev/vda2` on ext4, EFI partition `/dev/vda1` on FAT |
| Created account password login | Passed over the VM's loopback-only SSH forwarding |
| Xfce desktop service and login screen | Passed; screenshot recorded |
| Selected packages and package consistency | `kali-linux-default`, `kali-desktop-xfce`, and `openssh-server` fully installed; `dpkg --audit` empty |
| Networking | DHCP address, default route, DNS, and HTTPS request passed |

The rebuild writes `kali-linux-rolling-installer-amd64.iso`, its build log, `SHA256SUMS`, `SOURCE_COMMIT`, and `BUILD_PACKAGES` to the chosen output directory. See the [README](README.md#rebuild-from-github-in-docker) for the command and prerequisites.

The complete installation test ran in QEMU 11.1 with KVM, SeaBIOS, 4 GiB RAM, four virtual CPUs, and a new 64 GiB disk. The installer used the kernel and initrd extracted from this ISO, with the original ISO attached as its package source. After installation powered off, the VM booted its installed disk with the ISO and external kernel/initrd removed. The installed system reported Kali 2026.3. The selected desktop and default package metapackages were version 2026.3.9.

See the [recorded SeaBIOS VM results](docs/verification/installer-2026-09-20-vm.json), [graphical login screenshot](docs/verification/installer-2026-09-20-login.png), and [repeatable test instructions](VM-TESTING.md). Separate normal ISO boot checks reached the graphical installer through both [SeaBIOS](docs/verification/installer-2026-09-20-bios-start.png) and [OVMF UEFI](docs/verification/installer-2026-09-20-uefi-start.png), with the [UEFI boot menu](docs/verification/installer-2026-09-20-uefi-menu.png) also recorded. These checks attached only the original ISO and no virtual hard disk. Kali's rolling mirror changes over time, so a later run may produce a different ISO and checksum even from the same source commit; installation results apply to the exact checksum above.

A complete local UEFI installation subsequently passed using QEMU 11.1, OVMF 2026.05-2, KVM, and the test harness from commit `8d997a1f8539b1cd0dc59868e5f33fe5341651d9`. After installation, OVMF booted the new virtual disk with the ISO and external kernel/initrd removed. All 15 checks passed, including EFI runtime support, a mounted FAT EFI system partition, the installed GRUB EFI package, password login, system startup health, desktop service, package consistency, DNS, and HTTPS. See the [UEFI results](docs/verification/installer-2026-09-20-uefi-vm.json) and [UEFI login screenshot](docs/verification/installer-2026-09-20-uefi-login.png). Secure Boot was disabled. Secure Boot is unsupported; use BIOS or UEFI with Secure Boot disabled. Physical-PC compatibility has not been tested.

## Secure Boot compatibility

These images require Secure Boot to be disabled, consistent with [Kali's installation guide](https://www.kali.org/docs/installation/hard-disk-install/#preparing-for-the-installation). The original published ISO was also checked in QEMU with OVMF Secure Boot enabled and Microsoft certificates enrolled. Firmware rejected the ISO before the installer started, reporting `Access Denied -- rejected probably by Secure Boot`. This is an unsupported boot configuration, not a successful installation test. The check attached no hard disks and no network devices. See the [recorded environment and result](docs/verification/installer-2026-09-20-secure-boot.json) and [firmware screenshot](docs/verification/installer-2026-09-20-secure-boot.png).

## Multipart release verification


The same ISO was split into three assets of 1,992,294,400, 1,992,294,400, and 1,062,443,008 bytes. The packager checked the original ISO checksum before writing the part manifest.

Both Windows PowerShell 5.1 and Git Bash downloaded all three full-size parts from a local HTTP server, checked their individual SHA-256 hashes, and reconstructed the ISO with the original checksum above. The small regression fixture also passed in PowerShell 7, PowerShell 5.1, and Git Bash, including cached-part reuse and rejection of missing parts, truncated parts, duplicate or unexpected filenames, a wrong whole-image checksum, and an existing mismatched ISO.

The downloader regression suite also [passed on GitHub-hosted Linux, Windows, and macOS runners](https://github.com/agammann/kali-installer/actions/runs/35525878507). See [DOWNLOAD.md](DOWNLOAD.md) for downloading and reconstructing the release.

After publication, the release's PowerShell script was downloaded from GitHub and run under Windows PowerShell 5.1 against an empty output directory. It downloaded and verified all three public assets and reconstructed the complete ISO. An independent host SHA-256 calculation matched the original build. The [public download record](docs/verification/installer-2026-09-20-download.json) records the size and checksum.

The same published release also passed [GitHub-hosted VM installation run 35527288587](https://github.com/agammann/kali-installer/actions/runs/35527288587). That run downloaded the public parts, verified reconstruction, installed the image, removed the ISO, booted the installed disk, and passed every check, including `systemctl is-system-running` returning `running`. The [hosted test results](docs/verification/installer-2026-09-20-github-vm.json) and [login screenshot](docs/verification/installer-2026-09-20-github-login.png) are retained here as permanent evidence.

## Full rebuild and publication on GitHub Actions

[Run 35526289435](https://github.com/agammann/kali-installer/actions/runs/35526289435) completed successfully on a standard GitHub-hosted Ubuntu 24.04 runner. It used the Docker build script to clone source commit `0a14287ee2402e7fa1a8d5c766ced4c5dc12ec46` from GitHub, rebuilt the full installer, reported zero broken packages, verified its checksum and BIOS/UEFI boot records, split it into release assets, verified byte-for-byte reconstruction, and published [installer-ci-35526289435-1](https://github.com/agammann/kali-installer/releases/tag/installer-ci-35526289435-1).

This CI-built ISO is 5,047,031,808 bytes with SHA-256 `7f996450fb7ffc03a1188ab003c9046c6883e01486c4b60033a46926420b5450`. It is a separate build from the local image above; checksums are recorded separately. The [CI build record](docs/verification/installer-ci-35526289435-build.json) includes the source, package versions, part sizes, and GitHub asset digests.

The CI-built release then passed [hosted VM installation run 35527558096](https://github.com/agammann/kali-installer/actions/runs/35527558096). That independent runner downloaded the published parts, reconstructed and checked this exact ISO, completed installation, and booted the installed disk without installation media. Password login, selected packages, package consistency, system startup health, the desktop service, DNS, and HTTPS all passed. See the [CI image's installation results](docs/verification/installer-ci-35526289435-vm.json) and [graphical login screenshot](docs/verification/installer-ci-35526289435-login.png). These are also attached to its release, along with the matching build log.

The same CI-built image also passed [hosted UEFI installation run 35531086332](https://github.com/agammann/kali-installer/actions/runs/35531086332), using the test harness from commit `8d997a1f8539b1cd0dc59868e5f33fe5341651d9`. All 15 checks passed after booting the installed disk without the ISO: the guest reported UEFI, `/dev/vda1` mounted as the FAT EFI system partition, `/dev/vda2` as the ext4 root filesystem, the GRUB EFI package installed, and system state `running`. The [hosted UEFI results](docs/verification/installer-ci-35526289435-uefi-vm.json) and [login screenshot](docs/verification/installer-ci-35526289435-uefi-login.png) retain the evidence. Secure Boot was disabled.

Both published images therefore have complete SeaBIOS and UEFI installation and first-boot results. The GitHub-built image additionally demonstrates the full build, publication, download, and installation path without requiring the maintainer's PC. Future builds still need their own installation checks because their contents and checksums can change. Secure Boot is unsupported; use BIOS or UEFI with Secure Boot disabled. Physical-PC compatibility has not been tested.
