#!/usr/bin/env python3
"""Reduce a PMTiles v3 basemap without changing its vector geometries.

The MVT protobuf is edited at wire level: geometry, feature type, IDs, extent,
layer version and tile/zoom assignment are copied byte-for-byte.  Only layers,
features and attribute tables are rebuilt.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sqlite3
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

VERSION = "1.0.0"
LAYERS = ("earth", "water", "roads", "places")


def varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data) or shift >= 70:
            raise ValueError("invalid protobuf/PMTiles varint")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7f) << shift
        if byte < 0x80:
            return value, pos
        shift += 7


def encode_varint(value: int) -> bytes:
    result = bytearray()
    while value > 0x7f:
        result.append((value & 0x7f) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def fields(message: bytes):
    """Yield (number, wire type, raw value, complete encoded field)."""
    pos = 0
    while pos < len(message):
        start = pos
        key, pos = varint(message, pos)
        wire = key & 7
        if wire == 0:
            value, pos = varint(message, pos)
        elif wire == 1:
            value, pos = message[pos:pos + 8], pos + 8
        elif wire == 2:
            length, pos = varint(message, pos)
            value, pos = message[pos:pos + length], pos + length
        elif wire == 5:
            value, pos = message[pos:pos + 4], pos + 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        if pos > len(message):
            raise ValueError("truncated protobuf message")
        yield key >> 3, wire, value, message[start:pos]


def length_field(number: int, value: bytes) -> bytes:
    return encode_varint((number << 3) | 2) + encode_varint(len(value)) + value


def packed_uints(value: bytes) -> list[int]:
    result = []
    pos = 0
    while pos < len(value):
        item, pos = varint(value, pos)
        result.append(item)
    return result


def value_as_string(value_message: bytes) -> str | None:
    for number, wire, value, _ in fields(value_message):
        if number == 1 and wire == 2:
            return value.decode("utf-8")
    return None


def filter_layer(layer: bytes) -> tuple[str, bytes] | None:
    parsed = list(fields(layer))
    name = next((v.decode() for n, w, v, _ in parsed if n == 1 and w == 2), None)
    if name not in LAYERS:
        return None
    features = [v for n, w, v, _ in parsed if n == 2 and w == 2]
    keys = [v.decode() for n, w, v, _ in parsed if n == 3 and w == 2]
    values = [v for n, w, v, _ in parsed if n == 4 and w == 2]
    wanted = {"places": {"name"}, "water": {"kind"}}.get(name, set())
    new_keys: list[str] = []
    new_values: list[bytes] = []
    key_indexes: dict[str, int] = {}
    value_indexes: dict[bytes, int] = {}
    kept_features: list[bytes] = []

    for feature in features:
        feature_fields = list(fields(feature))
        tags_value = next((v for n, w, v, _ in feature_fields if n == 2 and w == 2), b"")
        tags = packed_uints(tags_value)
        attributes: list[tuple[str, bytes]] = []
        for index in range(0, len(tags) - 1, 2):
            if tags[index] < len(keys) and tags[index + 1] < len(values):
                attributes.append((keys[tags[index]], values[tags[index + 1]]))
        if name == "water" and not any(
            key == "kind" and value_as_string(value) == "ocean"
            for key, value in attributes
        ):
            continue
        new_tags: list[int] = []
        for key, value in attributes:
            if key not in wanted:
                continue
            if key not in key_indexes:
                key_indexes[key] = len(new_keys)
                new_keys.append(key)
            if value not in value_indexes:
                value_indexes[value] = len(new_values)
                new_values.append(value)
            new_tags.extend((key_indexes[key], value_indexes[value]))
        rebuilt = bytearray()
        for number, wire, _, raw in feature_fields:
            if number != 2:
                rebuilt += raw
        if new_tags:
            rebuilt += length_field(2, b"".join(encode_varint(v) for v in new_tags))
        kept_features.append(bytes(rebuilt))

    if not kept_features:
        return None
    rebuilt_layer = bytearray()
    for number, wire, _, raw in parsed:
        if number not in (2, 3, 4):
            rebuilt_layer += raw
    for feature in kept_features:
        rebuilt_layer += length_field(2, feature)
    for key in new_keys:
        rebuilt_layer += length_field(3, key.encode())
    for value in new_values:
        rebuilt_layer += length_field(4, value)
    return name, bytes(rebuilt_layer)


def filter_mvt(tile: bytes) -> bytes:
    result = bytearray()
    for number, wire, value, raw in fields(tile):
        if number == 3 and wire == 2:
            filtered = filter_layer(value)
            if filtered:
                result += length_field(3, filtered[1])
        else:
            result += raw
    return bytes(result)


@dataclass
class Entry:
    tile_id: int
    offset: int
    length: int
    run_length: int


def directory(data: bytes) -> list[Entry]:
    pos = 0
    count, pos = varint(data, pos)
    ids, last = [], 0
    for _ in range(count):
        delta, pos = varint(data, pos); last += delta; ids.append(last)
    runs = []
    for _ in range(count):
        value, pos = varint(data, pos); runs.append(value)
    lengths = []
    for _ in range(count):
        value, pos = varint(data, pos); lengths.append(value)
    offsets, previous = [], 0
    for i in range(count):
        value, pos = varint(data, pos)
        offset = previous if value == 0 and i else value - 1
        offsets.append(offset); previous = offset + lengths[i]
    return [Entry(*items) for items in zip(ids, offsets, lengths, runs)]


def hilbert_xy(order: int, distance: int) -> tuple[int, int]:
    x = y = 0
    scale = 1
    while scale < (1 << order):
        rx = 1 & (distance // 2)
        ry = 1 & (distance ^ rx)
        if not ry:
            if rx:
                x, y = scale - 1 - x, scale - 1 - y
            x, y = y, x
        x += scale * rx; y += scale * ry
        distance //= 4; scale *= 2
    return x, y


def tile_id_to_zxy(tile_id: int) -> tuple[int, int, int]:
    z, first, width = 0, 0, 1
    while tile_id >= first + width:
        first += width; width *= 4; z += 1
    x, y = hilbert_xy(z, tile_id - first)
    return z, x, y


class Archive:
    def __init__(self, path: Path):
        self.file = path.open("rb")
        header = self.file.read(127)
        if header[:8] != b"PMTiles\x03":
            raise ValueError("input must be a PMTiles v3 archive")
        values = struct.unpack_from("<11Q", header, 8)
        (self.root_offset, self.root_length, self.metadata_offset,
         self.metadata_length, self.leaf_offset, self.leaf_length,
         self.tile_offset, _, _, _, _) = values
        self.internal_compression, self.tile_compression, self.tile_type = header[97:100]
        self.min_zoom, self.max_zoom = header[100:102]
        self.bounds = struct.unpack_from("<4i", header, 102)
        self.header = header

    def read(self, offset: int, length: int) -> bytes:
        self.file.seek(offset); return self.file.read(length)

    def decompress_internal(self, value: bytes) -> bytes:
        if self.internal_compression == 1:
            return value
        if self.internal_compression == 2:
            return gzip.decompress(value)
        raise ValueError("only uncompressed or gzip PMTiles directories are supported")

    def entries(self):
        root = directory(self.decompress_internal(self.read(self.root_offset, self.root_length)))
        for entry in root:
            if entry.run_length:
                yield entry
            else:
                leaf = self.read(self.leaf_offset + entry.offset, entry.length)
                yield from directory(self.decompress_internal(leaf))


def metadata_from_archive(archive: Archive) -> dict[str, str]:
    raw = archive.decompress_internal(archive.read(archive.metadata_offset, archive.metadata_length))
    source = json.loads(raw)
    metadata = {str(k): json.dumps(v, separators=(",", ":")) if isinstance(v, (dict, list)) else str(v)
                for k, v in source.items()}
    metadata.update({
        "format": "pbf", "minzoom": str(archive.min_zoom), "maxzoom": str(archive.max_zoom),
        "bounds": ",".join(str(value / 10_000_000) for value in archive.bounds),
        "json": json.dumps({"vector_layers": [
            {"id": "earth", "fields": {}}, {"id": "water", "fields": {"kind": "String"}},
            {"id": "roads", "fields": {}}, {"id": "places", "fields": {"name": "String"}},
        ]}, separators=(",", ":")),
    })
    return metadata


def run(source: Path, destination: Path, pmtiles: str) -> tuple[int, int]:
    if source.resolve() == destination.resolve():
        raise ValueError("input and output must have different names")
    executable = shutil.which(pmtiles) or (str(Path(pmtiles).resolve()) if Path(pmtiles).is_file() else None)
    if not executable:
        raise FileNotFoundError(f"pmtiles executable not found: {pmtiles}")
    version = subprocess.run([executable, "version"], check=True, text=True, capture_output=True).stdout
    if "1.31.2" not in version:
        raise RuntimeError(f"expected pmtiles 1.31.2, got: {version.strip()}")
    archive = Archive(source)
    if archive.tile_type != 1:
        raise ValueError("input tiles must be MVT (PMTiles tile type 1)")
    if archive.tile_compression not in (1, 2):
        raise ValueError("only uncompressed or gzip MVT tiles are supported")
    read_count = write_count = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="basemap-filter-") as temp:
        mbtiles = Path(temp) / "reduced.mbtiles"
        db = sqlite3.connect(mbtiles)
        db.executescript("CREATE TABLE metadata (name TEXT, value TEXT);"
                         "CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB);"
                         "CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);")
        db.executemany("INSERT INTO metadata VALUES (?, ?)", metadata_from_archive(archive).items())
        for entry in archive.entries():
            compressed = archive.read(archive.tile_offset + entry.offset, entry.length)
            tile = gzip.decompress(compressed) if archive.tile_compression == 2 else compressed
            filtered = filter_mvt(tile)
            for tile_id in range(entry.tile_id, entry.tile_id + entry.run_length):
                read_count += 1
                if not filtered:
                    continue
                z, x, y = tile_id_to_zxy(tile_id)
                output = gzip.compress(filtered, mtime=0)
                db.execute("INSERT INTO tiles VALUES (?, ?, ?, ?)", (z, x, (1 << z) - 1 - y, output))
                write_count += 1
        db.commit(); db.close(); archive.file.close()
        subprocess.run([executable, "convert", "--force", str(mbtiles), str(destination)], check=True)
    return read_count, write_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pmtiles", default="pmtiles", help="pmtiles 1.31.2 executable")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()
    read_count, write_count = run(args.input, args.output, args.pmtiles)
    print(f"Filtered {read_count} tiles; wrote {write_count} non-empty tiles to {args.output}")


if __name__ == "__main__":
    main()
