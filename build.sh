#!/bin/bash

# If a command fails, make the whole script exit
set -e
# Use return code for any command errors in part of a pipe
set -o pipefail # Bashism

# Kali's default values
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
KALI_DIST="kali-rolling"
KALI_VERSION=""
KALI_VARIANT="default"
TARGET_DIR="$SCRIPT_DIR/images"
TARGET_SUBDIR=""
SUDO="sudo"
VERBOSE=""
DEBUG=""
HOST_ARCH=$(dpkg --print-architecture)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

image_name() {
  if [ "$KALI_VARIANT" = "netinst" ]; then
    echo "simple-cdd/images/kali-$KALI_VERSION-$KALI_ARCH-NETINST-1.iso"
  else
    echo "simple-cdd/images/kali-$KALI_VERSION-$KALI_ARCH-BD-1.iso"
  fi
}

target_image_name() {
  local arch=$1

  IMAGE_NAME="$(image_name $arch)"
  IMAGE_EXT="${IMAGE_NAME##*.}"
  if [ "$IMAGE_EXT" = "$IMAGE_NAME" ]; then
    IMAGE_EXT="img"
  fi
  if [ "$KALI_VARIANT" = "default" ]; then
    echo "${TARGET_SUBDIR:+$TARGET_SUBDIR/}kali-linux-$KALI_VERSION-installer-$KALI_ARCH.$IMAGE_EXT"
  else
    echo "${TARGET_SUBDIR:+$TARGET_SUBDIR/}kali-linux-$KALI_VERSION-installer-$KALI_VARIANT-$KALI_ARCH.$IMAGE_EXT"
  fi
}

target_build_log() {
  TARGET_IMAGE_NAME=$(target_image_name $1)
  echo ${TARGET_IMAGE_NAME%.*}.log
}

default_version() {
  case "$1" in
    kali-*)
      echo "${1#kali-}"
    ;;
    *)
      echo "$1"
    ;;
  esac
}

failure() {
  echo "Build of $KALI_DIST/$KALI_VARIANT/$KALI_ARCH installer image failed (see build.log for details)" >&2
  echo "Log: $BUILD_LOG" >&2
  exit 2
}

run_and_log() {
  if [ -n "$VERBOSE" ] || [ -n "$DEBUG" ]; then
    printf "RUNNING:" >&2
    for _ in "$@"; do
      [[ $_ =~ [[:space:]] ]] && printf " '%s'" "$_" || printf " %s" "$_"
    done >&2
    printf "\n" >&2
    "$@" 2>&1 | tee -a "$BUILD_LOG"
  else
    "$@" >>"$BUILD_LOG" 2>&1
  fi
  return $?
}

debug() {
  if [ -n "$DEBUG" ]; then
    echo "DEBUG: $*" >&2
  fi
}

clean() {
  debug "Cleaning"

  run_and_log $SUDO rm -rf "$(pwd)/simple-cdd/tmp"
  run_and_log $SUDO rm -rf "$(pwd)/simple-cdd/debian-cd"
}

print_help() {
  echo "Usage: $0 [<option>...]"
  echo
  for x in $(echo "${BUILD_OPTS_LONG}" | sed 's_,_ _g'); do
    x=$(echo $x | sed 's/:$/ <arg>/')
    echo "  --${x}"
  done
  exit 0
}

require_package() {
  local pkg=$1
  local required_version=$2
  local pkg_version=

  pkg_version=$(dpkg-query -f '${Version}' -W $pkg 2>/dev/null || true)
  if [ -z "$pkg_version" ]; then
    echo "ERROR: You need $pkg, but it is not installed" >&2
    exit 1
  fi
  if dpkg --compare-versions "$pkg_version" lt "$required_version"; then
    echo "ERROR: You need $pkg (>= $required_version), you have $pkg_version" >&2
    exit 1
  fi
  debug "$pkg version: $pkg_version"
}

