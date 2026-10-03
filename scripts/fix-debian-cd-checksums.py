#!/usr/bin/env python3
"""Backport debian-cd's Release checksum fix to the private build copy.

debian-cd 3.2.3 advertises SHA512 in Release even though its Packages records
only include SHA256. debootstrap 1.0.145 then rejects valid packages.
Upstream fix: https://salsa.debian.org/images-team/debian-cd/-/commit/7df98e9fbc4b97d67073f0de6ca47820e725a81a
"""
from pathlib import Path
import sys


def fix(path: Path) -> None:
    source = path.read_text()
    start = source.index('sub checksum_files_for_release {')
    end = source.index('\n}', start) + 1
    section = source[start:end]
    sha256 = ('\tprint RELEASE "SHA256:\\n";\n'
              '\t$current_checksum_type = "sha256";\n'
              '\tfind (\\&find_and_checksum_files_for_release, ".");\n')
    sha512 = sha256.replace('256', '512')
    if section.count(sha256) != 1:
        raise ValueError('Unexpected debian-cd checksum function; SHA256 must remain intact')
    if section.count(sha512) == 1:
        updated = section.replace(sha512, '')
        if 'sha512' in updated.lower():
            raise ValueError('Unexpected additional SHA512 handling in debian-cd')
        path.write_text(source[:start] + updated + source[end:])
    elif 'sha512' in section.lower():
        raise ValueError('Unrecognized debian-cd SHA512 handling; review the upstream fix')


if __name__ == '__main__':
    fix(Path(sys.argv[1]))
