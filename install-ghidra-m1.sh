#!/bin/bash
# Native Apple Silicon, Terminal-only Ghidra installation for the N9 research kit.
# Installs only below ~/nano7-research. Does not use or modify Homebrew formulae.
set -Eeuo pipefail

if [ "$(uname -s)" != Darwin ]; then
    printf 'This installer runs on your Mac, not the Linux cloud workspace.\n' >&2
    exit 1
fi
if [ "$(uname -m)" != arm64 ]; then
    exec /usr/bin/arch -arm64 /bin/bash "$0" "$@"
fi

n9_root=$HOME/nano7-research
n9_tools=$n9_root/tools
n9_cache=$n9_root/downloads
mkdir -p "$n9_tools" "$n9_cache" "$n9_root/logs" "$n9_root/tests"
n9_stamp=$(date +%Y%m%d_%H%M%S)
n9_log=$n9_root/logs/ghidra-direct-$n9_stamp.log
exec > >(tee -a "$n9_log") 2>&1
trap 'n9_status=$?; printf "\nINSTALLATION STOPPED (exit %s). Log: %s\nPaste the final error lines into the chat.\n" "$n9_status" "$n9_log"; exit "$n9_status"' ERR

n9_ghidra_name=ghidra_12.1.4_PUBLIC_20260921.zip
n9_ghidra_sha=ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db
n9_ghidra_url=https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/$n9_ghidra_name
n9_jdk_name=OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz
n9_jdk_sha=3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998
n9_jdk_url=https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/$n9_jdk_name
n9_gradle_name=gradle-9.7.1-bin.zip
n9_gradle_sha=acd53f1edaf02f1a8ff99879f8a34b302661a057d9b063ae9e35b552f804d20a
n9_gradle_url=https://github.com/gradle/gradle-distributions/releases/download/v9.7.1/$n9_gradle_name
n9_kit_name=N9_Nano7_Terminal_Kit_R2.zip
n9_kit_sha=5a67facc88481a06c21091f13ed84c18aeceb7cdd363e450d3eb2b28952b5894
n9_kit_url=https://raw.githubusercontent.com/Clayandscarlett/turtle/n9-firmware-download/$n9_kit_name

n9_digest() {
    /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

n9_download() {
    local n9_url=$1 n9_name=$2 n9_expected=$3
    local n9_target=$n9_cache/$n9_name
    if [ -f "$n9_target" ] && [ "$(n9_digest "$n9_target")" = "$n9_expected" ]; then
        printf 'Verified cached download: %s\n' "$n9_name"
        return
    fi
    if [ -e "$n9_target" ]; then
        mv "$n9_target" "$n9_target.unverified-$n9_stamp"
    fi
    printf '\nDownloading %s\n' "$n9_name"
    /usr/bin/curl --fail --location --show-error --progress-bar --http1.1 \
        --connect-timeout 15 --max-time 1800 --speed-limit 1 --speed-time 45 \
        --retry 2 --retry-delay 2 --retry-max-time 1800 --continue-at - \
        "$n9_url" --output "$n9_target.part"
    if [ "$(n9_digest "$n9_target.part")" != "$n9_expected" ]; then
        printf 'Checksum mismatch for %s. Nothing from this download was installed.\n' "$n9_name" >&2
        return 1
    fi
    mv "$n9_target.part" "$n9_target"
    printf 'SHA-256 verified: %s\n' "$n9_name"
}

n9_unpack_zip() {
    local n9_archive=$1 n9_directory=$2 n9_destination=$3
    local n9_stage
    if [ -d "$n9_destination" ]; then
        printf 'Using existing directory: %s\n' "$n9_destination"
        return
    fi
    n9_stage=$(mktemp -d "$n9_tools/.extract.XXXXXX")
    /usr/bin/ditto -x -k "$n9_archive" "$n9_stage"
    [ -d "$n9_stage/$n9_directory" ]
    mv "$n9_stage/$n9_directory" "$n9_destination"
    rmdir "$n9_stage"
}

printf '\n[1/6] Checking the Mac compiler\n'
/usr/bin/xcode-select -p
/usr/bin/xcrun --find clang
/usr/bin/xcrun --sdk macosx --show-sdk-path
printf '#include <vector>\nint main(){std::vector<int> v;return (int)v.size();}\n' |
    /usr/bin/xcrun clang++ -x c++ -std=c++11 -fsyntax-only -

printf '\n[2/6] Downloading verified Java, Ghidra, and Gradle releases\n'
n9_download "$n9_jdk_url" "$n9_jdk_name" "$n9_jdk_sha"
n9_download "$n9_ghidra_url" "$n9_ghidra_name" "$n9_ghidra_sha"
n9_download "$n9_gradle_url" "$n9_gradle_name" "$n9_gradle_sha"

printf '\n[3/6] Unpacking the private toolchain\n'
n9_jdk_bundle=$n9_tools/jdk-21
if [ ! -d "$n9_jdk_bundle" ]; then
    n9_stage=$(mktemp -d "$n9_tools/.jdk.XXXXXX")
    /usr/bin/tar -xzf "$n9_cache/$n9_jdk_name" -C "$n9_stage" --strip-components=1
    [ -x "$n9_stage/Contents/Home/bin/javac" ]
    mv "$n9_stage" "$n9_jdk_bundle"
fi
n9_java_home=$n9_jdk_bundle/Contents/Home
[ -x "$n9_java_home/bin/java" ]
[ -x "$n9_java_home/bin/javac" ]
export JAVA_HOME=$n9_java_home
export PATH="$JAVA_HOME/bin:$PATH"
n9_java_arch=$("$JAVA_HOME/bin/java" -XshowSettings:properties -version 2>&1 |
    /usr/bin/awk -F= '/^[[:space:]]*os\.arch[[:space:]]*=/ {gsub(/[[:space:]]/,"",$2);print $2;exit}')
case "$n9_java_arch" in
    aarch64|arm64) ;;
    *) printf 'Java is not ARM64: %s\n' "$n9_java_arch" >&2; exit 1 ;;