require_jigdo_xorrisofs() {
  if ! command -v xorrisofs >/dev/null 2>&1; then
    echo "ERROR: You need xorrisofs (from the xorriso package) to build an installer image" >&2
    exit 1
  fi

  if ! xorrisofs -version 2>&1 | grep -q '^libjte[[:space:]]'; then
    echo "ERROR: xorrisofs was built without libjte (Jigdo Template Extraction) support" >&2
    echo "Install a xorriso package with libjte support before building the installer image" >&2
    exit 1
  fi
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Change directory into where the script is
cd "$SCRIPT_DIR"

# Allowed command line options
source .getopt.sh

# Parsing command line options (see .getopt.sh)
temp=$(getopt -o "$BUILD_OPTS_SHORT" -l "$BUILD_OPTS_LONG" -- "$@")
eval set -- "$temp"
while true; do
  case "$1" in
    -d|--distribution) KALI_DIST="$2"; shift 2; ;;
    -a|--arch) KALI_ARCH="$2"; shift 2; ;;
    -v|--verbose) VERBOSE="1"; shift 1; ;;
    -D|--debug) DEBUG="1"; shift 1; ;;
    -h|--help) print_help; ;;
    --variant) KALI_VARIANT="$2"; shift 2; ;;
    --version) KALI_VERSION="$2"; shift 2; ;;
    --subdir) TARGET_SUBDIR="$2"; shift 2; ;;
    --get-image-path) ACTION="get-image-path"; shift 1; ;;
    --clean) ACTION="clean"; shift 1; ;;
    --no-clean) NO_CLEAN="1"; shift 1 ;;
    --) shift; break; ;;
    *) echo "ERROR: Invalid command-line option: $1" >&2; exit 1; ;;
  esac
done

# Define log file
BUILD_LOG="$(pwd)/build.log"
debug "BUILD_LOG: $BUILD_LOG"
# Create empty file
: > "$BUILD_LOG"

# Set default values
KALI_ARCH=${KALI_ARCH:-$HOST_ARCH}
if [ "$KALI_ARCH" = "x64" ]; then
  KALI_ARCH="amd64"
elif [ "$KALI_ARCH" = "x86" ]; then
  KALI_ARCH="i386"
fi
debug "KALI_ARCH: $KALI_ARCH"

if [ -z "$KALI_VERSION" ]; then
  KALI_VERSION="$(default_version $KALI_DIST)"
fi
debug "KALI_VERSION: $KALI_VERSION"

# Check parameters
debug "HOST_ARCH: $HOST_ARCH"

CODENAME=$KALI_DIST # For simple-cdd/debian-cd
debug "CODENAME: $CODENAME"
debug "KALI_DIST: $KALI_DIST"

# Set sane PATH (cron seems to lack /sbin/ dirs)
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
debug "PATH: $PATH"

if grep -q -e "^ID=debian" -e "^ID_LIKE=debian" /usr/lib/os-release; then
  debug "OS: $( . /usr/lib/os-release && echo $NAME $VERSION )"
elif [ -e /etc/debian_version ]; then
  debug "OS: $( cat /etc/debian_version )"
else
  echo "ERROR: Non Debian-based OS" >&2
fi

if [ ! -d "$SCRIPT_DIR/kali-config/installer-$KALI_VARIANT" ]; then
  echo "ERROR: Unknown variant of Kali installer configuration: $KALI_VARIANT" >&2
  exit 1
fi
require_package debian-cd "3.2.1+kali1"
require_package simple-cdd "0.6.9"

# We need root rights at some point
if [ "$(whoami)" != "root" ]; then
  if ! which $SUDO >/dev/null; then
    echo "ERROR: $0 is not run as root and $SUDO is not available" >&2
    exit 1
  fi
else
  SUDO="" # We're already root
fi
debug "SUDO: $SUDO"

IMAGE_NAME="$(image_name $KALI_ARCH)"
debug "IMAGE_NAME: $IMAGE_NAME"

debug "ACTION: $ACTION"
if [ "$ACTION" = "get-image-path" ]; then
  echo $(target_image_name $KALI_ARCH)
  exit 0
fi

if [ "$ACTION" != "clean" ]; then
  require_jigdo_xorrisofs
fi

if [ "$NO_CLEAN" = "" ]; then
  clean
fi
if [ "$ACTION" = "clean" ]; then
  exit 0
fi

# Create image output location
mkdir -pv "$TARGET_DIR/$TARGET_SUBDIR"
[ $? -eq 0 ] || failure

