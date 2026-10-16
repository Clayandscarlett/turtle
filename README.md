# N9 firmware downloads

Current reliability build: **N9_Media_Reliability_R5.zip** (`1.1.9-media-reliability-r5`).

R5 fixes wrong-file selection from an open Track List after rescans, stale scrub gestures seeking a changed track, and null writes on Music thumbnail allocation failure. The dashboard, fonts and visual styles are preserved. It carries the R4 persistence fixes and existing R3 TLS code. Read RELIABILITY_R5.md for exact checks and limits, FLASHING_MAC_R5.md for all-Terminal installation, and PRODUCT_STANDARD.md for the ongoing target.

Each ZIP includes its complete prebuilt images, SHA-256 image manifest and automatic USB installer. Verify the adjacent `.zip.sha256` file before extraction. `source/` contains review/overlay files rather than a full project checkout.

No physical phone was attached to the cloud environment. Host tests/builds do not establish live HTTPS, physical audio, FPS, charging or three-hour battery life. Earlier ZIPs remain available for comparison and recovery.

## Terminal-only nano 7 research tools

`N9_Nano7_Terminal_Kit_R2.zip` contains Mac M1 Terminal instructions, a checked headless Ghidra launcher, firmware inventory/range-extraction helpers, evidence annotation, and bounded disassembly/reference/pseudocode exports. Verify its adjacent `.zip.sha256` before extraction, then read `terminal-kit/README.md` from Terminal.

The tools were exercised with real Ghidra 12.1.4 on original test fixtures in the cloud. This is a research kit, not a new phone firmware release or an Apple firmware port. It includes no Apple image or keys. The dashboard and R4 firmware remain unchanged.

For the observed macOS 14 Homebrew download/timeout failure, `install-ghidra-m1.sh` installs a private ARM64 JDK, verified Ghidra/Gradle releases, builds native components using existing Apple compiler tools, configures the R2 helpers, and tests headless decompilation. It bypasses Homebrew dependencies and does not flash the phone. Mac compilation/test run on the user’s Mac; cloud validation is documented in the kit.

`inspect-nano7-firmware.py` reads the checksum-confirmed original nano 7 1.0.4 (`37A40005`) IPSW, reports its MSE directory and actual IMG1 encryption flags, and optionally writes a new JSON report. It does not extract, decrypt, access a device, choose CPU/load addresses, or import into Ghidra. Parsing follows pinned wInd3x format references and was checked with 35 synthetic cases; the real Apple package is inspected on the user’s Mac.
