# Complete VLyt evidence, revision 2

The original nano 7 English database contains 84 VLyt records totaling 20,904
bytes. The previous JSON retained only the first 32 bytes of each record. Two
complete 28-byte records match their hashes and support the reference parser's
length arithmetic, but longer records and padding need actual complete bytes.

`inspect-nano7-silverdb-r2.py --layout-evidence` selects the exact British-English
database only and includes all VLyt payloads as opaque hexadecimal data. It does
not assign coordinates, font properties, navigation actions or screen names.

```sh
/opt/homebrew/bin/python3 inspect-nano7-silverdb-r2.py \
  "$HOME/nano7-research/originals/iPod_1.0.4_37A40005.ipsw" \
  --layout-evidence \
  --out "$HOME/nano7-research/notes/nano7-layouts-$(date +%Y%m%d-%H%M%S).json" \
  --copy-summary
```

The two original helpers must remain alongside it. Their checksums and the IPSW
size/MD5/SHA-256 are verified before inspection. The complete FAT volume is
validated, and the English database must match its known size and SHA-256.
Each copied payload is bounds checked and matched to its recorded hash. Raw
evidence is capped at 16 KiB per record and 256 KiB in total. The original image
database is not selected for parsing in this mode.

The only retained output is a new JSON report. Source files stay read-only,
temporary resource data is removed, and no individual asset files are written.
No device access, OS decryption or N9 firmware changes occur. `--copy-summary`
copies the evidence to the Mac clipboard for the user to paste into this chat.

Default inspection keeps R1 behavior. Revision 2 is a separate filename, so the
existing R1 helper remains available.

Validation: 49 checks passed (24 layout/default/summary, 22 legacy parser and
3 integration checks). These cover exact original default-report equality,
all 84 synthetic opaque records and aliases, byte-budget boundaries, tampered
evidence rejection, and English-only selection through a real FAT16 fixture.
Integration used a synthetic ZIP and substituted verifier; it does not establish
verification of the user's Apple IPSW. Actual Apple layout bytes are the next
evidence to obtain from the Mac. No Apple asset binaries are distributed.