# Don't quit on any errors now
set +e

# Override some debian-cd environment variables
export BASEDIR="$(pwd)/simple-cdd/debian-cd"
export ARCHES=$KALI_ARCH
export ARCH=$KALI_ARCH
export DEBVERSION=$KALI_VERSION
debug "BASEDIR: $BASEDIR"
debug "ARCHES: $ARCHES"
debug "ARCH: $ARCH"
debug "DEBVERSION: $DEBVERSION"

if [ "$KALI_VARIANT" = "netinst" ]; then
  export DISKTYPE="NETINST"
  export FORCE_CD_SIZE1="STICK1GB"
  profiles="kali"
  auto_profiles="kali"
elif [ "$KALI_VARIANT" = "purple" ]; then
  export DISKTYPE="BD"
  profiles="kali kali-purple offline"
  auto_profiles="kali kali-purple offline"
  export KERNEL_PARAMS="debian-installer/theme=Clearlooks-Purple"
else    # plain installer
  export DISKTYPE="BD"
  profiles="kali offline"
  auto_profiles="kali offline"
fi
debug "DISKTYPE: $DISKTYPE"
debug "profiles: $profiles"
debug "auto_profiles: $auto_profiles"
[ -v KERNEL_PARAMS ] && debug "KERNEL_PARAMS: $KERNEL_PARAMS"

if [ -e .mirror ]; then
  kali_mirror=$(cat .mirror)
else
  kali_mirror=http://kali.download/kali/
fi
if ! echo "$kali_mirror" | grep -q '/$'; then
  kali_mirror="$kali_mirror/"
fi
debug "kali_mirror: $kali_mirror"

debug "Stage 1/2 - File(s)"
# Setup custom debian-cd to make our changes
cp -aT /usr/share/debian-cd simple-cdd/debian-cd
[ $? -eq 0 ] || failure

# Use the same grub theme as in the live images
# Until debian-cd is smart enough: http://bugs.debian.org/1003927
cp -f kali-config/common/bootloaders/grub-pc/grub-theme.in simple-cdd/debian-cd/data/$CODENAME/grub-theme.in
[ $? -eq 0 ] || failure

# Keep 686-pae udebs as we changed the default from 686
# to 686-pae in the debian-installer images
sed -i -e '/686-pae/d' \
  simple-cdd/debian-cd/data/$CODENAME/exclude-udebs-i386
[ $? -eq 0 ] || failure

# Configure the kali profile with the packages we want
grep -v '^#' kali-config/installer-$KALI_VARIANT/packages \
  > simple-cdd/profiles/kali.downloads
[ $? -eq 0 ] || failure

# Tasksel is required in the mirror for debian-cd
echo tasksel >> simple-cdd/profiles/kali.downloads
[ $? -eq 0 ] || failure

# Grub is the only supported bootloader on arm64
# so ensure it's on the iso for arm64.
if [ "$KALI_ARCH" = "arm64" ]; then
  debug "arm64 GRUB"
  echo "grub-efi-arm64" >> simple-cdd/profiles/kali.downloads
  [ $? -eq 0 ] || failure
fi

# Run simple-cdd
debug "Stage 2/2 - Build"
cd simple-cdd/
run_and_log build-simple-cdd \
  --verbose \
  --debug \
  --force-root \
  --conf simple-cdd.conf \
  --dist $CODENAME \
  --debian-mirror $kali_mirror \
  --profiles "$profiles" \
  --auto-profiles "$auto_profiles"
res=$?
cd ../
if [ $res -ne 0 ] || [ ! -e $IMAGE_NAME ]; then
  failure
fi

# If a command fails, make the whole script exit
set -e

debug "Moving files"
run_and_log mv -f "$IMAGE_NAME" "$TARGET_DIR/$(target_image_name "$KALI_ARCH")"
run_and_log mv -f "$BUILD_LOG" "$TARGET_DIR/$(target_build_log "$KALI_ARCH")"

echo -e "\n***\nGENERATED KALI IMAGE: $(readlink -f "$TARGET_DIR/$(target_image_name "$KALI_ARCH")")\n***"
