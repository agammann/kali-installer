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

The rebuild writes `kali-linux-rolling-installer-amd64.iso`, its build log, `SHA256SUMS`, `SOURCE_COMMIT`, and `BUILD_PACKAGES` to the chosen output directory. See the [README](README.md#rebuild-from-github-in-docker) for the command and prerequisites.

This verifies that the ISO builds and contains boot records. A complete installation and first boot in a virtual machine have not yet been tested. Kali's rolling mirror changes over time, so a later run may produce a different ISO and checksum even from the same source commit.

## Multipart release verification

The same ISO was split into three assets of 1,992,294,400, 1,992,294,400, and 1,062,443,008 bytes. The packager checked the original ISO checksum before writing the part manifest.

Both Windows PowerShell 5.1 and Git Bash downloaded all three full-size parts from a local HTTP server, checked their individual SHA-256 hashes, and reconstructed the ISO with the original checksum above. The small regression fixture also passed in PowerShell 7, PowerShell 5.1, and Git Bash, including cached-part reuse and rejection of missing parts, truncated parts, duplicate or unexpected filenames, a wrong whole-image checksum, and an existing mismatched ISO.

These are distribution checks; they do not change the installation-test status above. See [DOWNLOAD.md](DOWNLOAD.md) for downloading and reconstructing the release.
