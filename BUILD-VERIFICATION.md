# Full installer build verification

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
| First boot without ISO | Passed; root filesystem `/dev/vda1` on ext4 |
| Created account password login | Passed over the VM's loopback-only SSH forwarding |
| Xfce desktop service and login screen | Passed; screenshot recorded |
| Selected packages and package consistency | `kali-linux-default`, `kali-desktop-xfce`, and `openssh-server` fully installed; `dpkg --audit` empty |
| Networking | DHCP address, default route, DNS, and HTTPS request passed |

The rebuild writes `kali-linux-rolling-installer-amd64.iso`, its build log, `SHA256SUMS`, `SOURCE_COMMIT`, and `BUILD_PACKAGES` to the chosen output directory. See the [README](README.md#rebuild-from-github-in-docker) for the command and prerequisites.

The complete installation test ran in QEMU 11.1 with KVM, SeaBIOS, 4 GiB RAM, four virtual CPUs, and a new 64 GiB disk. The installer used the kernel and initrd extracted from this ISO, with the original ISO attached as its package source. After installation powered off, the VM booted its installed disk with the ISO and external kernel/initrd removed. The installed system reported Kali 2026.3. The selected desktop and default package metapackages were version 2026.3.9.

See the [recorded VM results](docs/verification/installer-2026-09-20-vm.json), [graphical login screenshot](docs/verification/installer-2026-09-20-login.png), and [repeatable test instructions](VM-TESTING.md). Separate normal ISO boot checks reached the graphical installer through both [SeaBIOS](docs/verification/installer-2026-09-20-bios-start.png) and [OVMF UEFI](docs/verification/installer-2026-09-20-uefi-start.png), with the [UEFI boot menu](docs/verification/installer-2026-09-20-uefi-menu.png) also recorded. These checks attached only the original ISO and no virtual hard disk. A complete UEFI installation and physical hardware remain untested. Kali's rolling mirror changes over time, so a later run may produce a different ISO and checksum even from the same source commit; installation results apply to the exact checksum above.

## Multipart release verification

The same ISO was split into three assets of 1,992,294,400, 1,992,294,400, and 1,062,443,008 bytes. The packager checked the original ISO checksum before writing the part manifest.

Both Windows PowerShell 5.1 and Git Bash downloaded all three full-size parts from a local HTTP server, checked their individual SHA-256 hashes, and reconstructed the ISO with the original checksum above. The small regression fixture also passed in PowerShell 7, PowerShell 5.1, and Git Bash, including cached-part reuse and rejection of missing parts, truncated parts, duplicate or unexpected filenames, a wrong whole-image checksum, and an existing mismatched ISO.

The downloader regression suite also [passed on GitHub-hosted Linux, Windows, and macOS runners](https://github.com/agammann/kali-installer/actions/runs/35525878507). See [DOWNLOAD.md](DOWNLOAD.md) for downloading and reconstructing the release.
