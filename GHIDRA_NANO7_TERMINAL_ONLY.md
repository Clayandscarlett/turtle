# nano 7 -> Freenove: Terminal-only research kit

All Mac setup, inventory, extraction, Ghidra analysis, annotation, exports,
searches, builds and flashing use Terminal. Nothing launches `ghidraRun`, Finder,
a browser, a GUI editor, or a Ghidra window. Scripts use Ghidra's real headless
analyzer and native decompiler.

This kit contains original research helpers, not Apple firmware, keys, a nano
emulator, or an automatic ARM-to-ESP32 converter. No readable nano 7 executable
has yet been supplied or analyzed. The existing N9 ZIP is Freenove software.

The product constraints remain: dashboard unchanged, no physical Home/volume
buttons required for normal operation, volume in Settings -> Sound, and existing
approved Cree wording as the translation authority.

## 1. Install the native Mac tools

Run in the Mac's ordinary Terminal shell, not a serial monitor. Exit an open
serial monitor with Control+] first. These commands target an M1/Apple Silicon
Mac. Password input for `sudo` is handled in Terminal.

```sh
/usr/bin/arch -arm64 /bin/bash <<'NANO_SETUP'
set -e
if [ ! -x /opt/homebrew/bin/brew ]; then
  sudo -v && NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install ghidra python ripgrep
NANO_SETUP
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Homebrew's **formula** handles Ghidra's JDK and native Mac components. The
official multi-platform Ghidra 12.1.4 ZIP includes Linux/Windows native binaries,
but its Mac native decompiler must be built separately. Using Homebrew avoids
that additional manual build. Do not substitute `brew install --cask ghidra`.

The launcher selects the installed formula's actual JDK, checks compatibility,
requires native ARM64 Java and the Mac ARM64 decompiler, closes standard input,
and forces Java headless mode. Missing prerequisites cause an explicit error.

## 2. Download and verify this kit from Terminal

```sh
mkdir -p "$HOME/nano7-research"
cd "$HOME/nano7-research"
curl -fL https://raw.githubusercontent.com/Clayandscarlett/turtle/n9-firmware-download/N9_Nano7_Terminal_Kit.zip -o N9_Nano7_Terminal_Kit.zip
curl -fL https://raw.githubusercontent.com/Clayandscarlett/turtle/n9-firmware-download/N9_Nano7_Terminal_Kit.zip.sha256 -o N9_Nano7_Terminal_Kit.zip.sha256
shasum -a 256 -c N9_Nano7_Terminal_Kit.zip.sha256
```

Proceed only when the checksum says `OK`:

```sh
unzip -o N9_Nano7_Terminal_Kit.zip
python3 terminal-kit/nano7.py init
bash terminal-kit/bin/ghidra-headless --show-config
```

The config check prints tool versions and paths, without opening a window.
The kit uses only Python's standard library; no pip packages are required.

Optional tool check before obtaining Apple firmware:

```sh
cc -g -O0 terminal-kit/tests/fixture.c -o tests/terminal-fixture
python3 terminal-kit/nano7.py analyze tests/terminal-fixture --project toolcheck_v1
cat exports/toolcheck_v1/result/EXPORT_COMPLETE.tsv
```

This builds and analyzes our small original test program. It does not analyze
the nano. Choose a fresh project name if repeating the tool check. The same C
fixture was validated as a Linux ELF in the cloud; Mac-native execution remains
to be checked on your Mac.

## 3. Identify the actual Apple input

List possible files already in Downloads, without opening Finder:

```sh
python3 - <<'PY'
from pathlib import Path
for p in sorted((Path.home() / 'Downloads').iterdir()):
    if p.is_file() and p.suffix.lower() in ('.ipsw', '.zip', '.bin', '.dfu', '.img'):
        print(f'{p.stat().st_size:>12}  {p}')
PY
```

Obtain the exact nano 7 update package from an authorized source and record its
model/build/source URL. No verified Apple download URL is invented in this kit.

The next assignment is a **template**: replace the filename with the real Apple
file. Do not use an N9 ZIP, a directory, or the quoted placeholder unchanged.

```sh
NANO_INPUT="$HOME/Downloads/REPLACE_WITH_REAL_APPLE_PACKAGE_FILENAME"
python3 terminal-kit/nano7.py inspect "$NANO_INPUT" --out notes/original-manifest.json
file "$NANO_INPUT"
xxd -l 128 "$NANO_INPUT"
strings -a "$NANO_INPUT" | head -80
```

`inspect` computes SHA-256, records size/header bytes, and lists ZIP contents
when applicable. It never extracts or executes an archive entry. It refuses to
overwrite an existing manifest; use a different output filename for another run.
Supply `--source-url`, `--model`, and `--build` when those values are known.

## 4. Establish executable extraction

Determine the container layout, component offsets/lengths, compression,
signatures, encryption, and load mapping. A ZIP listing or readable string alone
does not establish an executable. Signing and encryption are different issues.
High entropy does not distinguish compression from encryption.

After offset and length are supported by the format, bounded extraction is:

```sh
python3 terminal-kit/nano7.py carve "$NANO_INPUT" \
  --offset "${NANO_OFFSET:?Set the proven offset}" \
  --length "${NANO_LENGTH:?Set the proven length}" \
  --out extracted/main-component.bin \
  --evidence "${NANO_EXTRACTION_EVIDENCE:?Describe the format evidence}"
