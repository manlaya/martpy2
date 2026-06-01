# -*- coding: utf-8 -*-

import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from pyproj.crs import CRS


def read_bln(bln, epsg=None, unit=1, sep=' '):
    """
    Read a bln file with epsg projection

    Parameters
    ----------
    bln : str
        bln file to read
    epsg : str
        code epsg de la projection
    unit : int or float
        correction factor for converting the units of the bln file in meters
        example : 1000 if bln in km

    Return
    ------
    geopandas.DataFrame
    """
    features = []
    with open(bln, encoding='ISO-8859-1') as fbln:
        line = fbln.readline()
        id_ent = 0
        while line.strip():
            fields = line.strip().split(sep=sep)
            nb_pts, flag = int(fields[0]), int(fields[1])
            label = fields[2] if len(fields) > 2 else None
            entitie = []
            for _ in range(nb_pts):
                line = fbln.readline()
                entitie.append(
                    tuple(float(value)*unit for value in line.strip().split())
                )
            if len(entitie) == 1:
                geom = Point(entitie)
            elif len(entitie) > 1 and entitie[0] != entitie[-1]:
                geom = LineString(entitie)
            elif len(entitie) > 1 and entitie[0] == entitie[-1]:
                geom = Polygon(entitie)
            line = fbln.readline()
            features.append({'geometry': geom, 'filter_flag': flag, 'label': label})
            id_ent += 1
    gdf = gpd.GeoDataFrame(features, crs=CRS.from_epsg(epsg) if epsg else None)
    return gdf


def write_bln(gdf, filepath, sep=' '):
    with open(filepath, 'w') as f:
        for _, row in gdf.iterrows():
            geom = row.geometry
            flag = row.get('filter_flag', 0)
            label = row.get('label', 'feature')

            if isinstance(geom, Point):
                coords = [(geom.x, geom.y)]
            elif isinstance(geom, (LineString, Polygon)):
                coords = list(geom.exterior.coords) \
                    if isinstance(geom, Polygon) else list(geom.coords)

            f.write(f"{len(coords)}{sep}{flag}{sep}{label}{sep}xy\n")
            for x, y in coords:
                f.write(f"{x}{sep}{y}\n")
    return
