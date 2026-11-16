from typing import Tuple

import pyproj
from rasterio.transform import Affine


def get_transformer(from_crs: str, to_crs: str = "EPSG:4326") -> pyproj.Transformer:
    """Create a pyproj Transformer between CRSs, with always_xy=True (lon, lat)."""
    return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True)


def project_coords(
    x: float, y: float, from_crs: str, to_crs: str = "EPSG:4326"
) -> Tuple[float, float]:
    """Project a point (x, y) from source CRS to destination CRS (default EPSG:4326 [lon, lat])."""
    transformer = get_transformer(from_crs, to_crs)
    lon, lat = transformer.transform(x, y)
    return float(lon), float(lat)


def unproject_coords(
    lon: float, lat: float, to_crs: str, from_crs: str = "EPSG:4326"
) -> Tuple[float, float]:
    """Project (lon, lat) in EPSG:4326 to target CRS (e.g. UTM)."""
    transformer = get_transformer(from_crs, to_crs)
    x, y = transformer.transform(lon, lat)
    return float(x), float(y)


def compute_bounds_wgs84(
    width: int, height: int, transform: Affine, from_crs: str
) -> Tuple[float, float, float, float]:
    """Compute [min_lon, min_lat, max_lon, max_lat] in EPSG:4326 from raster dimensions and transform."""
    corners_raster = [(0, 0), (width, 0), (width, height), (0, height)]
    xs, ys = [], []
    for col, row in corners_raster:
        px, py = transform * (col, row)
        lon, lat = project_coords(px, py, from_crs, "EPSG:4326")
        xs.append(lon)
        ys.append(lat)
    return (min(xs), min(ys), max(xs), max(ys))


def pixel_to_geo(col: float, row: float, transform: Affine, from_crs: str) -> Tuple[float, float]:
    """Convert raster pixel (col, row) to geographic coordinates (lon, lat) in EPSG:4326."""
    px, py = transform * (col, row)
    return project_coords(px, py, from_crs, "EPSG:4326")


def geo_to_pixel(lon: float, lat: float, transform: Affine, from_crs: str) -> Tuple[float, float]:
    """Convert geographic coordinates (lon, lat) in EPSG:4326 to raster pixel (col, row)."""
    px, py = unproject_coords(lon, lat, from_crs, "EPSG:4326")
    inv_transform = ~transform
    col, row = inv_transform * (px, py)
    return float(col), float(row)


def compute_acreage(width: int, height: int, pixel_size_m: float) -> float:
    """Calculate acreage for a raster grid: 1 acre = 4046.8564224 square meters."""
    sq_meters = width * height * (pixel_size_m**2)
    return float(sq_meters / 4046.8564224)
