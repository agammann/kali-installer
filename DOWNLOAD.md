# Download the full installer

The [installer-2026-09-20 preview release](https://github.com/agammann/kali-installer/releases/tag/installer-2026-09-20) distributes the complete amd64 installer as three parts. Each part is below GitHub's 2 GiB asset limit. Joining the parts restores the original ISO without compression or changes to its contents.

The installer is ready to install in the tested BIOS and UEFI configurations. The full ISO build, package consistency checks, complete VM installations, and first boots with the ISO removed passed; see [BUILD-VERIFICATION.md](BUILD-VERIFICATION.md). **Secure Boot must be disabled:** these images do not support it, consistent with [Kali's installation requirements](https://www.kali.org/docs/installation/hard-disk-install/#preparing-for-the-installation). Physical-PC compatibility has not been tested. This is an independent preview build, not an official Kali release.

## Automatic download and verification

The [upstream comparison](UPSTREAM-COMPARISON.md) records a successful unmodified GitLab rebuild and VM installation, with matching installer configuration, package files, and boot content.

Allow at least 11 GB of free disk space for the downloaded parts and assembled ISO. Use a filesystem that supports files larger than 4 GB, such as NTFS, APFS, or ext4; FAT32 cannot hold this ISO.

Download the script for your operating system from the release, review it, and run it. Each script downloads `SHA256SUMS` and the three parts, verifies each part, joins them, and verifies the complete ISO. Existing verified parts are reused after an interrupted run. A completed ISO with a different checksum is never overwritten.

### Windows PowerShell

```powershell
Invoke-WebRequest -Uri 'https://github.com/agammann/kali-installer/releases/download/installer-2026-09-20/download-installer.ps1' -OutFile download-installer.ps1
Get-Content .\download-installer.ps1
powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\download-installer.ps1
```

Choose another destination with `-OutputDirectory 'D:\Kali download'`. The command sets `RemoteSigned` for this process only; it does not change your saved execution policy. If Windows marks the downloaded file as blocked, review it and use `Unblock-File .\download-installer.ps1` before running it. If your organization restricts script execution, follow its policy for running reviewed scripts.

### Linux, macOS, or Git Bash

Requires Bash, `curl`, and either `sha256sum` or `shasum`.

```sh
curl -fL https://github.com/agammann/kali-installer/releases/download/installer-2026-09-20/download-installer.sh -o download-installer.sh
cat download-installer.sh
bash download-installer.sh
```

Choose another destination with `--output '/path/to/Kali download'`.

The verified image is saved as `kali-installer-download/kali-linux-rolling-installer-amd64.iso` by default. Use that complete `.iso` with your USB-writing tool. **Do not flash the individual `.part001`, `.part002`, or `.part003` files.** You may delete the parts after the script reports that the full ISO verified successfully.

## Manual downloads or offline reassembly

Download `SHA256SUMS`, all three `.partNNN` assets, and your platform's script from the same release. Put the parts and manifest in one directory. Point the script at that directory using `-OutputDirectory` or `--output`, and add `-Offline` or `--offline`. Offline mode performs the same checks and reassembly without network access.

The full ISO for this release is 5,047,031,808 bytes. Its SHA-256 is:

```text
c104e3f427d074f5fda666bf10f24ace9c9dd52f857ed0dcf4d95ced7a6ac026
```

## Package another verified build

With Python 3, split an ISO using its independently recorded SHA-256:

```sh
python3 scripts/package-release.py rebuild-output/kali-linux-rolling-installer-amd64.iso rebuild-output/release-parts --expected-sha256 YOUR_RECORDED_SHA256
```

The output directory must be empty. The packager verifies the original ISO while writing parts of at most 1,900 MiB and writes `SHA256SUMS` only after the original checksum matches. Upload every part and the generated manifest to the same release, along with both downloader scripts and the matching build record. Use the downloaders' `--tag TAG` or `-Tag TAG` option for a different release. Never mix parts or manifests from different builds.

Run the multipart regression checks with `python3 tests/test_release_download.py`. They exercise available Bash and PowerShell clients against a small local HTTP server; `KALI_TEST_BASH` and `KALI_TEST_POWERSHELL` can select specific runtimes.
