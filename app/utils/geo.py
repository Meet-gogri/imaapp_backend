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
            timeout=8,
        )
        print(f"[geocode_pincode] pincode={pincode} status={response.status_code} body={response.text[:200]}")
        response.raise_for_status()
        results = response.json()
        if not results:
            print(f"[geocode_pincode] pincode={pincode} - no results returned")
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        print(f"[geocode_pincode] FAILED for pincode={pincode}: {exc}")
        return None


def geocode_city_state(city: str, state: str, country: str = "India"):
    """Fallback for when a raw pincode search fails - Nominatim's coverage of
    Indian postal codes specifically is patchy, but city/state place-name
    lookups are much more reliable. Same free/keyless service."""
    if not city and not state:
        return None
    query = ", ".join(part for part in [city, state, country] if part)
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "IMA-Maharashtra-App/1.0 (contact@example.org)"},
            timeout=8,
        )
        print(f"[geocode_city_state] query={query} status={response.status_code} body={response.text[:200]}")
        response.raise_for_status()
        results = response.json()
        if not results:
            print(f"[geocode_city_state] query={query} - no results returned")
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        print(f"[geocode_city_state] FAILED for query={query}: {exc}")
        return None