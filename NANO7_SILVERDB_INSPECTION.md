# Nano 7 English text and artwork metadata

`inspect-nano7-silverdb.py` reads the original nano 7 `37A40005` IPSW using the
existing, checksum-pinned `inspect-nano7-firmware.py` and `list-nano7-resources.py`.
All three helpers belong in `~/nano7-research`. Python's standard library is the
only dependency. No additional Homebrew packages, Ghidra runs or devices are needed.

The user's full resource inventory identified 34 language databases plus
`SilverImagesDB.LE.bin`. Its supplied 32-byte header declares one `BMap` section
with 1,533 entries. The British-English database has three sections. The new helper
validates and inspects these two exact files; their sizes and SHA-256 hashes are
pinned from the user-supplied inventory. Full record payloads are validated only
when this helper runs on the Mac; the cloud has the inventory metadata, not the
Apple IPSW.

```sh
/opt/homebrew/bin/python3 inspect-nano7-silverdb.py \
  "$HOME/nano7-research/originals/iPod_1.0.4_37A40005.ipsw" \
  --out "$HOME/nano7-research/notes/nano7-silverdb-$(date +%Y%m%d-%H%M%S).json" \
  --copy-summary
```

The source stays read-only. A temporary copy contains only the exact bounded
plaintext resource body and is automatically removed. Complete FAT validation
precedes selected file reads; cluster ownership, sizes and source hashes must
match. No individual fonts, icons, images, or binaries are extracted to files.
The only retained output is a new JSON report; existing reports are not overwritten.
`--copy-summary` copies a compact report to the Mac clipboard for the user to paste.

The JSON includes sections, resource IDs, sizes, hashes, bounded byte previews,
strict UTF-8/NUL text where valid, and image-header metadata. Failed text decoding
retains raw bytes within explicit budgets. Images are not decoded. Bitmap metadata
reports raw uncertain fields rather than assigning unsupported meanings.

The format follows `spotlightishere/silverutil` commit
`3a34c6a7e42555df8ae69fc42d168b5e888ae80b`, particularly `src/format.rs`,
`src/section_content.rs`, `src/section_types.rs` and `src/bitmap/format.rs`:

- Initial header: version, header length/data base, section count.
- Section records: stored FourCC, resource count, sequential flag, absolute metadata offset.
- Resource records: ID, payload offset relative to the data base, size.
- Nano bitmap header: height at `0x10`, width at `0x14`, ID at `0x18`, length at `0x1c`.

Payload aliases and duplicate IDs are reported, not rejected merely for existing.
The sequential flag does not force IDs to start at one. Table offsets and payload
offsets are honored instead of assuming tightly packed data.

The final helper passed 22 independent fixture checks: valid and gapped section
tables; Unicode and empty text; exact raw retention for bad UTF-8 and NUL cases;
bitmap and status-bar headers; unknown/empty records; malformed bounds/version
cases; payload aliases and duplicate IDs; and actual PyFatFS-generated FAT16
ownership reads, wrong-owner rejection and a 277-cluster reread with exact hashes.
The original IPSW was not substituted with a synthetic archive or declared
successfully analyzed in the cloud. The harness is retained at
`/workspace/n9-delivery/silverdb-fixtures/check-silverdb.py`.

This is resource research. The main `osos` remains encrypted, runtime behavior
and layout execution have not been recovered, and no Apple code can be claimed
ported from this result. The existing N9 firmware and dashboard are unchanged.
No Apple resource files or keys are distributed with the helper.