esac
"$JAVA_HOME/bin/java" -version
n9_ghidra=$n9_tools/ghidra_12.1.4_PUBLIC
n9_gradle=$n9_tools/gradle-9.7.1
n9_unpack_zip "$n9_cache/$n9_ghidra_name" ghidra_12.1.4_PUBLIC "$n9_ghidra"
n9_unpack_zip "$n9_cache/$n9_gradle_name" gradle-9.7.1 "$n9_gradle"
[ -r "$n9_ghidra/support/analyzeHeadless" ]
[ -x "$n9_gradle/bin/gradle" ]

printf '\n[4/6] Building Ghidra native Mac components\n'
printf 'This compiles the decompiler and companion tools. It may take several minutes.\n'
export GRADLE_USER_HOME=$n9_tools/gradle-cache
(
    cd "$n9_ghidra/support/gradle"
    "$n9_gradle/bin/gradle" --no-daemon --console=plain --max-workers=2 --info buildNatives
)
for n9_relative in \
    Ghidra/Features/Decompiler/build/os/mac_arm_64/decompile \
    Ghidra/Features/Decompiler/build/os/mac_arm_64/sleigh \
    GPL/DemanglerGnu/build/os/mac_arm_64/demangler_gnu_v2_41 \
    GPL/DemanglerGnu/build/os/mac_arm_64/demangler_gnu_v2_24 \
    Ghidra/Features/FileFormats/build/os/mac_arm_64/lzfse; do
    [ -x "$n9_ghidra/$n9_relative" ]
    /usr/bin/file "$n9_ghidra/$n9_relative"
done

printf '\n[5/6] Installing the Terminal research helpers\n'
n9_download "$n9_kit_url" "$n9_kit_name" "$n9_kit_sha"
/usr/bin/ditto -x -k "$n9_cache/$n9_kit_name" "$n9_root"
if [ -f "$n9_root/toolchain.env" ]; then
    cp -p "$n9_root/toolchain.env" "$n9_root/toolchain.env.backup-$n9_stamp"
fi
printf 'NANO_GHIDRA_ROOT=%s\nNANO_JAVA_HOME=%s\n' "$n9_ghidra" "$n9_java_home" > "$n9_root/toolchain.env.new"
mv "$n9_root/toolchain.env.new" "$n9_root/toolchain.env"
export NANO_TOOLCHAIN_CONFIG=$n9_root/toolchain.env
/bin/bash "$n9_root/terminal-kit/bin/ghidra-headless" --show-config
n9_python=''
for n9_candidate in /opt/homebrew/bin/python3 /usr/bin/python3; do
    if [ -x "$n9_candidate" ] && "$n9_candidate" -c 'import sys; assert sys.version_info >= (3,9)' >/dev/null 2>&1; then
        n9_python=$n9_candidate
        break
    fi
done
if [ -z "$n9_python" ]; then
    printf 'Python 3.9 or newer is needed for the helper test.\n' >&2
    exit 1
fi
"$n9_python" "$n9_root/terminal-kit/nano7.py" init

printf '\n[6/6] Running a real headless decompiler test\n'
n9_fixture=$n9_root/tests/terminal-fixture
/usr/bin/xcrun clang -g -O0 "$n9_root/terminal-kit/tests/fixture.c" -o "$n9_fixture"
n9_project=toolcheck_direct_$n9_stamp
"$n9_python" "$n9_root/terminal-kit/nano7.py" analyze "$n9_fixture" \
    --workspace "$n9_root" --project "$n9_project" --analysis-seconds 120 \
    --max-functions 200 --function-seconds 10 --export-seconds 120
"$n9_python" - "$n9_root/exports/$n9_project/result" <<'PY'
import csv
from pathlib import Path
import sys
root=Path(sys.argv[1])
with (root/'EXPORT_COMPLETE.tsv').open() as stream:
    status=dict(csv.reader(stream,delimiter='\t'))
if int(status.get('decompile_succeeded','0')) < 1:
    raise SystemExit('No function decompiled successfully. Inspect decompile_status.tsv.')
if not any('volume_clamp' in p.read_text() for p in (root/'decompiled').glob('*.c')):
    raise SystemExit('Expected fixture function missing from pseudocode. Inspect the test reports.')
print('VERIFIED: native headless decompilation produced the expected test function.')
PY

printf '\nREADY: Ghidra is configured for Terminal-only analysis.\n'
printf 'Workspace: %s\nReports: %s/exports/%s/result\nLog: %s\n' "$n9_root" "$n9_root" "$n9_project" "$n9_log"
printf 'This tested our original fixture; no Apple firmware has been analyzed.\n'
