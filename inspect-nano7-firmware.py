#!/usr/bin/env python3
"""Read-only inspection of Apple's iPod nano 7G 1.0.4 (37A40005) IPSW.

Format reference: freemyipod/wInd3x commit
7c7c4d83c8b923f29e7559585b2cdbbf4e028045, pkg/mse/mse.go,
pkg/image/image.go and pkg/exploit/decrypt/decrypt.go.
No payload extraction, decryption, device communication or Ghidra import.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import sys
import zipfile

SOURCE_COMMIT = "7c7c4d83c8b923f29e7559585b2cdbbf4e028045"
EXPECTED_SIZE = 117989754
EXPECTED_MD5 = "ceb2bc62eab6e1c5066ac3917a35284d"
EXPECTED_SHA256 = "cf26fb17fa37b685b9ac1d8faa7aab3705e1fe04ff6f63758611f0dce87413cf"
DIRECTORY_START = 0x5000
DIRECTORY_END = DIRECTORY_START + 16 * 40
MAX_MANIFEST = 1024 * 1024
MAX_MSE = 512 * 1024 * 1024
IMAGE_KINDS = {b"8702": ("Nano 3G", 0x800, b"1.0"),
               b"8720": ("Nano 4G", 0x600, b"2.0"),
               b"8730": ("Nano 5G", 0x600, b"2.0"),
               b"8723": ("Nano 6G", 0x400, b"2.0"),
               b"8740": ("Nano 7G / Mid-2015", 0x400, b"2.0")}
IMAGE_FORMATS = {1: "header declares signed, encrypted",
                 2: "header declares signed, unencrypted; code format unconfirmed",
                 3: "header declares X509 signed, encrypted",
                 4: "header declares X509 signed, unencrypted; code format unconfirmed"}


class InspectionError(ValueError):
    pass


def bounded(offset, length, total, label):
    if offset < 0 or length < 0 or offset > total or length > total - offset:
        raise InspectionError("{} exceeds its containing file".format(label))


def fourcc(number):
    # wInd3x reads uint32 little-endian, then displays its bytes big-endian.
    return number.to_bytes(4, "big").decode("ascii", errors="backslashreplace")


def parse_mse_directory(header, total_size):
    """Pure parser: header is the first DIRECTORY_END bytes, never all MSE data."""
    if total_size < DIRECTORY_END or total_size > MAX_MSE or len(header) < DIRECTORY_END:
        raise InspectionError("Firmware.MSE is truncated or exceeds the inspection limit")
    if b"Copyright" not in header[:0x100] or header[0xFF] != 0:
        raise InspectionError("Firmware.MSE copyright guard is not recognized")
    identifier, directory_offset, extended_offset, version = struct.unpack_from("<IIHH", header, 0x100)
    if (fourcc(identifier), directory_offset, extended_offset, version) != ("[hi]", 0x4000, 0x10C, 3):
        raise InspectionError("Firmware.MSE volume header does not match the reference format")
    if any(header[0x10C:DIRECTORY_START]):
        raise InspectionError("Firmware.MSE header padding is not zero as required by the reference parser")
    components = []
    for index in range(16):
        fields = struct.unpack_from("<10I", header, DIRECTORY_START + index * 40)
        target, name, used, offset, length, address, entry, checksum, revision, load_address = fields
        if fourcc(target) not in ("NAND", "ATA!"):
            continue
        bounded(offset, length, total_size, "MSE component {}".format(index))
        if length and offset < DIRECTORY_END:
            raise InspectionError("MSE component {} overlaps the directory".format(index))
        components.append({"index": index, "target": fourcc(target), "name": fourcc(name),
                           "used": used, "recorded_offset": offset, "length": length,
                           "raw_unconfirmed_fields": {"Address": address, "Entry": entry,
                                                      "Checksum": checksum, "Version": revision,
                                                      "LoadAddress": load_address}})
    return {"decoded_volume_id": fourcc(identifier), "version": version,
            "directory_start": DIRECTORY_START, "components": components}


def resolve_component(component, probe, total_size):
    """Apply only the prefix checks actually used by the pinned Nano 7 parser."""
    result = dict(component)
    offset, length = component["recorded_offset"], component["length"]
    prefix = None
    if len(probe) >= 24:
        zero1, unknown1, zero2, zero3, zero4, size = struct.unpack_from("<6I", probe)
        if zero1 == zero2 == zero3 == zero4 == 0 and unknown1 in (0, 4):
            # The Size field is recorded, not used as a validity condition.
            prefix = {"unknown1": unknown1, "size_field": size, "data_adjustment": 0x1000}
    data_offset = offset + (0x1000 if prefix else 0)
    bounded(data_offset, length, total_size, "adjusted MSE component {}".format(component["index"]))
    result.update({"prefix": prefix, "data_offset": data_offset})
    return result


def parse_img1_header(data, component_size):
    """Classify a bounded header; no executable ISA/load-address inference."""
    result = {"classification": "not a recognized IMG1 header", "encrypted": None}
    if len(data) < 4 or data[:4] not in IMAGE_KINDS:
        return result
    if len(data) < 28:
        raise InspectionError("Recognized IMG1 magic has a truncated header")
    magic, version, format_byte, entry, body_length, data_length, cert_offset, cert_length = struct.unpack_from("<4s3sB5I", data)
    kind, header_size, expected_version = IMAGE_KINDS[magic]
    result.update({"magic": magic.decode("ascii"), "image_version": version.decode("ascii", errors="backslashreplace"),
                   "device_family": kind, "format_byte": format_byte,
                   "header_size": header_size, "body_length": body_length, "data_length": data_length,
                   "certificate_offset_field": cert_offset, "certificate_length_field": cert_length,
                   "raw_unconfirmed_entrypoint_field": entry})
    if version != expected_version:
        result["classification"] = "recognized SoC magic; unsupported IMG1 version"
        return result
    bounded(header_size, data_length, component_size, "IMG1 declared data")
    bounded(header_size, body_length, component_size, "IMG1 declared body")
    if body_length > data_length:
        raise InspectionError("IMG1 body length exceeds declared data length")
    if cert_length:
        bounded(cert_offset, cert_length, data_length, "IMG1 certificate")
    result["classification"] = IMAGE_FORMATS.get(format_byte, "unknown IMG1 format byte")
    if format_byte in IMAGE_FORMATS:
        result["encrypted"] = format_byte in (1, 3)
    return result


def json_safe(value):
    """Normalize plist Data/date types before an optional JSON report is opened."""
    if isinstance(value, bytes):
        return {"type": "plist-data", "bytes": len(value), "hex": value.hex()}
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, plistlib.UID):
        return {"type": "plist-uid", "value": value.data}
    return value


def read_exact(stream, offset, length, total_size, label):
    bounded(offset, length, total_size, label)
    stream.seek(offset)
    data = stream.read(length)
    if len(data) != length:
        raise InspectionError("{} is truncated".format(label))
    return data


def inspect_zip(archive):
    """Inspect an already-open ZipFile (also usable with synthetic test fixtures)."""
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    if len(set(names)) != len(names):
        raise InspectionError("Archive has duplicate entry names")
    expected = {"Firmware.MSE", "N31.bootloader.rb3", "manifest.plist"}
    if set(names) != expected:
        raise InspectionError("Archive entries differ from the verified Nano 7 IPSW layout")
    for info in entries:
        if info.flag_bits & 1:
            raise InspectionError("A ZIP member itself is encrypted; unsupported archive")
    manifest_info = archive.getinfo("manifest.plist")
    if manifest_info.file_size > MAX_MANIFEST:
        raise InspectionError("manifest.plist exceeds 1 MiB")
    manifest = plistlib.loads(archive.read(manifest_info))
    mse_info = archive.getinfo("Firmware.MSE")
    if mse_info.file_size > MAX_MSE:
        raise InspectionError("Firmware.MSE exceeds 512 MiB")
    with archive.open(mse_info) as stream:
        header = read_exact(stream, 0, DIRECTORY_END, mse_info.file_size, "MSE directory")
        mse = parse_mse_directory(header, mse_info.file_size)
        resolved = []
        # Forward order avoids repeatedly decompressing the 176 MiB ZIP member.
        for component in sorted(mse["components"], key=lambda item: item["recorded_offset"]):
            if not component["length"]:
                continue
            offset, length = component["recorded_offset"], component["length"]
            probe_size = min(max(24, min(1024, length)), mse_info.file_size - offset)
            probe = read_exact(stream, offset, probe_size, mse_info.file_size, "component prefix/header")
            item = resolve_component(component, probe, mse_info.file_size)
            if item["prefix"]:
                data = read_exact(stream, item["data_offset"], min(1024, length), mse_info.file_size, "adjusted component header")
            else:
                data = probe[:length]
            item["first_64_bytes_hex"] = data[:64].hex()
            item["image"] = parse_img1_header(data, length)
            resolved.append(item)
        mse["components"] = sorted(resolved, key=lambda item: item["index"])
    boot_info = archive.getinfo("N31.bootloader.rb3")
    with archive.open(boot_info) as stream:
        boot_head = stream.read(min(64, boot_info.file_size))
    boot = {"entry": boot_info.filename, "bytes": boot_info.file_size,
            "first_64_bytes_hex": boot_head.hex(),
            "first_64_bytes_ascii": "".join(chr(ch) if 32 <= ch <= 126 else "." for ch in boot_head),
            "image": parse_img1_header(boot_head, boot_info.file_size)}
    return {"source_commit": SOURCE_COMMIT, "mode": "read-only; no extraction or decryption",
            "zip_entries": [{"name": info.filename, "bytes": info.file_size, "compressed_bytes": info.compress_size} for info in entries],
            "manifest": json_safe(manifest), "mse": mse, "bootloader": boot,
            "decryption": {"performed": False,
                "verified_reference_route": "wInd3x uses a connected compatible genuine iPod as its hardware AES service",
                "offline_key_or_decrypt_route_verified": False},
            "executable_architecture_or_import_address_determined": False}


def verify_container(path):
    md5, sha256 = hashlib.md5(), hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            md5.update(block)
            sha256.update(block)
    found = {"bytes": size, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}
    if found != {"bytes": EXPECTED_SIZE, "md5": EXPECTED_MD5, "sha256": EXPECTED_SHA256}:
        raise InspectionError("IPSW size/hash mismatch; expected Nano 7G 1.0.4 build 37A40005. Found: " + json.dumps(found))
    return found


def print_report(report):
    print("Verified Apple iPod nano 7G IPSW: 1.0.4 (37A40005)")
    print("MD5 and SHA-256 match; archive size {} bytes.".format(report["container"]["bytes"]))
    print("READ ONLY: no files extracted, no decryption, no device access.")
    print("ZIP: " + "; ".join("{} ({} bytes)".format(item["name"], item["bytes"]) for item in report["zip_entries"]))
    manifest = json.dumps(report["manifest"], ensure_ascii=True, sort_keys=True)
    print("Manifest: " + (manifest if len(manifest) <= 550 else manifest[:547] + "..."))
    print("MSE directory valid; offsets below are positions inside Firmware.MSE.")
    for item in report["mse"]["components"]:
        image = item["image"]
        detail = "{}; IMG1 format {}".format(image["classification"], image["format_byte"]) if "format_byte" in image else image["classification"]
        print("  {} {}: data=0x{:x}, bytes={}, {}{}".format(
            json.dumps(item["target"]), json.dumps(item["name"]), item["data_offset"], item["length"],
            "prefix +0x1000; " if item["prefix"] else "", detail))
    boot = report["bootloader"]
    print("Bootloader: " + boot["image"]["classification"])
    print("  first64 hex: " + boot["first_64_bytes_hex"])
    print("  first64 ASCII: " + json.dumps(boot["first_64_bytes_ascii"]))
    print("No CPU/ISA, load address, or decompilation readiness has been inferred.")
    print("Encrypted IMG1 needs decryption first; the verified reference uses genuine iPod hardware.")
    print("Signed/unencrypted IMG1 alone does not establish readable executable code.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipsw", type=Path, help="Path to the already-downloaded Nano 7G 1.0.4 IPSW")
    parser.add_argument("--out", type=Path, help="Optional NEW JSON report file (existing files are never overwritten)")
    args = parser.parse_args(argv)
    try:
        path = args.ipsw.expanduser()
        hashes = verify_container(path)
        with zipfile.ZipFile(path, "r") as archive:
            report = inspect_zip(archive)
        report["container"] = hashes
        report["input"] = str(path)
        # Serialize before opening an output, including all normalized plist values.
        serialized = json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
        print_report(report)
        if args.out:
            output = args.out.expanduser()
            with output.open("x", encoding="utf-8") as destination:
                destination.write(serialized)
            print("New JSON report: " + str(output))
        return 0
    except (InspectionError, OSError, zipfile.BadZipFile, plistlib.InvalidFileException,
            ValueError, EOFError, RuntimeError, RecursionError) as error:
        print("STOP: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
