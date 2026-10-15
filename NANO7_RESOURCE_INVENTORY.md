# Nano 7 resource inventory from Mac Terminal

This helper inventories the plaintext `rsrc` IMG1 body from the already downloaded
original nano 7 IPSW, version 1.0.4 build `37A40005`. It requires Python 3 and the
existing `inspect-nano7-firmware.py` in the same directory. There are no new Python
packages, Ghidra dependencies, mounts, device connections, or Homebrew installs.

The source archive is opened read-only and verified against its exact size,
MD5 and SHA-256. Only the bounded resource body is copied to a private temporary
file, which is automatically removed. The filesystem is classified by calculated
cluster count, not its text label. The helper supports FAT16 and stops on an
unsupported format, invalid bounds, differing FAT copies, bad cluster links,
cycles, cross-links, or exceeded resource limits.

The JSON inventory contains live file paths, short names, sizes, SHA-256 hashes,
bounded magic-byte previews, and conservative format candidates. File hashes
exclude cluster slack. Long names require valid VFAT order, checksum and UTF-16;
invalid long names fall back to the short name with a warning. No individual
resource files are extracted. A report is exclusively created; existing reports
are never overwritten.

From `~/nano7-research`, after downloading and verifying the adjacent helper:

```sh
/opt/homebrew/bin/python3 list-nano7-resources.py \
  "$HOME/nano7-research/originals/iPod_1.0.4_37A40005.ipsw" \
  --out "$HOME/nano7-research/notes/nano7-resources-$(date +%Y%m%d-%H%M%S).json"
```

The resource image being readable does not decrypt the main OS. Ghidra analysis
of the encrypted `osos` component remains blocked by encryption. No offline key
or decryption route has been verified in this project, and no physical nano is
available. Resource filenames and format candidates also do not establish the
OS's behavior or make its binaries executable on the Freenove ESP32-S3.

Validation uses an independent PyFatFS-generated FAT16 volume, real redistributable
Noto fonts, generated PNG/text fixtures, Unicode long filenames, nested directories,
an empty file and a deleted entry. Paths, sizes and hashes are compared with
PyFatFS's own inventory. Focused corruptions exercise rejection paths. The cloud
does not have the user's Apple image; actual Apple resource inventory must run
on the user's Mac. No Apple binaries, fonts, icons or keys are included here.

The final helper passed 11 of 11 fixture checks: exact valid inventory; FAT mirror
mismatch; directory and file cycles; short chains; cross-linked files; truncated
body; invalid sector size; two volume/body bounds checks; and safe short-name
fallback for a bad long-name checksum. Test harness retained in the cloud at
`/workspace/n9-delivery/resource-fixtures/check-inventory.py`.

The existing N9 firmware and dashboard are unchanged by this research helper.
