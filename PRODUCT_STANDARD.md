# N9 product standard

The reference is the iPod nano seventh-generation touchscreen media experience,
with the reliability of a finished dedicated device and the interaction precision
the user associates with Apple. This is independent software for the Freenove
FNK0104B ESP32-S3, not Apple's original firmware.

## Fixed design constraint

The main dashboard is frozen, including its current fonts, positions, artwork,
colors, widgets, icons and controls. Earlier dashboard typography proposals are
superseded by the user's instruction to keep it as it is. Reliability work occurs
inside applications, playback, storage and system services. Existing approved Cree
words remain the translation authority; missing vocabulary is not invented.

## Required behavior

- A visible song or episode always selects that same file, even after a background
  rescan or a removed/replaced file. Recycled rows must not retain another file's
  artwork, label or action.
- A reboot preserves the exact local playlist, shuffled sequence, current item,
  repeat/shuffle settings and saved position. Boot remains paused, matching the
  existing behavior. Temporary alarm, video and memo playback must not overwrite
  the last local-library session.
- Saving either completes or preserves the previous recoverable data. Disk-full,
  write, flush, close and rename failures must not erase all bookmarks, ratings or
  listening history. Never delete the last valid copy before an unchecked commit.
- Position and time calculations remain valid when media duration changes or a
  stored bookmark is beyond the new end. No unsigned wrap to enormous times.
- Navigation and touch feedback continue while background work runs. Back,
  pause/resume, sleep/wake and cancellation have predictable outcomes. A failed
  Internet request must reach a terminal state rather than indefinite loading.
- A recording is reported as saved only after its container and file are finalized.
  Failure to capture, write or finalize must have an explicit outcome.

## Measurement targets

These are targets, not claims that the phone has passed them:

- Visible press feedback within 100 ms for at least 95% of measured presses.
- Active navigation aims for 30 FPS; inspect actual frame intervals on hardware,
  including while audio is playing and a network request fails.
- No resets, wrong-file playback or corrupted saved data during the defined media,
  SD-error, network-error, sleep/wake and repeated-navigation scenarios.
- Three hours of screen-on operation remains a battery acceptance target. The
  reported 800 mAh cell implies an ideal average of at most 267 mA; current and
  runtime must be measured on the actual board, at recorded brightness/workload.

Host sanitizer tests, simulated audio and a successful firmware build do not
establish physical speaker output, SD power-loss durability, network compatibility,
frame rate, charging status or battery life. Each release must identify which
scenarios passed and which still need the phone.

## Hardware boundaries

The present board has no configured FM tuner or motion sensor, and ESP32-S3 does
not supply Bluetooth Classic A2DP headphone audio. Internet radio, a timed fitness
session and the Bluetooth settings screen do not establish those missing hardware
functions. Adding them needs a hardware/bridge design and its driver implementation.

## Current reliability pass

1. Exact playback-session snapshots and safe restoration after rescan/reboot.
2. Transactional library/statistics saves with a recoverable previous copy.
3. Stable media-list identity and refreshed podcast counts after library changes.
4. Safe audiobook remaining-time calculations.

The existing R3 TLS transport repair remains included. Cloud-relay and broader
seventh-generation feature parity remain subsequent work, not completed features.
