#!/usr/bin/env python3
"""Inventory the plaintext resource volume in Nano 7 build 37A40005.

Python standard library only. Reads the IPSW, copies only the bounded resource
body to a private temporary file, and writes an optional NEW JSON report.
Does not mount, decrypt, extract individual files, or communicate with devices.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys
import tempfile
import zipfile

INSPECTOR_SHA256 = "9a807ef768bbf2c1e862042a9eed3a4d7009e6673bd81336a4c7dc1923372fef"
MAX_BODY = 192 * 1024 * 1024
MAX_ENTRIES = 100000
MAX_FILES = 20000
MAX_DIRECTORIES = 4096
MAX_DEPTH = 32
MAX_DIRECTORY_BYTES = 32 * 1024 * 1024
MAX_HASH_BYTES = 192 * 1024 * 1024
MAX_FAT_BYTES = 1024 * 1024
MAX_PATH_CHARACTERS = 4096
MAX_RETAINED_WARNINGS = 100


class ResourceError(ValueError):
    pass


def u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def read_at(stream, offset, length, limit):
    if offset < 0 or length < 0 or offset > limit or length > limit - offset:
        raise ResourceError("Read exceeds resource body")
    stream.seek(offset)
    result = stream.read(length)
    if len(result) != length:
        raise ResourceError("Truncated resource body")
    return result


def geometry(boot, body_size):
    if len(boot) < 512 or boot[510:512] != b"\x55\xaa":
        raise ResourceError("Resource body has no FAT boot-sector signature")
    if not (boot[0] == 0xE9 or (boot[0] == 0xEB and boot[2] == 0x90)):
        raise ResourceError("Resource body has no recognized FAT boot jump")
    bps, spc = u16(boot, 11), boot[13]
    reserved, fats, root_entries = u16(boot, 14), boot[16], u16(boot, 17)
    total16, total32, fat_sectors = u16(boot, 19), u32(boot, 32), u16(boot, 22)
    if bps not in (512, 1024, 2048, 4096) or not spc or spc > 128 or spc & (spc - 1):
        raise ResourceError("Invalid FAT sector/cluster geometry")
    if not reserved or fats not in (1, 2) or not root_entries or not fat_sectors:
        raise ResourceError("Unsupported FAT metadata geometry")
    if root_entries * 32 % bps:
        raise ResourceError("FAT16 fixed root directory is not sector aligned")
    if fat_sectors * bps > MAX_FAT_BYTES:
        raise ResourceError("FAT metadata exceeds inventory memory limit")
    if total16 and total32:
        raise ResourceError("Conflicting FAT total-sector fields")
    total = total16 or total32
    root_sectors = (root_entries * 32 + bps - 1) // bps
    data_start = reserved + fats * fat_sectors + root_sectors
    if not total or data_start >= total or total * bps > body_size:
        raise ResourceError("FAT volume does not fit inside IMG1 BodyLength")
    clusters = (total - data_start) // spc
    if not 4085 <= clusters < 65525:
        kind = "FAT12" if clusters < 4085 else "FAT32"
        raise ResourceError("Calculated filesystem is {}; this helper supports FAT16 only".format(kind))
    if fat_sectors * bps < (clusters + 2) * 2:
        raise ResourceError("FAT cannot contain all declared clusters")
    return {"type": "FAT16", "bytes_per_sector": bps, "sectors_per_cluster": spc,
            "reserved_sectors": reserved, "fat_copies": fats,
            "fat_sectors": fat_sectors, "root_entries": root_entries,
            "total_sectors": total, "volume_bytes": total * bps,
            "body_bytes": body_size, "cluster_count": clusters,
            "root_offset": (reserved + fats * fat_sectors) * bps,
            "data_offset": data_start * bps,
            "volume_label": boot[43:54].decode("ascii", "backslashreplace").rstrip(),
            "oem": boot[3:11].decode("ascii", "backslashreplace")}


def short_name(entry):
    raw = bytearray(entry[:11])
    if raw[0] == 5:
        raw[0] = 0xE5
    base = bytes(raw[:8]).decode("cp437").rstrip(" ")
    ext = bytes(raw[8:11]).decode("cp437").rstrip(" ")
    if entry[12] & 8:
        base = base.lower()
    if entry[12] & 16:
        ext = ext.lower()
    return base + ("." + ext if ext else "")


def long_name(slots, entry):
    """Return a validated VFAT name or None; callers retain the short name."""
    if not slots or len(slots) > 20 or slots[0][0] != (0x40 | len(slots)):
        return None
    checksum = 0
    for byte in entry[:11]:
        checksum = (((checksum & 1) << 7) + (checksum >> 1) + byte) & 255
    for index, slot in enumerate(slots):
        ordinal = len(slots) - index
        if index == 0:
            ordinal |= 0x40
        if slot[0] != ordinal or slot[11] != 15 or slot[12] != 0 or slot[13] != checksum or u16(slot, 26):
            return None
    units = []
    for slot in reversed(slots):
        units.extend(struct.unpack("<13H", slot[1:11] + slot[14:26] + slot[28:32]))
    if 0 in units:
        end = units.index(0)
        if any(value != 0xFFFF for value in units[end + 1:]):
            return None
        units = units[:end]
    if not units or len(units) > 255 or 0xFFFF in units:
        return None
    try:
        return struct.pack("<{}H".format(len(units)), *units).decode("utf-16-le")
    except UnicodeError:
        return None


def file_kind(head):
    for magic, kind in ((b"\x00\x01\x00\x00", "TrueType candidate"),
                        (b"OTTO", "OpenType candidate"), (b"ttcf", "font collection candidate"),
                        (b"\x89PNG\r\n\x1a\n", "PNG"), (b"\xff\xd8\xff", "JPEG"),
                        (b"bplist00", "binary plist")):
        if head.startswith(magic):
            return kind
    if head.startswith(b"\x03\x00\x00\x00") and len(head) >= 16 and head[12:16] in (b"paMB", b"mTDL"):
        return "SilverDB resource candidate"
    return "unclassified"


class FAT16:
    def __init__(self, stream, body_size):
        self.stream, self.body_size = stream, body_size
        self.g = geometry(read_at(stream, 0, 512, body_size), body_size)
        g = self.g
        self.cluster_size = g["bytes_per_sector"] * g["sectors_per_cluster"]
        self.fat = read_at(stream, g["reserved_sectors"] * g["bytes_per_sector"],
                           g["fat_sectors"] * g["bytes_per_sector"], body_size)
        for index in range(1, g["fat_copies"]):
            copy = read_at(stream, (g["reserved_sectors"] + index * g["fat_sectors"]) * g["bytes_per_sector"],
                           len(self.fat), body_size)
            if copy != self.fat:
                raise ResourceError("FAT copies differ; no repair was attempted")
        media = read_at(stream, 21, 1, body_size)[0]
        if media != 0xF0 and not 0xF8 <= media <= 0xFF:
            raise ResourceError("Invalid FAT media descriptor")
        if u16(self.fat, 0) != (0xFF00 | media) or u16(self.fat, 2) & 0x3FFF != 0x3FFF:
            raise ResourceError("Invalid FAT reserved entries")
        self.owners = {}
        self.entries = self.directory_bytes = self.hash_bytes = 0
        self.files, self.directories, self.warnings = [], [], []
        self.warning_count = 0

    def chain(self, start, owner):
        if start == 0:
            return []
        result = []
        current = start
        while True:
            if current < 2 or current > self.g["cluster_count"] + 1 or current >= 0xFFF0:
                raise ResourceError("Out-of-range/reserved cluster in " + owner)
            if current in self.owners:
                raise ResourceError("Repeated or cross-linked cluster in " + owner)
            self.owners[current] = owner
            result.append(current)
            if len(self.owners) > self.g["cluster_count"]:
                raise ResourceError("Cluster visit budget exceeded")
            value = u16(self.fat, current * 2)
            if value >= 0xFFF8:
                return result
            if value < 2 or value >= 0xFFF0:
                raise ResourceError("Free, bad, or reserved cluster link in " + owner)
            current = value

    def cluster(self, number):
        offset = self.g["data_offset"] + (number - 2) * self.cluster_size
        return read_at(self.stream, offset, self.cluster_size, self.g["volume_bytes"])

    def directory(self, start, path, depth):
        if depth > MAX_DEPTH or len(self.directories) >= MAX_DIRECTORIES:
            raise ResourceError("Directory traversal limit exceeded")
        self.directories.append(path or "/")
        if depth == 0:
            size = self.g["root_entries"] * 32
            blocks = [read_at(self.stream, self.g["root_offset"], size, self.body_size)]
        else:
            if start < 2:
                raise ResourceError("Subdirectory has no data cluster")
            chain = self.chain(start, path)
            blocks = (self.cluster(c) for c in chain)
        pending = []
        for block in blocks:
            self.directory_bytes += len(block)
            if self.directory_bytes > MAX_DIRECTORY_BYTES:
                raise ResourceError("Directory byte budget exceeded")
            for offset in range(0, len(block), 32):
                entry = block[offset:offset + 32]
                if entry[0] == 0:
                    return
                self.entries += 1
                if self.entries > MAX_ENTRIES:
                    raise ResourceError("Directory entry budget exceeded")
                if entry[0] == 0xE5:
                    pending = []
                    continue
                attr = entry[11]
                if attr == 15:
                    pending.append(entry)
                    if len(pending) > 20:
                        pending = []
                    continue
                if attr & 8:
                    pending = []
                    continue
                short = short_name(entry)
                name = long_name(pending, entry)
                if pending and name is None:
                    self.warning_count += 1
                    if len(self.warnings) < MAX_RETAINED_WARNINGS:
                        self.warnings.append("Invalid long name; retained short name: " + path + "/" + short)
                pending = []
                name = name or short
                if short in (".", ".."):
                    continue
                if not name or name in (".", "..") or "/" in name or "\\" in name or any(ord(c) < 32 for c in name):
                    raise ResourceError("Invalid resource filename")
                if attr & 0xC0 or u16(entry, 20):
                    raise ResourceError("Unsupported FAT16 entry fields")
                full = path + "/" + name
                if len(full) > MAX_PATH_CHARACTERS:
                    raise ResourceError("Resource path length limit exceeded")
                cluster, size = u16(entry, 26), u32(entry, 28)
                if attr & 16:
                    self.directory(cluster, full, depth + 1)
                else:
                    self.file(cluster, size, full, short)

    def file(self, start, size, path, short):
        if len(self.files) >= MAX_FILES or size > self.body_size:
            raise ResourceError("File count/size limit exceeded")
        if self.hash_bytes + size > MAX_HASH_BYTES:
            raise ResourceError("File hashing byte budget exceeded")
        chain = self.chain(start, path)
        if len(chain) * self.cluster_size < size:
            raise ResourceError("File cluster chain is shorter than its size: " + path)
        sha = hashlib.sha256()
        remaining = size
        head = b""
        for c in chain:
            if not remaining:
                break
            block = self.cluster(c)[:remaining]
            if len(head) < 32:
                head += block[:32 - len(head)]
            sha.update(block)
            remaining -= len(block)
        self.hash_bytes += size
        self.files.append({"path": path, "short_name": short, "bytes": size,
                           "sha256": sha.hexdigest(), "first_32_bytes_hex": head.hex(),
                           "kind": file_kind(head), "allocated_clusters": len(chain)})

    def inventory(self):
        self.directory(0, "", 0)
        paths = [item["path"].casefold() for item in self.files] + [item.casefold() for item in self.directories]
        if len(paths) != len(set(paths)):
            raise ResourceError("Duplicate resource paths")
        return {"filesystem": self.g, "status": "complete", "files": sorted(self.files, key=lambda x: x["path"]),
                "directories": sorted(self.directories), "warnings": self.warnings,
                "warning_count": self.warning_count,
                "hashed_file_bytes": self.hash_bytes, "allocated_clusters_visited": len(self.owners),
                "scope": "allocated directory entries only; deleted files and unallocated data are not recovered"}


def inspect_resources(path, inspector_path):
    if hashlib.sha256(inspector_path.read_bytes()).hexdigest() != INSPECTOR_SHA256:
        raise ResourceError("Existing inspector checksum mismatch; use the published inspector version")
    api = runpy.run_path(str(inspector_path))
    hashes = api["verify_container"](path)
    with zipfile.ZipFile(path, "r") as archive:
        report = api["inspect_zip"](archive)
        matches = [item for item in report["mse"]["components"] if item["name"] == "rsrc"]
        if len(matches) != 1:
            raise ResourceError("Expected exactly one resource component")
        resource = matches[0]
        image = resource["image"]
        if image.get("magic") != "8740" or image.get("image_version") != "2.0" or image.get("format_byte") != 4 or image.get("encrypted") is not False:
            raise ResourceError("Resource component is not the expected plaintext IMG1")
        length = image["body_length"]
        if not 512 <= length <= MAX_BODY:
            raise ResourceError("Resource body size exceeds inspection limit")
        body_offset = resource["data_offset"] + image["header_size"]
        api["bounded"](image["header_size"], length, resource["length"], "resource body")
        with tempfile.TemporaryFile(prefix="nano7-resource-") as body:
            with archive.open("Firmware.MSE") as source:
                source.seek(body_offset)
                remaining = length
                while remaining:
                    block = source.read(min(1024 * 1024, remaining))
                    if not block:
                        raise ResourceError("Truncated resource body in ZIP stream")
                    body.write(block)
                    remaining -= len(block)
            body.flush()
            result = FAT16(body, length).inventory()
    result.update({"input": str(path), "container": hashes,
                   "firmware": "iPod nano 7G 1.0.4 (37A40005)",
                   "mode": "read-only source; temporary resource copy removed; no device access",
                   "main_os_decrypted_or_analyzed": False})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipsw", type=Path)
    parser.add_argument("--inspector", type=Path, default=Path(__file__).with_name("inspect-nano7-firmware.py"))
    parser.add_argument("--out", type=Path, help="Optional NEW JSON report; never overwrites files")
    args = parser.parse_args(argv)
    try:
        if args.out and args.out.expanduser().exists():
            raise ResourceError("Report already exists; choose a new --out filename")
        result = inspect_resources(args.ipsw.expanduser(), args.inspector.expanduser())
        serialized = json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
        if args.out:
            with args.out.expanduser().open("x", encoding="utf-8") as output:
                output.write(serialized)
        g = result["filesystem"]
        print("VERIFIED: {} resource volume; {} bytes, {}-byte clusters.".format(g["type"], g["volume_bytes"], g["bytes_per_sector"] * g["sectors_per_cluster"]))
        print("Complete inventory: {} files, {} directories; {} logical file bytes hashed.".format(len(result["files"]), len(result["directories"]), result["hashed_file_bytes"]))
        candidates = [f for f in result["files"] if f["kind"] != "unclassified" or "/fonts/" in f["path"].lower()]
        for item in candidates[:30]:
            print(json.dumps(item["path"], ensure_ascii=True) + "  " + str(item["bytes"]) + " bytes; " + item["kind"])
        if len(candidates) > 30:
            print("Additional candidates in JSON: {}".format(len(candidates) - 30))
        print("Warnings: {}. Main OS remains encrypted.".format(result["warning_count"]))
        if args.out:
            print("Report: " + str(args.out.expanduser()))
        else:
            print(serialized, end="")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, EOFError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
