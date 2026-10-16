# Nano 7 layout structure analysis

All supplied record hashes match, and every decoded record rebuilds byte for byte.

| Verified item | Count |
|---|---:|
| Records | 84 |
| Raw bytes | 20904 |
| Object entries | 388 |
| Distinct object keys | 126 |
| Property values | 948 |
| Property keys | 14 |
| Padding bytes | 38 |
| Object-key-set families | 32 |

The record is a count followed by object entries. Each object starts with a value length and an opaque object key; its value contains a property count and properties. Each property is a byte length, opaque key, value bytes, and padding to four-byte alignment.

The object value length includes its property-count word and encoded properties,
and excludes the preceding length and object-key words. Each property length is
the value-byte count; padding follows those bytes. Of 64 tested size/alignment
models, only this length convention with four-byte alignment consumes every
record exactly. The 38 padding bytes are all zero in the supplied evidence.

The independently checked decoder passes 24 focused cases and command-line
checks. All 84 real records match an independent parse, match the earlier
metadata, and rebuild byte for byte. Complete and compact report inputs agree;
malformed bounds, counts, identities, hashes and previews fail; output files
cannot be overwritten. Nonzero padding is preserved rather than silently erased.

## Exact English-ID matches

- `0x0dad145e` / `0x0dad1d5d` / `0x000004cc` matches `0x0dad0a55`: "double-tap to mark item for deletion"
- `0x0dad145f` / `0x0dad1d5d` / `0x000004cc` matches `0x0dad0a56`: "double-tap to cancel item deletion"
- `0x0dad1460` / `0x0dad1d5d` / `0x000004cc` matches `0x0dad0a55`: "double-tap to mark item for deletion"
- `0x0dad1461` / `0x0dad1d5d` / `0x000004cc` matches `0x0dad0a56`: "double-tap to cancel item deletion"
- `0x0dad152e` / `0x0dad1eea` / `0x000003fd` matches `0x0dad0a32`: "Cancel"
- `0x0dad152e` / `0x0dad1eeb` / `0x000003fd` matches `0x0dad0a33`: "OK"

## Limits

Matching a number to a text ID does not establish a property's role or a complete screen. Numeric property meanings, coordinates, font/color bindings, navigation and executable behavior remain unverified. The main OS remains encrypted.

There are 354 resource-like numeric references to 51 targets. Six occurrences
match the four English strings listed above; no value points to another supplied
VLyt record ID, so this is not an established screen-transition graph. Records
form 32 families with matching object-key sets, but order and operation lists can
vary within a family. No family has been assigned a screen or state name.

This research does not change the N9 firmware or dashboard. Rebuilding N9 apps
must preserve the existing dashboard, touch Home, Settings volume and approved
Cree vocabulary. The target display is 240x320; the original 240x432 artwork needs
app-specific adaptation. Partial native redraws and selected preconverted assets
are required for a sensible performance budget; physical frame rate, battery
duration and media reliability still require tests on the actual N9.
