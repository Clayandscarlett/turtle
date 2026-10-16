#!/usr/bin/env python3
"""Lossless structural decoder for the recovered Nano 7 VLyt records.

Input: an R2 full report or its copied summary. Does not read/modify firmware,
decode screens, or assign meanings to numeric property keys. Standard library.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys

MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 512
MAX_RECORD_BYTES = 16 * 1024
MAX_TOTAL_BYTES = 256 * 1024
MAX_OBJECTS = 256
MAX_PROPERTIES = 4096
DATABASE_SHA = "3f2437b85c855a0f5fd503ef4462afa0756a988b8c1b98d06974e0123179c9a0"


class LayoutError(ValueError):
    pass


def word(data, offset, limit):
    if offset < 0 or offset > limit - 4:
        raise LayoutError("Truncated layout word")
    return struct.unpack_from("<I", data, offset)[0]


def key_hex(value):
    return "0x{:08x}".format(value)


def parse_vlyt(data):
    if not 4 <= len(data) <= MAX_RECORD_BYTES:
        raise LayoutError("Layout record size exceeds limits")
    count = word(data, 0, len(data))
    if count > MAX_OBJECTS:
        raise LayoutError("Object count exceeds limit")
    objects, position, properties = [], 4, 0
    for _ in range(count):
        begin = position
        size = word(data, begin, len(data))
        end = begin + 8 + size
        if size < 4 or end > len(data):
            raise LayoutError("Object value length exceeds record")
        object_key = word(data, begin + 4, end)
        n = word(data, begin + 8, end)
        properties += n
        if properties > MAX_PROPERTIES:
            raise LayoutError("Property count exceeds limit")
        cursor = begin + 12
        values = []
        for _ in range(n):
            value_size = word(data, cursor, end)
            prop = word(data, cursor + 4, end)
            value_end = cursor + 8 + value_size
            aligned_end = (value_end + 3) & ~3
            if aligned_end > end:
                raise LayoutError("Property value or padding exceeds object")
            payload = bytes(data[cursor + 8:value_end])
            padding = bytes(data[value_end:aligned_end])
            item = {"offset": cursor, "key": prop, "key_hex": key_hex(prop),
                    "value_bytes": value_size, "value_hex": payload.hex(),
                    "padding_hex": padding.hex()}
            fourcc = prop.to_bytes(4, "big")
            if all(32 <= c <= 126 for c in fourcc):
                item["fourcc_candidate"] = fourcc.decode("ascii")
            if value_size and value_size % 4 == 0:
                item["unsigned_le_words"] = list(struct.unpack("<{}I".format(value_size // 4), payload))
                item["signed_le_words"] = list(struct.unpack("<{}i".format(value_size // 4), payload))
            values.append(item)
            cursor = aligned_end
        if cursor != end:
            raise LayoutError("Object count/length leaves unexplained bytes")
        objects.append({"offset": begin, "value_bytes": size,
                        "object_key": object_key, "object_key_hex": key_hex(object_key),
                        "properties": values})
        position = end
    if position != len(data):
        raise LayoutError("Record count/length leaves unexplained bytes")
    return {"bytes": len(data), "object_count": count, "objects": objects}


def encode_vlyt(record):
    """Rebuild bytes from the parsed fields, preserving order and padding."""
    objects = record["objects"]
    if len(objects) > MAX_OBJECTS:
        raise LayoutError("Object count exceeds limit")
    result = bytearray(struct.pack("<I", len(objects)))
    for obj in objects:
        props = obj["properties"]
        value = bytearray(struct.pack("<I", len(props)))
        for prop in props:
            payload = bytes.fromhex(prop["value_hex"])
            padding = bytes.fromhex(prop["padding_hex"])
            if len(payload) != prop["value_bytes"] or len(padding) != (-len(payload)) % 4:
                raise LayoutError("Parsed property length/padding is inconsistent")
            value.extend(struct.pack("<II", len(payload), prop["key"]))
            value.extend(payload)
            value.extend(padding)
        if len(value) != obj["value_bytes"]:
            raise LayoutError("Parsed object value length is inconsistent")
        result.extend(struct.pack("<II", len(value), obj["object_key"]))
        result.extend(value)
    if len(result) > MAX_RECORD_BYTES:
        raise LayoutError("Encoded record exceeds limit")
    return bytes(result)


def load_json(path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise LayoutError("JSON input exceeds 8 MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_records(report):
    if not isinstance(report, dict):
        raise LayoutError("Expected a JSON report object")
    if "raw_layout_records" in report:
        return report["raw_layout_records"]
    records = []
    for database in report.get("databases", []):
        if database.get("sha256") != DATABASE_SHA:
            continue
        for section in database.get("sections", []):
            if section.get("fourcc") == "VLyt":
                records.extend(section["resources"])
    if not records:
        raise LayoutError("No complete layout bytes found; use the R2 --layout-evidence report")
    return records


def extract_strings(report):
    if not isinstance(report, dict):
        raise LayoutError("Expected a JSON report object")
    if not isinstance(report.get("english_strings", {}), dict):
        raise LayoutError("Expected an English ID-to-text object")
    result = dict(report.get("english_strings", {}))
    for database in report.get("databases", []):
        if database.get("sha256") != DATABASE_SHA:
            continue
        for section in database.get("sections", []):
            if section.get("fourcc") == "Str ":
                for record in section.get("resources", []):
                    if record.get("text_status") == "decoded_utf8_nul":
                        result[record["id_hex"]] = record["text"]
    return {int(k, 16): v for k, v in result.items()}


def analyze(report, strings=None):
    source = extract_records(report)
    if not isinstance(source, list) or not 1 <= len(source) <= MAX_RECORDS:
        raise LayoutError("Layout record count exceeds limit")
    strings = extract_strings(report) if strings is None else strings
    records, total, ids = [], 0, set()
    for item in source:
        if not isinstance(item, dict):
            raise LayoutError("Expected a layout record object")
        raw_hex = item.get("raw_payload_hex")
        if not isinstance(raw_hex, str) or len(raw_hex) > MAX_RECORD_BYTES * 2:
            raise LayoutError("Missing or excessive complete raw layout bytes")
        raw = bytes.fromhex(raw_hex)
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise LayoutError("Aggregate layout evidence exceeds limit")
        identifier = item["id"]
        if not isinstance(identifier, int) or not 0 <= identifier <= 0xFFFFFFFF or identifier in ids:
            raise LayoutError("Invalid or duplicate layout ID")
        ids.add(identifier)
        if not isinstance(item["id_hex"], str) or item["id_hex"].lower() != key_hex(identifier):
            raise LayoutError("Layout ID representations disagree")
        if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise LayoutError("Layout evidence hash or length mismatch")
        preview = item.get("first_32_bytes_hex")
        if preview is not None and bytes.fromhex(preview) != raw[:32]:
            raise LayoutError("Layout preview disagrees with complete payload")
        parsed = parse_vlyt(raw)
        if encode_vlyt(parsed) != raw:
            raise LayoutError("Lossless roundtrip failed")
        parsed.update(id=identifier, id_hex=key_hex(identifier), sha256=item["sha256"])
        records.append(parsed)
    objects = {obj["object_key"] for record in records for obj in record["objects"]}
    frequencies, widths, families = Counter(), Counter(), defaultdict(list)
    references, padding_bytes, nonzero_padding = [], 0, 0
    for record in records:
        families[tuple(sorted(obj["object_key"] for obj in record["objects"]))].append(record["id_hex"])
        for obj in record["objects"]:
            for prop in obj["properties"]:
                frequencies[prop["key_hex"]] += 1
                widths[prop["value_bytes"]] += 1
                pad = bytes.fromhex(prop["padding_hex"])
                padding_bytes += len(pad)
                nonzero_padding += any(pad)
                for index, value in enumerate(prop.get("unsigned_le_words", [])):
                    if value >> 16 != 0x0DAD:
                        continue
                    ref = {"record": record["id_hex"], "object": obj["object_key_hex"],
                           "property": prop["key_hex"], "word_index": index,
                           "target": key_hex(value), "meaning": "numeric equality only"}
                    if value in strings:
                        ref.update(category="english_string", text=strings[value])
                    elif value in objects:
                        ref["category"] = "object_key_in_supplied_records"
                    else:
                        ref["category"] = "unresolved_resource_like_word"
                    references.append(ref)
    stats = {"layout_records": len(records), "raw_bytes": total,
             "object_entries": sum(r["object_count"] for r in records), "distinct_object_keys": len(objects),
             "property_values": sum(frequencies.values()), "distinct_property_keys": len(frequencies),
             "property_key_counts": dict(sorted(frequencies.items())),
             "value_size_counts": dict(sorted(widths.items())), "padding_bytes": padding_bytes,
             "nonzero_padding_regions": nonzero_padding, "object_key_set_families": len(families),
             "candidate_reference_occurrences": len(references),
             "exact_text_reference_occurrences": sum(x["category"] == "english_string" for x in references)}
    return {"status": "complete", "structure_verified": True, "semantic_properties_verified": False,
            "main_os_decrypted_or_executed": False, "statistics": stats, "records": records,
            "candidate_references": references,
            "variant_families": [{"object_keys": [key_hex(x) for x in keys], "records": values}
                                 for keys, values in families.items()],
            "limits": "Structure and numeric references only; no recovered screen transitions, coordinates, font mapping or executable behavior"}


def markdown(result):
    s = result["statistics"]
    lines = ["# Nano 7 layout structure analysis", "", "All supplied record hashes match, and every decoded record rebuilds byte for byte.", "",
             "| Verified item | Count |", "|---|---:|"]
    for label, key in (("Records", "layout_records"), ("Raw bytes", "raw_bytes"),
                       ("Object entries", "object_entries"), ("Distinct object keys", "distinct_object_keys"),
                       ("Property values", "property_values"), ("Property keys", "distinct_property_keys"),
                       ("Padding bytes", "padding_bytes"), ("Object-key-set families", "object_key_set_families")):
        lines.append("| {} | {} |".format(label, s[key]))
    lines.extend(["", "The record is a count followed by object entries. Each object starts with a value length and an opaque object key; its value contains a property count and properties. Each property is a byte length, opaque key, value bytes, and padding to four-byte alignment.", "", "## Exact English-ID matches", ""])
    matches = [r for r in result["candidate_references"] if r["category"] == "english_string"]
    if matches:
        for ref in matches:
            lines.append("- `{record}` / `{object}` / `{property}` matches `{target}`: {text}".format(**dict(ref, text=json.dumps(ref["text"], ensure_ascii=True))))
    else:
        lines.append("No English map was supplied or no exact matches were found.")
    lines.extend(["", "## Limits", "", "Matching a number to a text ID does not establish a property's role or a complete screen. Numeric property meanings, coordinates, font/color bindings, navigation and executable behavior remain unverified. The main OS remains encrypted.", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--strings", type=Path, help="Optional earlier English-map export")
    parser.add_argument("--out", type=Path, required=True, help="NEW decoded JSON report")
    parser.add_argument("--markdown", type=Path, help="Optional NEW Markdown findings report")
    args = parser.parse_args(argv)
    try:
        outputs = [p.expanduser() for p in (args.out, args.markdown) if p is not None]
        if any(p.exists() for p in outputs) or len({p.resolve() for p in outputs}) != len(outputs):
            raise LayoutError("Output exists or output paths overlap; choose new paths")
        source = args.report.expanduser()
        supplied = load_json(source)
        strings = extract_strings(load_json(args.strings.expanduser())) if args.strings else None
        result = analyze(supplied, strings)
        result["input_json_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        serialized = json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
        note = markdown(result)
        with outputs[0].open("x", encoding="utf-8") as output:
            output.write(serialized)
        if args.markdown:
            with outputs[1].open("x", encoding="utf-8") as output:
                output.write(note)
        print(json.dumps(result["statistics"], indent=2))
        print("Decoded JSON: " + str(outputs[0]))
        if args.markdown:
            print("Findings: " + str(outputs[1]))
        print("All records roundtrip exactly. Numeric property meanings remain unverified.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
