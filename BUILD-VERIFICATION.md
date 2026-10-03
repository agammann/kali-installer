# Full installer build verification

Verification applies to the exact ISO checksum. The September 20 images below passed BIOS and UEFI VM installations and first disk boots with installation media removed. The latest October 2 preview also has passing BIOS and UEFI runs, with an earlier unexplained UEFI filesystem failure retained in its record. Previous October 2 candidates failed separate installation or startup checks. Use BIOS or UEFI with Secure Boot disabled; physical-PC compatibility is not established by these VM results.

| September 20 release | Verified ISO SHA-256 |
| --- | --- |
| [Local build: installer-2026-09-20](https://github.com/agammann/kali-installer/releases/tag/installer-2026-09-20) | `c104e3f427d074f5fda666bf10f24ace9c9dd52f857ed0dcf4d95ced7a6ac026` |
| [GitHub build: installer-ci-35526289435-1](https://github.com/agammann/kali-installer/releases/tag/installer-ci-35526289435-1) | `7f996450fb7ffc03a1188ab003c9046c6883e01486c4b60033a46926420b5450` |

## October 2 candidate installation failure

[Build 37003501967](https://github.com/agammann/kali-installer/actions/runs/37003501967) produced candidate `installer-ci-37003501967-1` from source `8d9960d3278e8b1ba951519ed2d7252bfd4bd432`. Its 5,047,031,808-byte ISO has SHA-256 `19d6c81693e253b4560b92b847d3d62b46ded93f7d77c88ca64c927860a50ab0`. The published parts downloaded and reconstructed with that checksum, but both the [BIOS installation](https://github.com/agammann/kali-installer/actions/runs/37005476955) and [UEFI installation](https://github.com/agammann/kali-installer/actions/runs/37005477128) stopped at base installation with `Debootstrap warning` reporting `gcc-16-base_16.2.0-1_amd64.deb` as corrupt. Neither run completed installation or reached the installed-disk checks. Do not use this candidate for installation.

The package's actual size, 37,984 bytes, and SHA-256, `2c83b8b5a3ebe4431ca1f8f20370af04f8e80ca5a8726afd56f3fa1523f83e16`, match its `Packages` record. The failure came from checksum metadata: `debian-cd` 3.2.3 wrote a SHA512 section in `Release`, while the package records supplied SHA256 without SHA512. The embedded `debootstrap` 1.0.145 selected SHA512 and could not obtain that package digest.

The build now applies [upstream debian-cd commit 7df98e9](https://salsa.debian.org/images-team/debian-cd/-/commit/7df98e9fbc4b97d67073f0de6ca47820e725a81a) to its private build-tool copy. This removes the three lines generating the SHA512 `Release` section and preserves SHA256 verification. A replay using the actual package, package index, and embedded debootstrap functions rejected the original metadata and accepted the corrected metadata. An incorrect SHA-256 was still rejected. The installation harness also detects this fatal prompt instead of waiting for its full timeout.

### Corrected October 2 build

[Rebuild 37062982297](https://github.com/agammann/kali-installer/actions/runs/37062982297) completed from source `f45dd5729fa436236189353d81ac794dc5bccc13` and published [installer-ci-37062982297-1](https://github.com/agammann/kali-installer/releases/tag/installer-ci-37062982297-1). The 5,047,031,808-byte ISO has SHA-256 `8f5c9d2724440101b582fce8bad6730972fc8c113e883d033947e6fb312a7261`.

An independent download verified all three part hashes and the complete image hash. Its actual `Release` file no longer advertises SHA512. All five package indexes match their `Release` SHA256 and size records, and all 3,966 indexed package files, totaling 4,890,926,318 bytes, match their recorded SHA256 and size. See the [media verification record](docs/verification/installer-ci-37062982297-media.json).

[Original-ISO boot run 37065821566](https://github.com/agammann/kali-installer/actions/runs/37065821566) passed in BIOS and UEFI with QEMU 8.2.2 and KVM. The original firmware menus reached graphical language selection in 22.35 seconds and 17.14 seconds respectively, with no virtual hard disk, network device, or external kernel/initrd. Both runs verified the image hash before and after boot. The retained [BIOS result](docs/verification/installer-ci-37062982297-bios-boot.json), [BIOS menu](docs/verification/installer-ci-37062982297-bios-menu.png), [BIOS language page](docs/verification/installer-ci-37062982297-bios-language.png), [UEFI result](docs/verification/installer-ci-37062982297-uefi-boot.json), [UEFI menu](docs/verification/installer-ci-37062982297-uefi-menu.png), and [UEFI language page](docs/verification/installer-ci-37062982297-uefi-language.png) cover entry into the installer. Secure Boot was disabled.

Both [BIOS installation 37065844220](https://github.com/agammann/kali-installer/actions/runs/37065844220) and [UEFI installation 37065847468](https://github.com/agammann/kali-installer/actions/runs/37065847468) completed installation and booted the installed virtual disk with the ISO, external kernel, and initrd detached. Created-account password login, selected packages, an empty `dpkg --audit`, the desktop service, DNS, and HTTPS passed. The UEFI run also passed its EFI partition and bootloader checks.

The final system-health gate failed in both runs: `systemctl is-system-running --wait` returned `degraded` with exit status 1. BIOS passed 12 of 13 checks and UEFI passed 14 of 15. A [BIOS diagnostic rerun](https://github.com/agammann/kali-installer/actions/runs/37068260988) identified one failed unit, `user@967.service`: the LightDM greeter's user manager exited at PAM setup because the `lightdm` account had expired. This candidate remains a preview and has not passed the complete verification suite.

These unattended installation runs use the ISO's kernel and initrd with a test preseed. They did not pass the original menu's Simple-CDD profile arguments, so they do not verify execution of the custom profile's postinstall script. Profile coverage was corrected for the later [LightDM and profile-corrected preview](#lightdm-and-profile-corrected-preview), whose results apply to its own ISO checksum. The original-menu boot checks above only reach language selection.

### LightDM and profile-corrected preview

[Build 37071997083](https://github.com/agammann/kali-installer/actions/runs/37071997083) produced [installer-ci-37071997083-1](https://github.com/agammann/kali-installer/releases/tag/installer-ci-37071997083-1) from source `e6644a741849d387ba192eca5fe3a6eb38c88f1f`. Its 5,047,031,808-byte ISO has SHA-256 `63cb32037e6d8c4e590f8f8f727aecddedab7fd131f0b92eb5895373b50227df`.

The image retains SHA256 package verification and applies a guarded correction for LightDM 1.33.1-2 and 1.33.1-3: only the known packaged `!*` password, expired account, and `/bin/false` shell combination permits clearing the account expiry. The password stays locked and the shell stays disabled. This allows the greeter's PAM-managed user service to start.

The downloaded release passed all three part hashes and the complete ISO hash. All five package indexes and all 3,966 indexed packages, totaling 4,890,926,318 bytes, match their recorded SHA256 and size. The embedded executable `kali.postinst` matches the reviewed source hash `400638c945a1cb9f1ab93618bca1c28797748b95c95f2020baedd4b4d032f3a1`. The published Windows PowerShell 5.1 downloader reassembled the downloaded parts into the complete image, whose independently calculated hash matched. The published Bash downloader verified the cached image. See the [media verification record](docs/verification/installer-ci-37071997083-media.json).

[Original-ISO boot run 37074479441](https://github.com/agammann/kali-installer/actions/runs/37074479441) passed in both firmware modes. The BIOS menu appeared at 1.02 seconds and reached graphical language selection at 12.57 seconds; UEFI reached those stages at 14.20 and 23.34 seconds. Each run attached only the original ISO, with no virtual hard disk, network device, or external kernel/initrd, and checked the same hash before and after boot. See the [BIOS result](docs/verification/installer-ci-37071997083-bios-boot.json), [menu](docs/verification/installer-ci-37071997083-bios-menu.png), [language screen](docs/verification/installer-ci-37071997083-bios-language.png), [UEFI result](docs/verification/installer-ci-37071997083-uefi-boot.json), [menu](docs/verification/installer-ci-37071997083-uefi-menu.png), and [language screen](docs/verification/installer-ci-37071997083-uefi-language.png).

The unattended installation harness now passes the original menu's `preseed/file`, `simple-cdd/profiles=kali,offline`, and `desktop=xfce` arguments, with early locale answers before the test preseed loads. Installed-system checks verify the copied postinstall script's hash, the Kali APT source, and the created user's `adm`, `dialout`, `kaboxer`, and `wireshark` groups.

| Complete installation and disk boot | Harness source | Recorded command results |
| --- | --- | --- |
| [BIOS 37074059050](https://github.com/agammann/kali-installer/actions/runs/37074059050) | `e6644a741849d387ba192eca5fe3a6eb38c88f1f` | 16 of 16 exited successfully |
| [UEFI 37076659707](https://github.com/agammann/kali-installer/actions/runs/37076659707) | `5b4d9b6623822b12a67d1180862e54f64203990b` | 18 of 18 exited successfully |

Both runs completed installation to a new 64 GiB disk, powered off, and booted from that disk with the ISO and external kernel/initrd detached. SSH password login, selected packages, an empty `dpkg --audit`, system state `running`, networking, the display manager, and the greeter's user manager passed. The LightDM account had a locked password, `/bin/false`, and no expiry. UEFI additionally verified the EFI runtime, FAT EFI system partition, and installed GRUB EFI package. The [BIOS results](docs/verification/installer-ci-37071997083-bios-vm.json), [BIOS greeter](docs/verification/installer-ci-37071997083-bios-greeter.png), [UEFI results](docs/verification/installer-ci-37071997083-uefi-vm.json), and [UEFI greeter](docs/verification/installer-ci-37071997083-uefi-greeter.png) retain the evidence.

The counts include four informational commands for user identity, OS release, system inventory, and network inventory; all command exit statuses are checked. The captured OS release identifies Kali. A later one-operator harness correction makes a wrong OS ID fail instead of allowing the following `cat` command to mask it; that correction is separate from these recorded VM runs.

An earlier [UEFI run 37074287101](https://github.com/agammann/kali-installer/actions/runs/37074287101) on this exact ISO passed 15 of 18 commands but ended with system state `degraded`, the display manager still activating, and the greeter user manager inactive. Several services reported read-only filesystem errors under `/var/lib`, `/var/log`, and `/var/cache`. The Kali profile and locked LightDM account checks passed in that failed run. See its [results](docs/verification/installer-ci-37071997083-uefi-failure.json), [service diagnostics](docs/verification/installer-ci-37071997083-uefi-failure-health.json), and [console screen](docs/verification/installer-ci-37071997083-uefi-failure-console.png).

The subsequent diagnostic run added only read-only evidence collection after a health failure; all 18 commands, installation timing, and failure assertions were unchanged. It passed without an image change, remount, service restart, or reset of failed units. The earlier failure did not recur and remains unexplained. The added failure-only diagnostics therefore did not run. This image remains a preview; these results do not establish that the earlier filesystem failure has been repaired.

The earlier screenshots linked above show the LightDM login screen, not an authenticated graphical desktop. Password login in those runs was tested through SSH. Secure Boot was disabled; physical hardware, every installation option, and interactive desktop use were outside those checks.

### October 3 authenticated desktop check

[UEFI run 37110160868](https://github.com/agammann/kali-installer/actions/runs/37110160868) completed successfully on October 3 using harness commit `c303a8df4988e5fbf26902393e1244c6fceb5cc9` and the unchanged `installer-ci-37071997083-1` ISO, SHA-256 `63cb32037e6d8c4e590f8f8f727aecddedab7fd131f0b92eb5895373b50227df`. It installed to a new 64 GiB UEFI disk and booted that disk without the ISO. The downloaded results record all 18 installed-system commands exiting successfully, including password login, selected packages, package consistency, desktop service, DNS, and HTTPS. The graphical record shows one LightDM credential submission followed by two observations of the same active local X11 user session on `seat0`, display `:0`, with both `xfce4-session` and `xfce4-panel` running.

The opt-in graphical phase requires the created account to have a stable active local X11 user session on `seat0`, with both `xfce4-session` and `xfce4-panel` running. It allows one credential submission within 120 seconds. It does not exercise desktop applications or every interactive workflow. See [how to run this check](VM-TESTING.md).

The [first attempt, 37108419882](https://github.com/agammann/kali-installer/actions/runs/37108419882), passed the 18 installed-system commands but stopped before entering any credentials. Its screenshot helper retained an open QMP stream before the graphical phase opened another connection. The corrected harness closes that stream and records QMP connection setup separately; the image and acceptance requirements were unchanged.

The downloaded `vm-installation-evidence-37110160868.zip` is 1,187,510 bytes; SHA-256 `c36b73ed104509b5b3c402c6dae29b8440ca43eeb99918b36f23cd345c702ca6` matches the digest published with the run. Its session record, results, and both 1280×800 screenshots were inspected: the initial image shows the greeter, while the authenticated image shows the XFCE panel and Kali desktop icons. The authenticated screenshot SHA-256 is `1c59c3aed7760072865fc2c8fcc297ddbb04d72268d542cddec0a966a57859ee`, matching the session record. This image remains a preview. The earlier unexplained read-only filesystem failure remains in the record, and this run does not establish its resolution, Secure Boot support, or physical-hardware compatibility.

## September 20 local build and installation

An [independent rebuild and installation of the unmodified GitLab source](UPSTREAM-COMPARISON.md) also passed on September 20. Installer configuration, package files, and boot executables matched the compared fork images; differences in generated files were checked and traced to timestamps and archive metadata. The reference VM passed the same 15 checks, with matching installed-system identity, package versions, filesystem layout, and startup state.

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

The tested images require Secure Boot to be disabled, consistent with [Kali's installation guide](https://www.kali.org/docs/installation/hard-disk-install/#preparing-for-the-installation). The `installer-2026-09-20` ISO was also checked in QEMU with OVMF Secure Boot enabled and Microsoft certificates enrolled. Firmware rejected the ISO before the installer started, reporting `Access Denied -- rejected probably by Secure Boot`. This is an unsupported boot configuration, not a successful installation test. The check attached no hard disks and no network devices. See the [recorded environment and result](docs/verification/installer-2026-09-20-secure-boot.json) and [firmware screenshot](docs/verification/installer-2026-09-20-secure-boot.png).

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

These two September 20 images therefore have complete SeaBIOS and UEFI installation and first-boot results. The GitHub-built image additionally demonstrates the full build, publication, download, and installation path without requiring the maintainer's PC. Those results do not cover other release images; each different ISO checksum needs its own installation checks. Secure Boot is unsupported for the tested images. Physical-PC compatibility has not been tested.
