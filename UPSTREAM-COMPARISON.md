# Comparison with the GitLab installer source

On 2026-09-20, GitLab's current `main` was commit [`6108f92826417d0c474abd793fde946e3dfa85f9`](https://gitlab.com/kalilinux/build-scripts/kali-installer/-/commit/6108f92826417d0c474abd793fde946e3dfa85f9), the same revision imported into this repository. We built that unmodified revision separately in the same Docker builder used for the fork. The build and package-consistency check passed, and the resulting ISO checksum verified.

GitLab's public API returned no pipeline results for this branch. This record therefore uses our own reference build and tests; it does not assume a maintainer test result that was unavailable.

The [reference build record](docs/verification/upstream-6108f928-build.json) contains the source revision, builder image, package versions, ISO hash, and build-log hash. The [full build log](https://github.com/agammann/kali-installer/releases/download/installer-2026-09-20/upstream-6108f928-build.log) is attached to the release.

## Source comparison

Both published fork builds have exactly the same Git objects as upstream for `kali-config/`, `simple-cdd/`, and `.getopt.sh`. This includes the package lists, preseeds, boot theme, and installation hooks. The fork's `build.sh` changes resolve and quote paths, reject an unknown variant early, and check the required `xorrisofs`/`libjte` capability before building. The valid default installer's configuration is unchanged.

The Docker builder's seven recorded build-tool versions also matched. See the [source and tool comparison](docs/verification/upstream-6108f928-source-comparison.json).

## Image comparison

The upstream reference and original published fork image are both 5,047,031,808 bytes. Their whole-image hashes differ because the builds contain generated metadata:

| Image | SHA-256 |
| --- | --- |
| Unmodified GitLab reference | `ed319afc1d5006130664c9290ae7b94445f8f245c5ee66a60fa6181ecb2bd765` |
| Published `installer-2026-09-20` | `c104e3f427d074f5fda666bf10f24ace9c9dd52f857ed0dcf4d95ced7a6ac026` |

All **3,964 package-file entries** match in the ISOs' provided MD5 manifests. Of 4,048 unique manifest paths, 4,044 match directly, with no added or missing files. Independent SHA-256 hashes also match for the installer kernel, text-mode initrd, and both EFI executables.

The four remaining file differences were inspected:

| File | Verified difference |
| --- | --- |
| `.disk/info` | Build date/time in the image description |
| `dists/kali-rolling/Release` | `Date` field only |
| `boot/grub/efi.img` | 48 bytes in FAT creation/modification time fields; all contained boot files match by SHA-256 |
| `install.amd/gtk/initrd.gz` | Archive inode numbers and timestamps; all 4,868 entries have matching contents, permissions, ownership, and other metadata |

Both manifests repeat `README.html` and `README.txt` with identical hashes; these repetitions were checked and counted once. See the [full comparison record](docs/verification/upstream-6108f928-image-comparison.json). This is evidence of matching installer content for these exact builds, not a claim of bit-for-bit reproducible ISO generation.

## Installation comparison

The unmodified upstream reference passed a complete UEFI installation to a new virtual disk and then booted that disk with the ISO removed. All 15 checks passed, including created-account login, EFI runtime support, EFI system partition, GRUB EFI installation, selected packages, package consistency, system startup, desktop service, DNS, and HTTPS. See the [reference VM results](docs/verification/upstream-6108f928-uefi-vm.json) and [login screenshot](docs/verification/upstream-6108f928-uefi-login.png).

The installed operating-system identity, selected package versions, root filesystem, EFI partition, firmware mode, bootloader status, package audit, and system startup state matched the original fork's UEFI test outputs. The published fork images also passed complete BIOS installations and disk-only first boots, as recorded in [BUILD-VERIFICATION.md](BUILD-VERIFICATION.md). This comparison supports deployment in the tested BIOS/UEFI configuration with Secure Boot disabled; no physical installation was performed.

## Repeat the reference build from GitHub

The upstream commit is preserved in this GitHub repository's history. From this checkout, the same Docker wrapper can build it without fetching from GitLab:

```sh
./scripts/rebuild-from-github.sh "$PWD/reference-output" 6108f92826417d0c474abd793fde946e3dfa85f9
```

Use the [VM test instructions](VM-TESTING.md) with that output ISO and its recorded checksum. Select `--firmware uefi` and a fresh output directory. Kali's rolling package mirror can change between runs, so record new checksums and compare contents again. Secure Boot must be disabled. No physical installation is required for this repository's VM-based deployment verification.
