import math
import requests

# Built-in coordinates for every district/major city in Maharashtra, since
# IMA MS is a Maharashtra-only association. This is the PRIMARY geocoding
# method now - it needs no network call at all, so there's nothing for any
# external service to rate-limit or block (which is exactly what happened
# with the free Nominatim API - Render's shared IP range gets a blanket
# 403 from them, unrelated to anything in this code). City-level accuracy
# is genuinely sufficient for a 10km SOS radius check between clinics.
# Add more entries here any time as you register doctors in new areas.
MAHARASHTRA_CITY_COORDS = {
    "mumbai": (19.0760, 72.8777), "greater mumbai": (19.0760, 72.8777),
    "thane": (19.2183, 72.9781), "navi mumbai": (19.0330, 73.0297),
    "pune": (18.5204, 73.8567), "pimpri-chinchwad": (18.6298, 73.7997),
    "nagpur": (21.1458, 79.0882), "nashik": (19.9975, 73.7898),
    "chhatrapati sambhajinagar": (19.8762, 75.3433), "aurangabad": (19.8762, 75.3433),
    "solapur": (17.6599, 75.9064), "kolhapur": (16.7050, 74.2433),
    "amravati": (20.9374, 77.7796), "nanded": (19.1383, 77.3210),
    "sangli": (16.8524, 74.5815), "akola": (20.7002, 77.0082),
    "latur": (18.4088, 76.5604), "dhule": (20.9042, 74.7749),
    "ahmednagar": (19.0948, 74.7480), "ahilyanagar": (19.0948, 74.7480),
    "chandrapur": (19.9615, 79.2961), "parbhani": (19.2704, 76.7600),
    "jalgaon": (21.0077, 75.5626), "bhiwandi": (19.3002, 73.0635),
    "ichalkaranji": (16.6910, 74.4600), "malegaon": (20.5579, 74.5089),
    "vasai-virar": (19.4912, 72.8054), "vasai": (19.4912, 72.8054), "virar": (19.4559, 72.8107),
    "ulhasnagar": (19.2215, 73.1645), "panvel": (18.9894, 73.1175),
    "jalna": (19.8410, 75.8864), "satara": (17.6805, 74.0183),
    "beed": (18.9891, 75.7601), "yavatmal": (20.3888, 78.1204),
    "kamptee": (21.2265, 79.1927), "gondia": (21.4602, 80.1922),
    "wardha": (20.7453, 78.6022), "osmanabad": (18.1860, 76.0419),
    "dharashiv": (18.1860, 76.0419), "buldhana": (20.5293, 76.1804),
    "washim": (20.1113, 77.1330), "hingoli": (19.7147, 77.1494),
    "gadchiroli": (20.1809, 80.0026), "raigad": (18.5158, 73.1822),
    "alibaug": (18.6414, 72.8722), "ratnagiri": (16.9902, 73.3120),
    "sindhudurg": (16.1667, 73.6500), "palghar": (19.6969, 72.7699),
    "nandurbar": (21.3667, 74.2500), "sangamner": (19.5678, 74.2100),
    "baramati": (18.1514, 74.5815), "karad": (17.2913, 74.1858),
    "miraj": (16.8300, 74.6400), "wai": (17.9500, 73.8900),
    "lonavala": (18.7500, 73.4067), "khopoli": (18.7833, 73.3400),
    "pandharpur": (17.6792, 75.3317),
}


def geocode_from_city_lookup(city: str | None, state: str | None):
    """Primary geocoding path: match the doctor's city against the built-in
    Maharashtra table above. Zero network calls, so nothing to be blocked."""
    if not city:
        return None
    key = city.strip().lower()
    if key in MAHARASHTRA_CITY_COORDS:
        return MAHARASHTRA_CITY_COORDS[key]
    # Loose match: city text sometimes includes extra words (e.g. "Mumbai Suburban")
    for name, coords in MAHARASHTRA_CITY_COORDS.items():
        if name in key or key in name:
            return coords
    return None


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