```

Decimal or `0x`-prefixed values are accepted. The helper validates the range,
refuses overwrites, and writes a source/output-hash manifest. It copies a proven
byte range; it does not decompress, decrypt, or identify code automatically.

If encryption prevents readable extraction, stop the binary-analysis track at
that point and continue behavior-based implementation. Older freemyipod crypto
tools are not an established nano 7 decryptor. Ghidra cannot analyze encrypted
payloads into meaningful source code.

## 5. List available processors and establish the map

```sh
python3 terminal-kit/nano7.py languages --processor ARM > notes/arm-languages.tsv
column -t -s $'\t' notes/arm-languages.tsv | less -S
```

These are available choices, not a recommendation that any listed profile is
correct for nano 7. Determine the exact processor/profile, endianness, ABI,
instruction state, entry points, and image base from the image and corroborating
hardware information. Do not assume ARMv7, Cortex-M, or base zero.

Preserve mapping evidence in `notes`. Memory permissions and separately loaded
modules matter; a flat raw import is not a complete reconstruction of the device.

## 6. Import and analyze entirely headlessly

For an extracted executable with a recognized, valid header, set `NANO_EXECUTABLE`
to its actual path, then use:

```sh
python3 terminal-kit/nano7.py analyze "${NANO_EXECUTABLE:?Set a verified executable path}" \
  --project nano7_header_v1
```

For a confirmed raw executable, first record verified entry/mode evidence in a
TSV file. Then use the explicit raw import below. Each required variable must
come from evidence, not a guessed example:

```sh
python3 terminal-kit/nano7.py analyze "${NANO_EXECUTABLE:?Set a verified executable path}" \
  --project nano7_raw_v1 --mode raw \
  --language "${NANO_LANGUAGE:?Set the confirmed Ghidra language ID}" \
  --compiler "${NANO_COMPILER:?Set the confirmed compiler/ABI ID}" \
  --base "${NANO_IMAGE_BASE:?Set the confirmed image base}" \
  --evidence notes/verified-seeds.tsv \
  --evidence-note "${NANO_MAPPING_EVIDENCE:?Describe the mapping evidence}"
```

The helper uses the real `support/analyzeHeadless`, `-import`, `-scriptPath`,
`-preScript`/`-postScript`, two analysis CPUs, and a 600-second auto-analysis
timeout. The decompiler separately defaults to at most 200 attempted functions,
10 seconds per function, and a 120-second overall export budget. Increase limits
deliberately when warranted, for example `--max-functions 2000 --export-seconds 600`.

All imports use a new project name and refuse existing projects; no automatic
`-overwrite`, project deletion, device flashing, or code execution occurs. Analysis
parses executable bytes; it does not boot them.

Each run records the command, input hash, analyst configuration, logs, and result
files in `exports/PROJECT_NAME`. A missing export marker is an error. A marker
with `partial` means the recorded analysis/export limits prevented completion.
Even a complete export does not prove the processor or image base is correct.

## 7. Search disassembly, pseudocode and references from Terminal

```sh
NANO_REPORT="$HOME/nano7-research/exports/nano7_header_v1/result"
cat "$NANO_REPORT/metadata.tsv"
cat "$NANO_REPORT/EXPORT_COMPLETE.tsv"
rg -ni 'music|playlist|shuffle|volume|touch|sleep|audio' "$NANO_REPORT/defined_strings.tsv"
column -t -s $'\t' "$NANO_REPORT/functions.tsv" | less -S
less -S "$NANO_REPORT/instructions.tsv"
less -S "$NANO_REPORT/references.tsv"
less -S "$NANO_REPORT/calls.tsv"
rg -n 'candidate_volume|volume|shuffle' "$NANO_REPORT/decompiled"
```

Use the actual project name if it differs. Search an interesting string's address
in `references.tsv`, then inspect the referring function and its pseudocode.
Cross-check interpretations with `instructions.tsv`. `memorymap.tsv` records
the imported ranges and access flags. Auto-discovered functions and strings are
not a complete inventory of all meaningful code/data. Computed call targets can
remain unresolved; they are reported rather than fabricated.

Decompilation outcomes, timeouts, skipped functions, and warnings are recorded in
`decompile_status.tsv`. Pseudocode is approximate, not Apple's original source.

## 8. Apply verified annotations using a TSV and rerun

`NanoApplyEvidence.java` accepts these literal tab-separated row formats:

```text
label<TAB>ADDRESS<TAB>candidate_name
function<TAB>EVEN_ARM_ENTRY_ADDRESS<TAB>candidate_function_name
tmode<TAB>START_ADDRESS<TAB>END_ADDRESS<TAB>0_OR_1
```

`<TAB>` describes a real tab; it is not literal file content. Comments begin with
`#`. Use `printf` to create the file without opening an editor. For example, once
the relevant ARM addresses/state are independently established:

