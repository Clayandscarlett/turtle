# N9 media reliability R4

Version: `1.1.9-media-reliability-r4`.

This release implements the first reliability pass toward the user's seventh-
generation nano media experience and finished-device quality standard. It does
not claim complete iPod feature parity or Apple firmware compatibility.

## What changed

- Local playback sessions retain the actual playlist, original and shuffled
  orders, duplicate occurrence, current item, position, repeat and shuffle state.
  Boot remains paused. A/B snapshot files and a checksummed KV commit keep queue
  and position identities consistent. Missing files are remapped safely, and old
  last-track preferences can migrate.
- Large new session buffers use scoped PSRAM allocators on ESP32. A conservative
  memory preflight preserves the existing committed session if budget is low.
  This does not alter the global allocator policy.
- Library/stat saves check write, error, flush, sync, close and commit results.
  The previous complete file is retained as a backup rather than removed before
  an unchecked rename. Loaders recover complete backups and ignore orphan temp
  files. Existing on-card formats remain readable.
- Music, podcast and audiobook views re-query their context after rescans.
  Revision guards prevent old labels from selecting a reused numeric track ID.
  Page timers skip hidden pages, and podcast badges refresh on return.
- Audiobook remaining time is clamped when a bookmark exceeds a changed duration.
  Bookmark arithmetic also avoids unsigned wrap.

The dashboard is unchanged: all 12 recorded dashboard/theme/asset/font source
hashes match the pre-pass baseline. The R3 standard certificate-chain verifier,
reconnect repair and automatic USB installer remain included.

## Checks completed

| Check | Result |
|---|---|
| Actual playback/coordinator with fake HAL and real fault-injected file I/O | 133 host assertions PASS, ASan/UBSan |
| ESP32-macro/no-exceptions allocator configuration with heap-caps shim | 138 assertions PASS, ASan/UBSan |
| Actual library store/load failure and recovery paths | 36 cases PASS, ASan/UBSan |
| Actual LVGL media views, rescans, stale clicks, recycled rows and return navigation | 14 scenarios PASS under ASan/UBSan |
| Full simulator process restart, persisted two-song playlist, paused restore and next/play controls | save + restore phases PASS |
| Actual audiobook view with 120-second bookmark on a 10-second file | displays `0:00 remaining`; screenshot inspected |
| Dashboard baseline | 12/12 files unchanged |
| ESP32-S3 build | PASS; 100,628 static RAM bytes, 4,725,286 application flash bytes |
| Four prebuilt images | SHA-256 verification PASS; application recognized by esptool |

UI scenario runners disable leak checking. These runs establish the listed
behavior and sanitizer checks, not a general leak-free or exhaustive-app claim.
The R3 real-mbedTLS checks are previous evidence for unchanged TLS code, not a
new live-network test in this pass.

## Remaining limits

New queue snapshots use the shared background worker. A blocking network job can
delay their durability; shutdown does not drain it. Until a snapshot commits,
reboot restores the previous committed session. Position checkpoints retain the
existing 15-second interval plus explicit control events. This is consistent
recovery, not a promise to retain every last second after sudden power loss.

Sessions are bounded to 2,048 entries and 256 KiB encoded data. That is not peak
RAM usage: in-flight/pending snapshots, metadata and validation buffers need more.
Scoped PSRAM placement and preflight reduce internal-RAM pressure, but a concurrent
out-of-memory race is not guaranteed recoverable when exceptions are disabled.

Retained backups address the tested write/commit/interruption states. Physical
SD power cuts and arbitrary corruption that still forms valid legacy rows are
not covered by those tests. Whole-device memory peaks, SD latency, actual audio,
HTTPS on the user's network, 30 FPS, charging and three-hour battery life still
require the phone. Missing FM, motion-sensing and Bluetooth Classic audio hardware
is not added by this release. Approved Cree vocabulary coverage is unchanged.

Read PRODUCT_STANDARD.md for the ongoing quality target. The ZIP contains complete
prebuilt images and the installer; `source/` contains review files and tests to
apply to the complete original project, not a standalone full project checkout.
