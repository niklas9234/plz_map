import gzip
import importlib.util
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("filter_pmtiles", Path(__file__).with_name("filter_pmtiles.py"))
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def field(number, value):
    return module.length_field(number, value)


def string_value(value):
    return field(1, value.encode())


def feature(tags, geometry=b"\x09\x02\x04", feature_type=1):
    packed = b"".join(module.encode_varint(value) for value in tags)
    return field(2, packed) + module.encode_varint(3 << 3) + module.encode_varint(feature_type) + field(4, geometry)


def layer(name, features, keys=(), values=()):
    result = field(1, name.encode())
    result += b"".join(field(2, value) for value in features)
    result += b"".join(field(3, value.encode()) for value in keys)
    result += b"".join(field(4, value) for value in values)
    result += module.encode_varint(5 << 3) + module.encode_varint(4096)
    result += module.encode_varint(15 << 3) + module.encode_varint(2)
    return result


def decoded_layers(tile):
    return [(module.filter_layer(value) or (None,))[0]
            for number, wire, value, _ in module.fields(tile) if number == 3 and wire == 2]


class FilterTest(unittest.TestCase):
    def test_keeps_expected_layers_and_only_ocean(self):
        water = layer("water", [feature([0, 0]), feature([0, 1])], ["kind"],
                      [string_value("ocean"), string_value("lake")])
        places = layer("places", [feature([0, 0, 1, 1])], ["name", "population"],
                       [string_value("Berlin"), string_value("1")])
        tile = b"".join(field(3, item) for item in [water, places, layer("buildings", [feature([])])])
        output = module.filter_mvt(tile)
        layers = [value for number, wire, value, _ in module.fields(output) if number == 3]
        self.assertEqual([module.filter_layer(value)[0] for value in layers], ["water", "places"])
        water_features = [v for n, w, v, _ in module.fields(layers[0]) if n == 2]
        self.assertEqual(len(water_features), 1)
        place_keys = [v.decode() for n, w, v, _ in module.fields(layers[1]) if n == 3]
        self.assertEqual(place_keys, ["name"])

    def test_geometry_type_extent_and_version_are_byte_identical(self):
        geometry = b"\x09\xff\x01\x80\x02\x12\x06\x04"
        source = layer("roads", [feature([0, 0], geometry, 2)], ["class"], [string_value("motorway")])
        output = module.filter_layer(source)[1]
        source_feature = next(v for n, w, v, _ in module.fields(source) if n == 2)
        output_feature = next(v for n, w, v, _ in module.fields(output) if n == 2)
        source_invariants = [(n, raw) for n, w, v, raw in module.fields(source_feature) if n in (3, 4)]
        output_invariants = [(n, raw) for n, w, v, raw in module.fields(output_feature) if n in (3, 4)]
        self.assertEqual(output_invariants, source_invariants)
        self.assertEqual([(n, raw) for n, w, v, raw in module.fields(output) if n in (5, 15)],
                         [(n, raw) for n, w, v, raw in module.fields(source) if n in (5, 15)])

    def test_empty_layers_and_tiles_are_removed(self):
        lake = layer("water", [feature([0, 0])], ["kind"], [string_value("lake")])
        self.assertEqual(module.filter_mvt(field(3, lake)), b"")

    def test_hilbert_tile_ids_preserve_zoom_assignment(self):
        expected = [(0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)]
        self.assertEqual([module.tile_id_to_zxy(i) for i in range(5)], expected)


if __name__ == "__main__":
    unittest.main()
