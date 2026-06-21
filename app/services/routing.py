import requests
from urllib.parse import urlencode

from shapely.geometry import Point, Polygon
from sqlmodel import Session, select

from app.config import settings
from app.schemas import Location, Barangay
from app.services.database import db_engine


def _validate_location(location: Location) -> Location:
    if not isinstance(location, Location):
        raise ValueError("Invalid location payload")
    if location.latitude is None or location.longitude is None:
        raise ValueError("Location latitude and longitude are required")
    return location


def _load_barangay_polygons() -> list[Polygon]:
    with Session(db_engine) as session:
        barangays = session.exec(select(Barangay)).all()

    polygons: list[Polygon] = []
    for barangay in barangays:
        if not barangay.bounds_coords or len(barangay.bounds_coords) < 3:
            continue
        polygon_coords = [(long, lat) for lat, long in barangay.bounds_coords]
        polygons.append(Polygon(polygon_coords))
    return polygons


def _location_is_within_any_barangay(location: Location, polygons: list[Polygon]) -> bool:
    report_point = Point(location.longitude, location.latitude)
    return any(polygon.covers(report_point) for polygon in polygons)


def _validate_report_locations_in_barangays(report_locations: list[Location]) -> None:
    if not isinstance(report_locations, list):
        raise ValueError("report_locations must be a list")

    polygons = _load_barangay_polygons()
    if not polygons:
        raise ValueError("No barangay boundaries are available for validation")

    invalid_locations: list[str] = []
    for index, location in enumerate(report_locations):
        _validate_location(location)
        if not _location_is_within_any_barangay(location, polygons):
            invalid_locations.append(
                f"index {index} (latitude={location.latitude}, longitude={location.longitude})"
            )

    if invalid_locations:
        raise ValueError(
            "Report locations must each fall within a barangay boundary. "
            "Invalid locations: " + ", ".join(invalid_locations)
        )


def _location_to_osrm_coordinate(location: Location) -> str:
    location = _validate_location(location)
    return f"{float(location.longitude)},{float(location.latitude)}"


def _build_osrm_trip_url(start: Location, end: Location, report_locations: list[Location]) -> str:
    coordinates = [_location_to_osrm_coordinate(start)]
    coordinates.extend(_location_to_osrm_coordinate(location) for location in report_locations)
    coordinates.append(_location_to_osrm_coordinate(end))

    params = {
        "source": "first",
        "destination": "last",
        "roundtrip": "false",
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
        "annotations": "false",
    }

    base_url = settings.OSRM_BASE_URL.rstrip("/")
    coordinate_string = ";".join(coordinates)
    return f"{base_url}/trip/v1/driving/{coordinate_string}?{urlencode(params)}"


def _parse_osrm_trip_response(response_json: dict) -> list[tuple[float, float]]:
    if response_json.get("code") != "Ok":
        raise ValueError(f"OSRM trip API error: {response_json.get('message', 'unknown error')}")

    trips = response_json.get("trips")
    if not trips:
        raise ValueError("OSRM trip API returned no trips")

    geometry = trips[0].get("geometry")
    if not geometry or geometry.get("type") != "LineString":
        raise ValueError("OSRM trip API returned an invalid geometry")

    coordinates = geometry.get("coordinates", [])
    return [(float(lat), float(lon)) for lon, lat in coordinates]


def generate_unapproved_route_waypoints(start: Location, end: Location, report_locations: list[Location]) -> list[tuple[float, float]]:
    _validate_report_locations_in_barangays(report_locations)
    if len(report_locations) > 24:
        raise ValueError("OSRM trip request supports at most 24 report locations")

    url = _build_osrm_trip_url(start, end, report_locations)
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        raise ValueError(f"OSRM trip request failed with status {response.status_code}: {response.text}")

    return _parse_osrm_trip_response(response.json())
