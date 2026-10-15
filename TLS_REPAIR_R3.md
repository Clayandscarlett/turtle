# N9 TLS repair R3

Version: `1.1.9-tls-repair-r3`.

The phone reached HTTP successfully, but its certificate-bundle callback rejected
HTTPS with a generic X509 fatal error (-12288). The Mac received a valid chain
ending at SSL.com TLS ECC Root CA 2022. That root's exact name and public key were
already embedded in the phone's prior firmware; simply adding that root would
not address the fault.

## Implementation

R3 uses ordinary mbedTLS certificate-chain verification instead of the compressed
bundle's custom verification callback. Its 121 trusted CA names and public keys
are unchanged. The complete public certificates are pinned, provenance recorded,
and checked against the original bundle; no cloud-private or test CA is included.

The certificates are parsed once from 129,143 immutable DER bytes in flash. Their
parsed structures use the existing mbedTLS PSRAM allocator. Peer verification is
required. Logging reports the actual rejection flags without clearing them or
turning off authentication. Normalized issuer-name handling is delegated to the
standard verifier rather than a raw DER-name lookup.

The SDK clears the TLS attachment callback when a client closes. R3 restores it
for reconnects, which matters to the reusable radio client. It also restores the
closed socket descriptor to -1 after the SDK clears the context.

The SDK lacks mbedTLS threading support. Initial handshakes and STARTTLS therefore
share a recursive guard with a five-second wait limit. Application data transfers
retain their existing behavior. TLS renegotiation is disabled so certificate-key
caches cannot be accessed outside the initial-handshake guard.

The USB installer now selects only a single USB serial device, excludes Bluetooth
ports, and stops when selection is ambiguous. `--monitor` opens diagnostic output
without flashing or prompting for a port. Boot logs and the installer report R3.

Home artwork, fonts, placements, controls and application layout are unchanged.
The proposed home typography and cloud relay are not implemented by this repair.

## Validation

- Matching real mbedTLS 3.6.5 executes the production TLS code on the host. All
  121 roots parse with persistent zero-copy DER backing. Valid P-384/P-256,
  RSA/ECC and PrintableString/UTF8 issuer-name chains validate.
- Wrong hostname, untrusted root, corrupted signature, missing intermediate and
  malformed DER are rejected. Temporary test CAs are rejected by the actual
  production trust cache and never enter firmware.
- Lifecycle tests under ASan/UBSan cover verification flags, required peer
  authentication, initialization once, reconnect state, recursive dispatch,
  concurrent handshakes and failed parsing at each of the 121 root positions.
- Nine root-generator tests cover reproducibility and reject additions,
  omissions, duplicates, replacement keys, invalid signatures and malformed
  reference data. Fifteen installer tests cover selection, hashes and flashing
  arguments.

Reports include `tests/results/tls_real_verification.json` and `.txt`.
The ESP32-S3 build passed with 100,484 bytes static RAM and 4,695,362 bytes
application flash. All four flash-image checksums passed, esptool recognizes
the application image, and the exact 129,143 DER bytes and R3 version string
were found in the packaged firmware. These static sizes do not measure dynamic
heap or PSRAM peaks.
Host date-check tests are explicitly host-only: the target SDK's existing
disabled certificate-date configuration is unchanged. Host tests use real
crypto but do not measure ESP32 RAM peaks, audio quality, FPS or battery current.

## Device acceptance

No physical board is attached to the cloud environment. The original on-device
cause is not yet proven, and this build must be confirmed on the phone. After
flashing, run Test Internet, then load a newspaper and play radio. An HTTPS pass
on the phone is required before describing live Internet as repaired.

If a failure remains, open the included installer with `--monitor`, repeat the
test, and capture the `[tls-verify]` issuer/depth/flags. Standard verification
retains the specific reason instead of the previous generic callback error.

The firmware ZIP contains complete prebuilt images and its installer. Its
`source/` directory contains the repair files and tests for review, not the
entire original project.
