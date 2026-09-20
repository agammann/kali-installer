# Kali installer image build scripts

This is an independent GitHub import of the [Kali installer build scripts](https://gitlab.com/kalilinux/build-scripts/kali-installer). The GitLab project is the upstream source; this repository preserves its commit history and is not an official Kali release. It builds an **installer ISO** for a PC. If you want an image that boots into a live desktop without installing, use [kali-live](https://gitlab.com/kalilinux/build-scripts/kali-live).

The installer uses [Simple-CDD](https://wiki.debian.org/Simple-CDD) and `debian-cd`. Kali's [custom ISO guide](https://www.kali.org/docs/development/live-build-a-custom-kali-iso/) describes the upstream build process and options.

For the prebuilt full installer, use the [GitHub Release download instructions](DOWNLOAD.md). The Windows and Bash scripts download three parts and verify the reconstructed ISO. The release is a preview pending a complete VM installation test.

## Build an amd64 PC installer

Build on a Kali Linux system with enough free space for the downloaded package mirror and ISO. A Kali virtual machine or container is suitable for building; test the resulting ISO in a separate virtual machine before installing it on a PC.

```sh
sudo apt update
sudo apt install -y ca-certificates git simple-cdd debian-cd curl xorriso cpio mtools dosfstools isolinux
git clone https://github.com/agammann/kali-installer.git
cd kali-installer
./build.sh --arch amd64 --verbose
```

The script reports the path to the ISO under `images/` when it finishes. It also saves a build log there. Check the output and record a checksum:

```sh
ls -lh images/*.iso
sha256sum images/*.iso
git rev-parse HEAD
dpkg-query -W cpio debian-cd dosfstools isolinux mtools simple-cdd xorriso
```

The build needs an `xorrisofs` binary compiled with `libjte` (Jigdo Template Extraction). The script checks this before downloading the image's packages. If the check fails, install a compatible `xorriso` package. The `xorrisofs -version` output should contain a `libjte` line.

The default build uses `kali-rolling`, so repeating the commands at a later date can select different package versions. Record the source commit, build environment, package versions, ISO hash, and build log for each image. Kali also documents [building from `kali-last-snapshot`](https://www.kali.org/docs/development/live-build-a-custom-kali-iso/#re-building-the-latest-kali-image) when you need to target a specific release. These steps make the build traceable; they do not promise a bit-for-bit identical ISO.

### Rebuild from GitHub in Docker

On a Linux host, in WSL with Docker available, or in Git Bash on Windows with Docker Desktop, clone this GitHub repository and run:

```sh
./scripts/rebuild-from-github.sh
```

The script builds a Kali container, clones the source **from GitHub inside that container**, and makes a full `amd64` installer ISO. This also avoids Windows checkout differences in executable bits and symlinks. It writes the ISO, build log, SHA-256 checksum, source commit, and build-package versions to `rebuild-output/`. You can pass an output directory and a Git ref (commit, tag, or `origin/main`) as arguments:

```sh
./scripts/rebuild-from-github.sh /path/to/output origin/main
```

The container still downloads Kali packages from Kali's package mirror. Allow substantial free disk space for the mirror, temporary build files, and output ISO. The Dockerfile pins the base-image digest, but Kali's rolling package mirror changes over time; keep the recorded build inputs when comparing results.

For WSL, enable Docker Desktop's [integration for your distribution](https://docs.docker.com/desktop/features/wsl/) before running the command. Git Bash can use Docker Desktop's Windows CLI without that integration.

The [full build verification](BUILD-VERIFICATION.md) records a successful GitHub-source rebuild and its checksum. It does not replace an installation test in a virtual machine.

### Rebuild on GitHub Actions

Open [Full installer rebuild](https://github.com/agammann/kali-installer/actions/workflows/rebuild.yml), select **Run workflow**, and choose whether to publish the rebuilt ISO as a multipart preview release. The workflow also runs when installer sources or build configuration change on `main`. It uses a standard Ubuntu GitHub-hosted runner and the same Docker build script, pinned to the workflow's source commit.

Every run records its build logs, source commit, build-package versions, ISO checksum, and boot-record report in a `build-evidence` artifact retained for 14 days. It verifies the split parts reconstruct the original bytes. When publication is enabled, it uploads the parts and downloader scripts to a separate `installer-ci-...` preview release. Each release's scripts select that build by default. Without publication enabled, the ISO is discarded when the runner finishes; the evidence remains available.

The workflow has a three-hour limit and checks available disk space before building. It does not perform a VM installation. Each freshly rebuilt ISO needs its own installation test before being promoted from preview. Downloader regression checks run separately on Linux, Windows, and macOS.

Do not commit an ISO or its parts to Git. GitHub blocks files over 100 MiB in Git and limits each Release asset to under 2 GiB. This repository distributes the full ISO as three Release assets, each at most 1,900 MiB, with scripts that verify and join them. See [download and packaging instructions](DOWNLOAD.md), [GitHub's repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits), and [Release asset limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).

## Test before use

Boot the ISO in a disposable virtual machine. Complete an installation, then check that the new system boots, accepts the account created during setup, has working networking, and includes the packages you selected. Kali's [ISO testing guide](https://www.kali.org/docs/development/live-build-a-custom-kali-iso/#testing-built-image) gives QEMU commands for BIOS and UEFI testing. A successful ISO build by itself does not prove that an installation works.

## Customize the installer

- Add packages to `kali-config/installer-default/packages`. If they must also be installed into the target system, review `simple-cdd/profiles/kali.postinst`.
- Use `./build.sh --variant netinst --arch amd64 --verbose` for a smaller network installer, or `--variant everything` for the broad package set. Run `./build.sh --help` for all options.
- Keep credentials, private keys, and personal files out of the repository and ISO.

If you add files with `all_extras` in `simple-cdd/simple-cdd.conf`, they are placed under `/simple-cdd` on the ISO. The `kali.postinst` profile script runs in the installed system's context, so it cannot access the installer's mounted media by trying to mount `/dev/sr0` again. Debian Installer exposes the mounted media at `/cdrom` and the target filesystem at `/target` **in the installer environment**. Use a `preseed/late_command` in a custom preseed to copy your extra files before the installer finishes. For example, if `all_extras` includes a directory named `my-files`:

```text
d-i preseed/late_command string mkdir -p /target/opt/my-files; cp -a /cdrom/simple-cdd/my-files/. /target/opt/my-files/
```

Test that customization in a virtual machine; it has not been validated for every install path in this fork. See [Debian's installer command documentation](https://www.debian.org/releases/stable/amd64/apbs05.en.html) and [upstream issue #5](https://gitlab.com/kalilinux/build-scripts/kali-installer/-/work_items/5).

## Source, issues, and licensing

The source of this import is [Kali's GitLab repository](https://gitlab.com/kalilinux/build-scripts/kali-installer). For bugs in this copy, use this repository's GitHub Issues; for upstream bugs, use the GitLab project. Review [Kali's open source policy](https://www.kali.org/docs/policy/kali-linux-open-source-policy/) and the licenses of packages you add before redistributing an image. The upstream `main` branch does not currently include a repository-level `LICENSE` file, so this copy does not invent one.
