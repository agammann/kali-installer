#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
output_dir=${1:-"$repo_dir/rebuild-output"}
source_ref=${2:-origin/main}

mkdir -p -- "$output_dir"
output_dir=$(cd -- "$output_dir" && pwd)

docker build --platform linux/amd64 -t kali-installer-builder:local "$repo_dir"
docker run --rm \
  --platform linux/amd64 \
  --mount "type=bind,source=$output_dir,target=/out" \
  --env "SOURCE_REF=$source_ref" \
  kali-installer-builder:local \
  bash -euo pipefail -c '
    git clone https://github.com/agammann/kali-installer.git /build/kali-installer
    cd /build/kali-installer
    git checkout --detach "$SOURCE_REF"
    ./build.sh --arch amd64 --verbose
    iso=$(find images -maxdepth 1 -type f -name "*.iso" -print -quit)
    test -n "$iso"
    cp "$iso" images/*.log /out/
    (cd /out && sha256sum "$(basename "$iso")" > SHA256SUMS && sha256sum -c SHA256SUMS)
    git rev-parse HEAD > /out/SOURCE_COMMIT
    dpkg-query -W cpio debian-cd dosfstools isolinux mtools simple-cdd xorriso > /out/BUILD_PACKAGES
  '
