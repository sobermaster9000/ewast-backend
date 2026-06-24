import requests

from shapely.geometry import Point, LineString
from shapely.ops import transform as shapely_transform

from sqlmodel import Session, select

from app.services.database import db_engine
from app.schemas import Report, Route


def compute_collection_rates_for_barangay(barangay_id: int, radius_meters: float = 10.0) -> list[tuple[int, float, int]]:
    """
    For each route under the specified barangay, compute how many reports fall within
    `radius_meters` of the route. Persist `collection_rate` on each route record.

    Returns a list of tuples: (route_id, collection_rate_percent, collected_count)
    """

    with Session(db_engine) as session:
        reports = session.exec(select(Report).where(Report.under_barangay_id == barangay_id)).all()
        total_reports = len(reports)

        routes = session.exec(select(Route).where(Route.for_barangay_id == barangay_id)).all()

        results: list[tuple[int, float, int]] = []

        # prepare projected report points
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        def _proj(x, y, z=None):
            return transformer.transform(x, y)

        projected_report_points = []
        for report in reports:
            # Report stores lat/long on fields `latitude`, `longitude`
            pt = Point(report.longitude, report.latitude)
            projected = shapely_transform(pt, _proj)
            projected_report_points.append((report, projected))

        for route in routes:
            # route.waypoints stored as list of (lat, lon) tuples; convert to (lon, lat)
            if not route.waypoints:
                route.collection_rate = 0.0
                session.add(route)
                session.commit()
                results.append((route.route_id, 0.0, 0))
                continue

            coords_lonlat = [(float(lon), float(lat)) for lat, lon in route.waypoints]
            line = LineString(coords_lonlat)
            projected_line = shapely_transform(line, _proj)

            collected = 0
            for report, proj_pt in projected_report_points:
                dist = proj_pt.distance(projected_line)
                if dist <= float(radius_meters):
                    collected += 1

            collection_rate = 0.0
            if total_reports > 0:
                collection_rate = (collected / total_reports) * 100.0

            route.collection_rate = round(collection_rate, 2)
            session.add(route)
            session.commit()

            results.append((route.route_id, route.collection_rate, collected))

        return results