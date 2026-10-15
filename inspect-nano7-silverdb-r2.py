#!/usr/bin/env python3
"""Read-only Nano 7 resource inspection, with optional full VLyt evidence.

Uses the two existing, checksum-pinned Python helpers. Reads original 37A40005
IPSW only. No individual assets are written, no image pixels decoded, no device
access, and no OS decryption. SilverDB reference: spotlightishere/silverutil
3a34c6a7e42555df8ae69fc42d168b5e888ae80b, src/format.rs and bitmap/format.rs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import runpy
import struct
import subprocess
import sys
import tempfile
import zipfile

INSPECTOR_SHA = "9a807ef768bbf2c1e862042a9eed3a4d7009e6673bd81336a4c7dc1923372fef"
INVENTORY_SHA = "980aa847928a1245f527ba55af322de44450fb7af65f4b705e514c63d8befb7d"
SOURCE_COMMIT = "3a34c6a7e42555df8ae69fc42d168b5e888ae80b"
TARGETS = {
    "/Resources/UI/SilverDB.en_GB.LE.bin": {
        "bytes": 70248, "sha256": "3f2437b85c855a0f5fd503ef4462afa0756a988b8c1b98d06974e0123179c9a0"},
    "/Resources/UI/SilverImagesDB.LE.bin": {
        "bytes": 27967388, "sha256": "8407b6d09fd9a5a9d9f26405aafdd0fbf28d3ba74eae9613c476914fd5fc3085"},
}
MAX_DATABASE = 32 * 1024 * 1024
MAX_HEADER = 256 * 1024
MAX_SECTIONS = 128
MAX_RESOURCES = 16384
MAX_HASH_BYTES = 128 * 1024 * 1024
MAX_TEXT_BYTES = 256 * 1024
MAX_LAYOUT_RECORD = 16 * 1024
MAX_LAYOUT_TOTAL = 256 * 1024
TEXT_SECTIONS = {"Str ", "StrT", "ACST", "SCST"}
BITMAP_FORMATS = {2: "grayscale2", 4: "grayscale4", 8: "grayscale8",
                  0x565: "RGB565", 0x1444: "ARGB4444", 0x1888: "ARGB8888",
                  0x64: "indexed8", 0x65: "indexed16"}


class SilverError(ValueError):
    pass


def bounded(offset, size, limit, label):
    if offset < 0 or size < 0 or offset > limit or size > limit - offset:
        raise SilverError(label + " exceeds its containing data")


def bitmap_header(payload, resource_id):
    if not payload:
        return {"status": "empty"}
    if len(payload) < 32:
        return {"status": "unrecognized", "reason": "shorter than Nano bitmap header"}
    mode, external, row, depth, unknown1, unknown2, height, width, image_id, length = struct.unpack_from("<4H6I", payload)
    result = {"status": "header_checked", "format_code": mode,
              "format_name": BITMAP_FORMATS.get(mode, "unknown"),
              "raw_external": external, "raw_row_field": row, "raw_depth_field": depth,
              "raw_unknown_08": unknown1, "raw_unknown_0c": unknown2,
              "height": height, "width": width, "resource_id": image_id,
              "pixel_content_bytes": length, "pixels_decoded": False}
    if image_id != resource_id or length != len(payload) - 32:
        result.update(status="unrecognized", reason="ID or content-length mismatch")
    return result


def inspect_silverdb(data, include_layout_bytes=False):
    """Pure bounded parser. Keeps unknown records as hashes and short previews."""
    view = memoryview(data)
    if not 12 <= len(view) <= MAX_DATABASE:
        raise SilverError("Database size is unsupported")
    version, base, count = struct.unpack_from("<3I", view)
    if version != 3:
        raise SilverError("Unsupported SilverDB version")
    if not 1 <= count <= MAX_SECTIONS:
        raise SilverError("Section count exceeds inspection limit")
    section_end = 12 + 16 * count
    if not section_end <= base <= min(len(view), MAX_HEADER):
        raise SilverError("Invalid header length/data base")
    sections, intervals = [], []
    resource_total = hash_bytes = text_bytes = text_payload_bytes = layout_bytes = 0
    for index in range(count):
        raw, n, sequential, offset = struct.unpack_from("<4s3I", view, 12 + 16 * index)
        if any(byte < 32 or byte > 126 for byte in raw) or sequential not in (0, 1):
            raise SilverError("Invalid section FourCC or sequential flag")
        tag = raw[::-1].decode("ascii")
        resource_total += n
        if resource_total > MAX_RESOURCES:
            raise SilverError("Resource count exceeds inspection limit")
        if n:
            if offset < section_end:
                raise SilverError("Resource table overlaps section headers")
            bounded(offset, n * 12, base, "Resource metadata table")
        elif offset > base:
            raise SilverError("Empty-section offset exceeds header")
        entries, ids = [], set()
        duplicate_ids = 0
        for row in range(n):
            resource_id, relative, size = struct.unpack_from("<3I", view, offset + row * 12)
            absolute = base + relative
            bounded(absolute, size, len(view), "Resource payload")
            hash_bytes += size
            if hash_bytes > MAX_HASH_BYTES:
                raise SilverError("Payload hashing budget exceeded")
            payload = view[absolute:absolute + size]
            item = {"id": resource_id, "id_hex": "0x{:08x}".format(resource_id),
                    "bytes": size, "relative_data_offset": relative,
                    "absolute_data_offset": absolute,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "first_32_bytes_hex": bytes(payload[:32]).hex()}
            if resource_id in ids:
                duplicate_ids += 1
            ids.add(resource_id)
            if size:
                intervals.append((absolute, absolute + size))
            if tag in TEXT_SECTIONS:
                text_payload_bytes += size
                if text_payload_bytes > MAX_TEXT_BYTES:
                    raise SilverError("Text payload budget exceeded")
                item["text_status"] = "raw_preserved"
                if size and payload[-1] == 0:
                    raw_text = bytes(payload[:-1])
                    try:
                        decoded = raw_text.decode("utf-8", errors="strict")
                    except UnicodeError:
                        item["text_reason"] = "invalid UTF-8"
                    else:
                        if "\x00" in decoded:
                            item["text_reason"] = "embedded NUL"
                        else:
                            text_bytes += len(raw_text)
                            if text_bytes > MAX_TEXT_BYTES:
                                raise SilverError("Decoded text budget exceeded")
                            item.update(text_status="decoded_utf8_nul", text=decoded)
                else:
                    item["text_reason"] = "missing terminal NUL"
                if item["text_status"] == "raw_preserved":
                    item["raw_bytes_hex"] = bytes(payload).hex()
            if tag in ("BMap", "StBM"):
                item["image_header"] = bitmap_header(payload, resource_id)
            if include_layout_bytes and tag == "VLyt":
                layout_bytes += size
                if size > MAX_LAYOUT_RECORD or layout_bytes > MAX_LAYOUT_TOTAL:
                    raise SilverError("Raw layout evidence exceeds byte limit")
                item["raw_payload_hex"] = bytes(payload).hex()
            entries.append(item)
        sections.append({"fourcc": tag, "stored_fourcc": raw.decode("ascii"),
                         "resource_count": n, "raw_sequential_flag": sequential,
                         "metadata_offset": offset, "duplicate_id_count": duplicate_ids,
                         "resources": entries})
    # The format allows shared payload offsets; do not confuse them with FAT cross-links.
    overlap_records = 0
    furthest = 0
    for start, end in sorted(intervals):
        if start < furthest:
            overlap_records += 1
        furthest = max(furthest, end)
    return {"status": "complete", "version": version, "header_length": base,
            "section_count": count, "resource_count": resource_total,
            "payload_records_overlapping_previous_spans": overlap_records,
            "decoded_text_bytes": text_bytes, "sections": sections,
            "bytes": len(view), "sha256": hashlib.sha256(view).hexdigest()}


def read_owned_file(volume, start, size, path):
    """Read a file only after the independent FAT inventory validated ownership."""
    if not 0 <= size <= MAX_DATABASE:
        raise SilverError("Selected database exceeds size limit")
    result, seen = bytearray(), set()
    current = start
    while len(result) < size:
        if current in seen or volume.owners.get(current) != path:
            raise SilverError("Database cluster ownership does not match validated inventory")
        seen.add(current)
        block = volume.cluster(current)
        result.extend(block[:size - len(result)])
        if len(result) < size:
            current = struct.unpack_from("<H", volume.fat, current * 2)[0]
    return result


def load_helper(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SilverError("Helper checksum mismatch: " + str(path))
    return runpy.run_path(str(path))


def inspect_ipsw(path, helper_directory, layout_evidence=False):
    api = load_helper(helper_directory / "inspect-nano7-firmware.py", INSPECTOR_SHA)
    inventory = load_helper(helper_directory / "list-nano7-resources.py", INVENTORY_SHA)
    container_hashes = api["verify_container"](path)
    target_names = {"/Resources/UI/SilverDB.en_GB.LE.bin"} if layout_evidence else set(TARGETS)

    class SelectedFAT(inventory["FAT16"]):
        def __init__(self, stream, size):
            super().__init__(stream, size)
            self.selected = {}

        def file(self, start, size, name, short):
            super().file(start, size, name, short)
            if name in target_names:
                self.selected[name] = (start, size)

    results = []
    with zipfile.ZipFile(path, "r") as archive:
        report = api["inspect_zip"](archive)
        matches = [x for x in report["mse"]["components"] if x["name"] == "rsrc"]
        if len(matches) != 1:
            raise SilverError("Expected exactly one resource image")
        r = matches[0]
        image = r["image"]
        if image.get("magic") != "8740" or image.get("image_version") != "2.0" or image.get("format_byte") != 4 or image.get("encrypted") is not False:
            raise SilverError("Unsupported or encrypted resource image")
        size = image["body_length"]
        if not 512 <= size <= inventory["MAX_BODY"]:
            raise SilverError("Resource image exceeds size limit")
        api["bounded"](image["header_size"], size, r["length"], "resource body")
        with tempfile.TemporaryFile(prefix="nano7-silverdb-") as body:
            with archive.open("Firmware.MSE") as source:
                source.seek(r["data_offset"] + image["header_size"])
                remaining = size
                while remaining:
                    block = source.read(min(1024 * 1024, remaining))
                    if not block:
                        raise SilverError("Truncated resource image")
                    body.write(block)
                    remaining -= len(block)
            body.flush()
            volume = SelectedFAT(body, size)
            inv = volume.inventory()
            if set(volume.selected) != target_names:
                raise SilverError("Expected selected databases were not found")
            for name in TARGETS:
                if name not in target_names:
                    continue
                start, file_size = volume.selected[name]
                expected = TARGETS[name]
                if file_size != expected["bytes"]:
                    raise SilverError("Database file size differs from supplied Mac inventory")
                data = read_owned_file(volume, start, file_size, name)
                if hashlib.sha256(data).hexdigest() != expected["sha256"]:
                    raise SilverError("Database hash differs from supplied Mac inventory")
                parsed = inspect_silverdb(data, include_layout_bytes=layout_evidence)
                parsed["path"] = name
                results.append(parsed)
                del data
    return {"status": "complete", "input": str(path), "container": container_hashes,
            "reference_commit": SOURCE_COMMIT, "databases": results,
            "resource_file_count": len(inv["files"]), "filesystem": inv["filesystem"],
            "source_files_modified": False, "image_pixels_decoded": False,
            "main_os_decrypted_or_executed": False,
            "scope": "English text and image-header metadata only; behavior and layout execution are not recovered"}


def summarize(report):
    result = {key: report[key] for key in ("status", "main_os_decrypted_or_executed", "reference_commit")}
    result["databases"] = []
    keywords = re.compile(r"\b(play|pause|shuffle|repeat|music|video|volume|settings?|home|back|radio|record|podcasts?|album|artist|battery|brightness|bluetooth|playlist|alarm|clock|stopwatch|timer|memo|date|time)\b", re.I)
    for database in report["databases"]:
        entry = {key: database[key] for key in ("path", "bytes", "sha256", "resource_count")}
        entry["sections"] = []
        text_candidates, dimensions, formats, header_states = [], Counter(), Counter(), Counter()
        text_total = raw_text_total = 0
        for section in database["sections"]:
            entry["sections"].append({k: section[k] for k in ("fourcc", "resource_count", "raw_sequential_flag", "duplicate_id_count")})
            for record in section["resources"]:
                if "text_status" in record:
                    if record["text_status"] == "decoded_utf8_nul":
                        text_total += 1
                        if keywords.search(record["text"]):
                            text_candidates.append({"section": section["fourcc"], "id": record["id_hex"], "text": record["text"][:240]})
                    else:
                        raw_text_total += 1
                image = record.get("image_header")
                if image:
                    header_states[image["status"]] += 1
                    if image["status"] == "header_checked":
                        dimensions[(image["width"], image["height"])] += 1
                        formats[image["format_name"]] += 1
        entry.update(decoded_text_records=text_total, undecoded_text_records=raw_text_total,
                     selected_menu_text=text_candidates[:60], matched_menu_text_count=len(text_candidates),
                     bitmap_header_states=dict(header_states), bitmap_formats=dict(formats),
                     most_common_image_dimensions=[{"width": w, "height": h, "count": n} for (w, h), n in dimensions.most_common(24)])
        result["databases"].append(entry)
    return result


def layout_summary(report):
    """Export opaque layout evidence; assign no unverified field meanings."""
    result = {"status": report["status"], "main_os_decrypted_or_executed": False,
              "reference_commit": SOURCE_COMMIT, "databases": [],
              "raw_layout_records": [], "layout_semantics_decoded": False}
    total = 0
    for database in report["databases"]:
        result["databases"].append({
            "path": database["path"], "sha256": database["sha256"], "bytes": database["bytes"],
            "sections": [{key: section[key] for key in ("fourcc", "resource_count", "raw_sequential_flag", "duplicate_id_count")}
                         for section in database["sections"]],
            "decoded_text_records": sum(r.get("text_status") == "decoded_utf8_nul" for s in database["sections"] for r in s["resources"]),
            "undecoded_text_records": sum(r.get("text_status") == "raw_preserved" for s in database["sections"] for r in s["resources"]),
            "bitmap_header_states": {}})
        for section in database["sections"]:
            if section["fourcc"] != "VLyt":
                continue
            for record in section["resources"]:
                raw = bytes.fromhex(record["raw_payload_hex"])
                if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                    raise SilverError("Raw layout evidence hash or length mismatch")
                total += len(raw)
                result["raw_layout_records"].append(dict(record, database=database["path"]))
    result["raw_layout_record_count"] = len(result["raw_layout_records"])
    result["raw_layout_bytes"] = total
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipsw", type=Path)
    parser.add_argument("--helpers", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--out", type=Path, required=True, help="NEW full JSON report; existing files are never overwritten")
    parser.add_argument("--copy-summary", action="store_true", help="Copy a short JSON summary using macOS pbcopy")
    parser.add_argument("--layout-evidence", action="store_true", help="Inspect only British English and retain complete bounded VLyt payloads as opaque hex")
    args = parser.parse_args(argv)
    try:
        output = args.out.expanduser()
        if output.exists():
            raise SilverError("Report already exists; choose a new --out path")
        report = inspect_ipsw(args.ipsw.expanduser(), args.helpers.expanduser(), layout_evidence=args.layout_evidence)
        summary = layout_summary(report) if args.layout_evidence else summarize(report)
        serialized = json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
        with output.open("x", encoding="utf-8") as destination:
            destination.write(serialized)
        print("Complete: raw British-English layout evidence inspected." if args.layout_evidence else "Complete: British-English text and artwork metadata inspected.")
        for d in summary["databases"]:
            print(json.dumps(d["path"]) + ": " + ", ".join(s["fourcc"] + "=" + str(s["resource_count"]) for s in d["sections"]))
            if d["decoded_text_records"] or d["undecoded_text_records"]:
                print("  Decoded text: {}; retained as raw: {}".format(d["decoded_text_records"], d["undecoded_text_records"]))
            if d["bitmap_header_states"]:
                print("  Bitmap headers: " + json.dumps(d["bitmap_header_states"], sort_keys=True))
        if args.layout_evidence:
            print("Raw layout records: {}; total bytes: {}. Field meanings remain unverified.".format(
                summary["raw_layout_record_count"], summary["raw_layout_bytes"]))
        print("Full report: " + str(output))
        short_json = json.dumps(summary, indent=2, ensure_ascii=True) + "\n"
        if args.copy_summary:
            try:
                subprocess.run(["/usr/bin/pbcopy"], input=short_json, text=True, check=True)
            except (OSError, subprocess.CalledProcessError) as error:
                print("Clipboard copy failed; report was saved: " + str(error), file=sys.stderr)
                print(short_json, end="")
                return 1
            print("Summary copied. Paste into the chat with Command+V.")
        else:
            print(short_json, end="")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, EOFError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
