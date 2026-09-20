#!/usr/bin/env python3
"""Split the verified installer into GitHub Release assets without changing bytes."""
import argparse
import hashlib
from pathlib import Path
import re

ISO_NAME = "kali-linux-rolling-installer-amd64.iso"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--part-mib", type=int, default=1900)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        parser.error("expected SHA-256 must be 64 lowercase hexadecimal characters")
    if not 1 <= args.part_mib <= 1900:
        parser.error("part size must be between 1 and 1900 MiB")
    if not args.iso.is_file() or args.iso.stat().st_size == 0:
        parser.error("ISO must be a nonempty file")
    part_size = args.part_mib * 1024 * 1024
    if (args.iso.stat().st_size + part_size - 1) // part_size > 999:
        parser.error("too many parts; increase --part-mib")
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        parser.error("output directory must be empty to avoid mixing releases")

    whole = hashlib.sha256()
    entries = []
    with args.iso.open("rb") as source:
        index = 1
        while True:
            block = source.read(min(8 * 1024 * 1024, part_size))
            if not block:
                break
            name = f"{ISO_NAME}.part{index:03d}"
            digest = hashlib.sha256()
            written = 0
            with (args.output / name).open("xb") as part:
                while block:
                    part.write(block)
                    whole.update(block)
                    digest.update(block)
                    written += len(block)
                    if written == part_size:
                        break
                    block = source.read(min(8 * 1024 * 1024, part_size - written))
            entries.append((digest.hexdigest(), name))
            print(f"{name}: {written} bytes", flush=True)
            index += 1

    if whole.hexdigest() != args.expected_sha256:
        raise SystemExit("ISO checksum mismatch; no release manifest was written")
    entries.insert(0, (whole.hexdigest(), ISO_NAME))
    with (args.output / "SHA256SUMS").open("x", encoding="ascii", newline="\n") as manifest:
        for digest, name in entries:
            manifest.write(f"{digest}  {name}\n")
    print("Verified original ISO; release parts and SHA256SUMS are ready.")


if __name__ == "__main__":
    main()
