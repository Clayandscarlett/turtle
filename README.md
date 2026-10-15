# N9 firmware downloads

Current reliability build: **N9_Media_Reliability_R4.zip** (`1.1.9-media-reliability-r4`).

R4 preserves the main dashboard and repairs committed playback-session restoration, recoverable library/stat saves, stale media rows after rescans and audiobook remaining-time bounds. It includes R3 TLS and reconnect changes. Read RELIABILITY_R4.md for exact tests and remaining limits, and PRODUCT_STANDARD.md for the ongoing product target.

Each ZIP includes its complete prebuilt images, SHA-256 image manifest and automatic USB installer. Verify the adjacent `.zip.sha256` file before extraction. `source/` contains review/overlay files rather than a full project checkout.

No physical phone was attached to the cloud environment. Host tests/builds do not establish live HTTPS, physical audio, FPS, charging or three-hour battery life. Earlier ZIPs remain available for comparison and recovery.

## Terminal-only nano 7 research tools

`N9_Nano7_Terminal_Kit_R2.zip` contains Mac M1 Terminal instructions, a checked headless Ghidra launcher, firmware inventory/range-extraction helpers, evidence annotation, and bounded disassembly/reference/pseudocode exports. Verify its adjacent `.zip.sha256` before extraction, then read `terminal-kit/README.md` from Terminal.

The tools were exercised with real Ghidra 12.1.4 on original test fixtures in the cloud. This is a research kit, not a new phone firmware release or an Apple firmware port. It includes no Apple image or keys. The dashboard and R4 firmware remain unchanged.

For the observed macOS 14 Homebrew download/timeout failure, `install-ghidra-m1.sh` installs a private ARM64 JDK, verified Ghidra/Gradle releases, builds native components using existing Apple compiler tools, configures the R2 helpers, and tests headless decompilation. It bypasses Homebrew dependencies and does not flash the phone. Mac compilation/test run on the user’s Mac; cloud validation is documented in the kit.