```sh
printf 'tmode\t%s\t%s\t%s\nfunction\t%s\t%s\n' \
  "${NANO_MODE_START:?}" "${NANO_MODE_END:?}" "${NANO_TMODE:?}" \
  "${NANO_ENTRY:?}" 'candidate_entry' > notes/verified-seeds.tsv
```

Record why those values are justified in a separate evidence note. Apply TMode
only to supported ARM ranges; never set all firmware to Thumb because it looks
plausible. The script checks syntax, mapped ranges, names, and mode consistency;
those checks cannot establish the truth of analyst-supplied evidence.

Rerun the analyze command using a fresh project name and `--evidence` to apply
labels, execution-state ranges, and function seeds before automatic analysis.
This rebuilds from the original input; it does not mutate an older project.
For richer types, MMIO regions, overlays, or prototypes, extend a reviewed Java
pre-script through Ghidra's APIs and invoke it with `-preScript`. No GUI is needed.

## 9. Recover specifications, then implement for Freenove

For each subsystem, keep a plain-text/TSV notebook of reference behavior, build
hash/address, confidence, input/output, state transitions, and acceptance tests.
Recover navigation first, then local music/library/Now Playing, podcasts and
audiobooks, photos/video, settings/power, memos and clock.

Implement portable behavior in the existing N9 source. Apple peripheral drivers
and machine code cannot execute on the ESP32-S3's Xtensa CPU. Ghidra does not
generate a Freenove build system or replace its hardware layer.

Existing touch/volume destinations:

- Home: bottom-edge swipe in `ui/os/system.cpp`; preserve dashboard visuals.
- Back: `ui/os/nav.cpp`, swipe right or existing app Back control.
- Settings -> Sound: `ui/apps/settings.cpp`, using `os::set_volume`.
- Playback/storage: `ui/svc/player.cpp`, `playback_session.cpp`, `library.cpp`.
- Hardware audio: `firmware/src/hal_esp32.cpp`.
- Calls have a separate fixed gain in `firmware/src/voice.cpp`; integrate that
  explicitly if Settings must control every audio source.

Consolidate volume controls in Settings, keep separate output-route levels,
clamp limits, debounce saving, and physically verify mute and gain changes.
Do not change the dashboard or invent unapproved Cree translations.

## 10. Build, check, and flash from Terminal

Use the actual N9 source directory. The published firmware ZIP contains review
overlays, not a replacement full source checkout. Once the full source and its
documented dependencies are present, run the relevant checks for changed code:

```sh
python3 tests/playback_session_test.py
python3 tests/library_store_test.py
python3 -m platformio run -d firmware
```

Add behavior-derived tests for new navigation/volume/media logic. Generate patches
and inspect them with `git diff` or text diffs from Terminal; no GUI editor is
required. Check frozen-dashboard hashes before release.

After packaging a build with the existing image manifest and installer, verify
and flash from Terminal using its actual Python environment and package folder:

```sh
"$HOME/n9-install/.flash-env/bin/python" tools/flash_prebuilt.py --verify-only
"$HOME/n9-install/.flash-env/bin/python" tools/flash_prebuilt.py
"$HOME/n9-install/.flash-env/bin/python" tools/flash_prebuilt.py --monitor
```

These are later Freenove release commands, not nano 7 extraction commands. This
research kit does not flash hardware and is not a new N9 firmware release.

## 11. Qualify the physical device

Collect logs from Terminal for Home/Back cancellation, recording finalization,
SD errors, network timeouts, volume/output changes, restart restoration, frame
timing, audio underruns, and battery current/runtime. Exercise each exposed app.

At 40 MHz SPI, a full 240x320 RGB565 frame takes at least 30.72 ms to transmit,
before rendering overhead. Favor partial redraws and cached artwork. Target
p95 press feedback <=100 ms and measure active frame timing on the board.
Three hours on 800 mAh implies an ideal average <=267 mA before practical losses;
measure the real battery, brightness, and workload.

Bluetooth Classic/A2DP, an FM tuner, motion sensing, and nano-equivalent video
decoding are not supplied by Ghidra or the current board. Native offline media
is the primary path; optional companion transcoding is a separate project.
The nano 7's media firmware cannot repair N9 Wi-Fi/HTTPS services.

## Validation and scope

See `VALIDATION.md` for checks actually run. A headless fixture test validates the
helpers; it is not evidence of nano 7 extraction, Apple behavior, an ESP32 port,
Mac hardware execution, physical audio, 30 FPS, or three-hour battery life.

No Apple image, extracted Apple code, private key, or Ghidra/Java distribution is
included in this kit.
