import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union
from shapely.validation import make_valid

INPUT = "plz-2stellig.geojson"
OUTPUT = "plz-2stellig-clean.geojson"
REPORT = "plz-clean-report.csv"

# ------------------------------------------------------------
# Einstellungen
# ------------------------------------------------------------

# Ein abgetrenntes Teilstück gilt als klein, wenn es weniger
# als diesen Anteil der größten Fläche derselben PLZ besitzt.
MAX_RELATIVE_AREA = 0.03       # 3 %

# Zusätzlich können extrem kleine Flächen immer bereinigt werden.
MAX_ABSOLUTE_AREA_KM2 = 10     # 10 km²


# ------------------------------------------------------------
# Daten laden
# ------------------------------------------------------------

gdf = gpd.read_file(INPUT)

if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:4326")

# Für Flächen- und Längenberechnungen nicht in WGS84 arbeiten.
# EPSG:3035 ist für Europa geeignet.
gdf = gdf.to_crs("EPSG:3035")


# ------------------------------------------------------------
# Alle Features derselben PLZ zusammenfassen
# ------------------------------------------------------------

original_properties = (
    gdf.drop(columns="geometry")
       .drop_duplicates(subset="plz")
       .set_index("plz")
)

dissolved = gdf.dissolve(by="plz").reset_index()

dissolved["geometry"] = dissolved.geometry.apply(make_valid)


# ------------------------------------------------------------
# PLZ in einzelne zusammenhängende Polygone zerlegen
# ------------------------------------------------------------

parts = dissolved[["plz", "geometry"]].explode(
    index_parts=False
).reset_index(drop=True)

parts["area"] = parts.geometry.area


# größte Fläche jeder PLZ
main_area = parts.groupby("plz")["area"].max().to_dict()


# ------------------------------------------------------------
# Zielgeometrien vorbereiten
# ------------------------------------------------------------

result_parts = {}

for plz in dissolved["plz"]:
    result_parts[plz] = []


report = []


# ------------------------------------------------------------
# Jedes Teilpolygon prüfen
# ------------------------------------------------------------

for idx, part in parts.iterrows():

    plz = part["plz"]
    geom = part.geometry
    area = geom.area

    largest = main_area[plz]

    # Ist dies die Hauptfläche?
    is_main = abs(area - largest) < 0.01

    if is_main:
        result_parts[plz].append(geom)
        continue

    area_km2 = area / 1_000_000
    relative_size = area / largest

    is_small = (
        relative_size < MAX_RELATIVE_AREA
        or area_km2 < MAX_ABSOLUTE_AREA_KM2
    )

    # Größere getrennte Gebiete behalten
    if not is_small:
        result_parts[plz].append(geom)
        continue


    # --------------------------------------------------------
    # angrenzende andere PLZ suchen
    # --------------------------------------------------------

    candidates = []

    for other_idx, other in dissolved.iterrows():

        other_plz = other["plz"]

        if other_plz == plz:
            continue

        other_geom = other.geometry

        # Nur tatsächliche Nachbarn berücksichtigen
        if not geom.intersects(other_geom):
            continue

        # Länge der gemeinsamen Grenze
        shared = (
            geom.boundary
                .intersection(other_geom.boundary)
                .length
        )

        if shared > 0:
            candidates.append(
                (shared, other_plz)
            )


    # --------------------------------------------------------
    # Keine angrenzende PLZ:
    # vermutlich Insel -> behalten
    # --------------------------------------------------------

    if not candidates:

        result_parts[plz].append(geom)

        report.append({
            "original_plz": plz,
            "new_plz": plz,
            "area_km2": area_km2,
            "action": "kept_island_or_isolated"
        })

        continue


    # --------------------------------------------------------
    # PLZ mit längster gemeinsamer Grenze auswählen
    # --------------------------------------------------------

    candidates.sort(reverse=True)

    shared_length, target_plz = candidates[0]

    result_parts[target_plz].append(geom)

    report.append({
        "original_plz": plz,
        "new_plz": target_plz,
        "area_km2": area_km2,
        "relative_size": relative_size,
        "shared_border_m": shared_length,
        "action": "moved"
    })


# ------------------------------------------------------------
# Geometrien wieder pro PLZ zusammenbauen
# ------------------------------------------------------------

rows = []

for plz, geometries in result_parts.items():

    if not geometries:
        continue

    geom = unary_union(geometries)
    geom = make_valid(geom)

    rows.append({
        "plz": plz,
        "geometry": geom
    })


clean = gpd.GeoDataFrame(
    rows,
    crs="EPSG:3035"
)


# Fläche neu berechnen
clean["qkm"] = clean.geometry.area / 1_000_000


# zurück nach WGS84 für MapLibre
clean = clean.to_crs("EPSG:4326")


# ------------------------------------------------------------
# speichern
# ------------------------------------------------------------

clean.to_file(
    OUTPUT,
    driver="GeoJSON"
)

pd.DataFrame(report).to_csv(
    REPORT,
    index=False
)

print(f"Fertig: {OUTPUT}")
print(f"Report: {REPORT}")