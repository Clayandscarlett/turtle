# Lossless Nano 7 layout decoder

`analyze-nano7-layouts.py` reads the saved R2 layout-evidence report or its copied
summary. It never rereads the IPSW, contacts a device, or changes source files.
It uses Python's standard library only.

The supplied original nano 7 dataset contains 84 VLyt resources, 20,904 bytes,
388 object entries and 948 property values. The numeric structure is decoded;
property meanings and runtime behavior remain unverified. See the adjacent
`NANO7_LAYOUT_STRUCTURE_REPORT.md` for aggregate findings and exact text matches.

Download and verify from Terminal:

```sh
cd "$HOME/nano7-research"
curl -fL https://raw.githubusercontent.com/Clayandscarlett/turtle/n9-firmware-download/analyze-nano7-layouts.py -o analyze-nano7-layouts.py
printf '%s\n' '359d2a71b09e7fe561727028bcf0d30720e0899e76ff7fff2248f120fa65b8b7  analyze-nano7-layouts.py' | shasum -a 256 -c -
```

Run against the newest completed R2 report (already saved on the Mac):

```sh
n9_layout_json="$(/opt/homebrew/bin/python3 -c 'from pathlib import Path; print(max((Path.home()/"nano7-research/notes").glob("nano7-layouts-*.json"), key=lambda p:p.stat().st_mtime))')"
n9_layout_stamp="$(date +%Y%m%d-%H%M%S)"
/opt/homebrew/bin/python3 analyze-nano7-layouts.py "$n9_layout_json" \
  --out "$HOME/nano7-research/notes/nano7-decoded-$n9_layout_stamp.json" \
  --markdown "$HOME/nano7-research/notes/nano7-decoded-$n9_layout_stamp.md"
cat "$HOME/nano7-research/notes/nano7-decoded-$n9_layout_stamp.md"
```

The full R2 report supplies English strings automatically. For a copied summary
without English text, `--strings PATH` can read the earlier English-map JSON.

The decoder checks per-record sizes, SHA-256 hashes, IDs, byte previews, all
count/length boundaries, and aggregate limits. It preserves ordering, opaque
property values, and alignment padding. Every record must rebuild byte for byte
from the decoded representation. Outputs use exclusive creation, so existing
files cannot be overwritten.

The output contains the complete parsed tree, numeric references and variant
families. A matching text ID is an exact numeric match, not a recovered event
handler. No numeric property is renamed to a guessed coordinate, color or font.

Validation: 24 focused checks plus CLI checks passed. All 84 user-supplied real
records match the independent parser; roundtrips, all 354 reference locations,
six text matches and 32 families agree. Malformed lengths/counts/identities/
hashes/previews are rejected; complete and compact inputs agree; nonzero padding
is preserved; CLI outputs and overwrite refusal were checked with unchanged
source hashes. The private source corpus and complete decoded payloads remain
in the workspace and are not bundled in this public tool.

The original main OS remains encrypted. This decoder does not recover executable
logic or constitute an Apple firmware port. The N9 dashboard and firmware are
unchanged by this analysis.
