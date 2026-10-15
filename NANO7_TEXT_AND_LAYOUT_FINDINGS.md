# Evidence from the original nano 7 resources

Source: the user pasted the full English text map and layout metadata from the
Mac report for Apple firmware 1.0.4 (`37A40005`). The English database SHA-256 is
`3f2437b85c855a0f5fd503ef4462afa0756a988b8c1b98d06974e0123179c9a0`.
The cloud has this text/metadata, not the full IPSW or all layout payloads.

## Verified

- 1,847 English strings retain their distinct resource IDs, even where text repeats.
- 84 VLyt records have unique IDs and hashes and total 20,904 bytes.
- They occupy a contiguous database tail from byte 49,344 to 70,248.
- Lengths range from 28 to 524 bytes. All 34 distinct sizes are four-byte aligned.
- Both 28-byte records are fully available in the byte previews and their hashes match.
- Those two records, plus the beginning of a 52-byte record, support the reference
  schema's numerical outer advancement of `size + 8`. They do not prove field meanings.
- No record ID or 32-bit word in these previews matches an English string ID.

One record contains an apparent inner-size value of three, leaving a byte under
an unaligned interpretation. Its missing tail bytes are necessary to distinguish
padding from a different structure. The next step therefore collects all complete
VLyt payloads as opaque bytes, without applying speculative coordinates or actions.

## Native N9 implementation implications

The text provides useful reference vocabulary for Music/library/queue, Podcasts,
Audiobooks, Photos/slideshow, Clock/alarm/timer and Voice Memos. Text is evidence
that a label exists, not proof of the underlying event handling or audio behavior.
Repeated strings and VoiceOver instructions must retain their IDs and roles.

Apple FM radio/antenna/Live Pause, Bluetooth pairing, fitness sensors, video/DRM,
Genius and playback-speed labels do not establish corresponding N9 hardware or
software support. N9 Web, News and cloud/network screens require their own design.

The FNK display defaults to 40 MHz SPI and RGB565. A full 240x320 frame is 153,600
bytes, requiring at least 30.72 ms of payload transfer; 30 full frames/second would
use 92.16% of the theoretical SPI bandwidth before overhead. Use native partial
redraws and cached app-specific RGB565/alpha assets. Frame-rate and battery targets
still require physical measurement. The complete 27,967,388-byte image database
also exceeds the board's 16 MiB flash: select and preconvert necessary assets.

Existing code evidence, relative to the N9 source root:

- `firmware/src/lcd.cpp`: 240x320 geometry and two 40-row (19,200-byte) DMA buffers.
- `firmware/src/board.h`: default 40 MHz SPI, optional faster setting.
- `ui/os/theme.h` and `ui/os/nav.cpp`: 20-pixel status and 32-pixel app navigation.
- `ui/lv_conf.h`: PNG/JPEG enabled, runtime TTF disabled.
- `ui/svc/artwork.cpp`: photo decoding/cache has substantial temporary memory use.

Keep the current home/dashboard and shared assets frozen. Use touch Home and
Settings volume. Existing Aunty Priscilla-approved Cree vocabulary remains the
language authority. No Apple resource words are automatically approved translations.

## Limits

The 84 VLyt resources are not 84 recovered screens. Coordinates, property IDs,
screen hierarchy, navigation and executable behavior are not established. The main
OS remains encrypted. No Apple binary has been executed or ported to the ESP32-S3.
