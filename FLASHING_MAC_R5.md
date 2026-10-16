# N9 R5 installation from Mac Terminal

This is the native N9 firmware for Freenove FNK0104B N16R8. Connect that board
with a USB data cable. The installer verifies four images, selects one USB serial
device automatically, and writes firmware without an erase-all command. Existing
NVS/data sectors are retained. Close any serial monitor before flashing.

Python is already installed at `/opt/homebrew/bin/python3` from the research setup.
This script creates the flash environment if missing and installs the published
`esptool==5.1.0` (the unavailable pip version `5.1.2` is not used).

Paste the complete block into a new Terminal window:

```sh
bash <<'N9_R5'
set -euo pipefail
mkdir -p "$HOME/n9-install"
cd "$HOME/n9-install"
curl -fL --connect-timeout 15 --max-time 180 \
  https://raw.githubusercontent.com/Clayandscarlett/turtle/n9-firmware-download/N9_Media_Reliability_R5.zip \
  -o N9_Media_Reliability_R5.zip
curl -fL --connect-timeout 15 --max-time 60 \
  https://raw.githubusercontent.com/Clayandscarlett/turtle/n9-firmware-download/N9_Media_Reliability_R5.zip.sha256 \
  -o N9_Media_Reliability_R5.zip.sha256
shasum -a 256 -c N9_Media_Reliability_R5.zip.sha256
unzip -o N9_Media_Reliability_R5.zip -d r5
if [ ! -x .flash-env/bin/python ]; then
  /opt/homebrew/bin/python3 -m venv .flash-env
fi
.flash-env/bin/python -m pip install 'esptool==5.1.0'
.flash-env/bin/python r5/tools/flash_prebuilt.py
N9_R5
```

Expected final message: `Flashed 1.1.9-media-reliability-r5`.

To inspect the bundle without flashing:

```sh
"$HOME/n9-install/.flash-env/bin/python" \
  "$HOME/n9-install/r5/tools/flash_prebuilt.py" --verify-only
```

To view USB diagnostics afterward:

```sh
"$HOME/n9-install/.flash-env/bin/python" \
  "$HOME/n9-install/r5/tools/flash_prebuilt.py" --monitor
```

Hold Control and press `]` to leave the monitor. If more than one USB serial
device is connected, disconnect the others or pass `--port /dev/cu.YOUR_PHONE`.
The helper lists candidates and refuses to guess.

After installation, verify correct track selection after a rescan and scrubbing
across a track ending. Physical audio, Internet connections, memo saving,
frame rate and battery runtime still need testing on the actual phone. R5 does
not establish a complete Apple firmware port or new hardware features.
