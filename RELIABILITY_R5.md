# N9 media reliability R5

Version: `1.1.9-media-reliability-r5`.

This update fixes three reproduced defects in the native N9 media apps. It uses
the existing N9 engine; the iPod resource research has not supplied executable
Apple firmware. The dashboard, fonts, artwork and approved Cree vocabulary are
unchanged.

## Changes

- **Track List identity:** a library rescan could reuse numeric IDs while an
  open Track List retained its old queue. A row labeled Track03 reproducibly
  selected Track02. The view now checks library/playback revisions, refreshes
  from the live queue, rejects stale taps, and jumps within that live queue.
  It also removes the view's duplicate full queue allocation. Removed and
  replaced queues, including an empty queue, refresh safely.
- **Scrubbing across track changes:** releasing an old held slider could seek
  the next track after EOF. Scrub gestures now belong to their starting playback
  generation. A track change, same-path restart or repeat-one restart cancels
  that gesture; normal scrubbing still seeks.
- **Low-memory placeholder:** Music wrote through null pointers if either its
  thumbnail descriptor or 3,872-byte pixel allocation failed. The descriptor is
  now static, and a failed pixel allocation returns the existing immutable
  artwork. A later bind retries safely. Normal thumbnail pixels are unchanged.

No new user-interface wording or image assets were introduced. The extra queue
empty state uses the existing translated `No Songs` text. Physical Home remains
unnecessary, and Settings volume remains available.

## Validation

| Check | Result |
|---|---|
| Actual LVGL media views: rescan, stale taps, removal, replacement and empty queue | 18/18 scenarios PASS under ASan/UBSan |
| Actual Now Playing: ordinary seek, auto-next, same-path restart and repeat-one during held scrub | 4/4 scenarios PASS under ASan/UBSan |
| Production Music placeholder: pixel allocation failure/retry, descriptor-failure tolerance and normal path | 3/3 modes PASS under ASan/UBSan; all 1,936 pixels checked |
| Actual player/session coordinator with fake HAL and fault-injected storage | 133 host / 138 ESP32-macro checks PASS |
| USB installer and manifest/port selection | 15/15 tests PASS |
| Frozen dashboard baseline | 12/12 source hashes unchanged |
| ESP32-S3 build and four-image manifest | Recorded in `VALIDATION_R5.json` |

Baseline failures were captured before the fixes: wrong-file playback, an old
scrub seeking the next track, and null writes for both thumbnail allocations.
The English test fixture now writes the supported `language=0` setting; the old
unused `lang=en` entry did not select English. Production language behavior was
not changed to satisfy test assertions.

## Limits

The UI tests use simulated audio and disposable card fixtures. They establish the
listed selection, lifecycle, seeking and allocation behavior. Leak checking is
disabled in UI/thumbnail scenarios; they are not a whole-device memory or leak
guarantee. The thumbnail fix addresses its specific allocation failures, not all
possible heap exhaustion.

This pass found no newly proven memo-saving defect in the current source, and
does not claim the original physical Saving freeze has been verified resolved.
Microphone audio, SD latency, speaker output and cross-core operation still need
the phone. The existing R3 TLS repair is included unchanged; live HTTPS/radio/Web
success on the user's network has not been established by this pass.

30 FPS, charging/battery reporting and three hours of screen-on use on the 800 mAh
cell remain hardware acceptance targets, not measured results. R4's documented
shared-worker/checkpoint durability limits and hardware feature boundaries also
remain. Read `RELIABILITY_R4.md` and `PRODUCT_STANDARD.md` for those details.

The ZIP contains complete flash images and the automatic USB installer.
`source/` contains the review files and tests carried from R4 plus these changes;
it is not a standalone full source checkout. No Apple asset binaries are included.
