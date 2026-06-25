import logging
import requests

logger = logging.getLogger(__name__)

def reverse_geocode(latitude: float, longitude: float) -> str | None:
    """
    Reverse geocode latitude and longitude coordinates using OpenStreetMap Nominatim API.
    Returns the formatted address string or None if it fails.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "accept-language": "en"
    }
    headers = {
        "User-Agent": "EWAST-Backend/1.0"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            display_name = data.get("display_name")
            if display_name:
                return display_name
        else:
            logger.warning(f"Nominatim geocoding API returned status code {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error reverse geocoding coordinates ({latitude}, {longitude}): {e}")
    return None
