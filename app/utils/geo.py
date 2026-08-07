import math
import requests


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two lat/lng points, in kilometers.
    Plain-Python formula - no PostGIS or database extension required, so this
    works whether you're on SQLite locally or Postgres in production."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def geocode_pincode(pincode: str, country: str = "India"):
    """Free, keyless geocoding via OpenStreetMap Nominatim. Returns (lat, lng)
    or None. Called once when a doctor saves their profile, then cached on
    their record - never called again per SOS trigger."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"postalcode": pincode, "country": country, "format": "json", "limit": 1},
            headers={"User-Agent": "IMA-Maharashtra-App/1.0 (contact@example.org)"},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        # Geocoding is best-effort: if it fails, the profile still saves,
        # it just won't be reachable by SOS radius search until it succeeds.
        return None
