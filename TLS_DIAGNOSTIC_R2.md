# N9 TLS diagnostic R2

This is a diagnostic firmware, not a verified Internet repair. It follows the
device log showing successful HTTP and two HTTPS attempts rejected by the
certificate-bundle verifier with mbedTLS error -12288.

The current public trust bundle is already dated 2026-09-25. Its 121 roots,
offsets, sorted names and public keys match the installed IDF bundle format.
No evidence justifies replacing its trust roots yet.

## Change

Each TLS client now installs a diagnostic callback around the existing SDK
verifier. It reports certificate depth, issuer, subject, incoming and remaining
verification flags, and the verifier's exact numeric result. Failed verification
also reports the UTC epoch. The original SDK verifier still makes every trust
decision, and its result and flags are returned unchanged.

The firmware identifies itself as `1.1.9-tls-diagnostic-r2`. Home typography,
artwork and controls are unchanged; the typography discussion remains a design
proposal. This build retains the application and battery policy of the previous
candidate and does not introduce a cloud relay.

## Validation and limits

`python3 tests/tls_trust_diagnostics_test.py` compiles the actual diagnostic code
with host stubs under address/undefined-behavior sanitizers. It checks eight
verification outcomes, unchanged verifier results/flags, secure client setup,
failed attachment, null configuration and once-only/failed initialization.
These tests do not verify a live ESP32 TLS handshake.

The ESP32-S3 firmware build passed: 100,076 bytes static RAM and 4,690,242
bytes application flash. All four packaged-image hashes passed, and esptool
recognized the application as an ESP32-S3 image. No physical board was attached
to this cloud environment. The phone still needs the on-device diagnosis.

The cloud network cannot capture the same server certificate chain as the
phone's home network. The outstanding diagnostic is the chain/issuer received
there. The user can first obtain it without flashing using Mac Terminal:

```sh
openssl s_client -connect example.com:443 -servername example.com -tls1_2 -showcerts </dev/null 2>&1 | sed -n '1,25p'
```

If on-device diagnostics are needed, close the serial monitor before flashing,
use the included checksum-verifying `tools/flash_prebuilt.py`, then reopen the
monitor at 115200 baud and run Test Internet. Capture `[tls-verify]` and `[net]`
lines. Do not describe this build as fixing HTTPS until the phone succeeds.
