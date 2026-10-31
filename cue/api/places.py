from __future__ import annotations

import math

CITIES: tuple[tuple[str, float, float], ...] = (
    ("New York, NY", 40.71, -74.01),
    ("Brooklyn, NY", 40.68, -73.94),
    ("Los Angeles, CA", 34.05, -118.24),
    ("San Francisco, CA", 37.77, -122.42),
    ("Oakland, CA", 37.80, -122.27),
    ("San Diego, CA", 32.72, -117.16),
    ("Sacramento, CA", 38.58, -121.49),
    ("Seattle, WA", 47.61, -122.33),
    ("Portland, OR", 45.52, -122.68),
    ("Chicago, IL", 41.88, -87.63),
    ("Detroit, MI", 42.33, -83.05),
    ("Ann Arbor, MI", 42.28, -83.74),
    ("Grand Rapids, MI", 42.96, -85.67),
    ("Kalamazoo, MI", 42.29, -85.59),
    ("Lansing, MI", 42.73, -84.56),
    ("Milwaukee, WI", 43.04, -87.91),
    ("Madison, WI", 43.07, -89.40),
    ("Minneapolis, MN", 44.98, -93.27),
    ("Boston, MA", 42.36, -71.06),
    ("Philadelphia, PA", 39.95, -75.17),
    ("Pittsburgh, PA", 40.44, -80.00),
    ("Washington, DC", 38.91, -77.04),
    ("Baltimore, MD", 39.29, -76.61),
    ("Richmond, VA", 37.54, -77.44),
    ("Raleigh, NC", 35.78, -78.64),
    ("Charlotte, NC", 35.23, -80.84),
    ("Atlanta, GA", 33.75, -84.39),
    ("Nashville, TN", 36.16, -86.78),
    ("Memphis, TN", 35.15, -90.05),
    ("Louisville, KY", 38.25, -85.76),
    ("Cincinnati, OH", 39.10, -84.51),
    ("Columbus, OH", 39.96, -83.00),
    ("Cleveland, OH", 41.50, -81.69),
    ("Indianapolis, IN", 39.77, -86.16),
    ("St. Louis, MO", 38.63, -90.20),
    ("Kansas City, MO", 39.10, -94.58),
    ("Omaha, NE", 41.26, -95.93),
    ("Denver, CO", 39.74, -104.99),
    ("Salt Lake City, UT", 40.76, -111.89),
    ("Phoenix, AZ", 33.45, -112.07),
    ("Las Vegas, NV", 36.17, -115.14),
    ("Austin, TX", 30.27, -97.74),
    ("Dallas, TX", 32.78, -96.80),
    ("Houston, TX", 29.76, -95.37),
    ("San Antonio, TX", 29.42, -98.49),
    ("New Orleans, LA", 29.95, -90.07),
    ("Miami, FL", 25.76, -80.19),
    ("Orlando, FL", 28.54, -81.38),
    ("Tampa, FL", 27.95, -82.46),
    ("Albuquerque, NM", 35.08, -106.65),
    ("Toronto, ON", 43.65, -79.38),
    ("Montreal, QC", 45.50, -73.57),
    ("Vancouver, BC", 49.28, -123.12),
    ("London, UK", 51.51, -0.13),
    ("Manchester, UK", 53.48, -2.24),
    ("Mumbai, India", 19.08, 72.88),
    ("Delhi, India", 28.61, 77.21),
    ("Bengaluru, India", 12.97, 77.59),
    ("Chennai, India", 13.08, 80.27),
    ("Kolkata, India", 22.57, 88.36),
    ("Hyderabad, India", 17.39, 78.49),
    ("Pune, India", 18.52, 73.86),
)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def nearest_city(lat: float, lon: float, within_km: float = 120) -> str | None:
    name, km = min(((n, distance_km(lat, lon, la, lo)) for n, la, lo in CITIES), key=lambda pair: pair[1])
    return name if km <= within_km else None


def top_areas(points: list[dict], limit: int = 5) -> list[dict]:
    areas: dict[str, dict] = {}
    for point in sorted(points, key=lambda p: -(p.get("affinity") or 0)):
        city = nearest_city(point["lat"], point["lon"])
        if city is None or city in areas:
            continue
        areas[city] = {"name": city, "affinity": point.get("affinity"), "lat": point["lat"], "lon": point["lon"]}
        if len(areas) == limit:
            break
    return list(areas.values())
