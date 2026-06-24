from bs4 import BeautifulSoup
import requests

from pyproj import Geod

from sqlmodel import Session, select

from app.schemas import Route
from app.services.database import db_engine

AVG_L_KM = (1.26 + 1.8) / 2 # some legit numbers 💯

def _get_diesel_price() -> float:
    page_to_scrape = requests.get("https://tipidgas.ph/city/davao-city/")
    soup = BeautifulSoup(page_to_scrape.text, "html.parser")
    main_prices = soup.find_all("div", attrs={"class": "fuel-card"})

    diesel_price = 0

    for price in main_prices:
        if "Diesel" not in price.text:
            continue
        diesel_price_text = [x for x in price.text.split() if "Average" in x][0]
        diesel_price = float(diesel_price_text.replace("Average", "").replace("Range", "")[1:])
        break

    return diesel_price

def _get_route_distance(waypoints: list[tuple[float, float]]) -> float:
    geod = Geod(ellps="WGS84")
    distance_m = 0
    for i in range(1, len(waypoints)):
        lat1, lon1 = waypoints[i]
        lat2, lon2 = waypoints[i-1]
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        distance_m += dist
    distance_km = distance_m / 1000.0
    return distance_km

def get_estimated_route_efficiency(route_id: int) -> dict[str, float]:
    fuel_price_L = _get_diesel_price()
    with Session(db_engine) as session:
        route = session.get(Route, route_id)
        if not route:
            raise Exception(f"Route with ID {route_id} not found")
        route_dist_km = _get_route_distance(route.waypoints)
        return {
            "total_distance_km": route_dist_km,
            "total_liters": AVG_L_KM * route_dist_km,
            "cost_per_km_php": AVG_L_KM * fuel_price_L,
            "fuel_cost_php": AVG_L_KM * route_dist_km * fuel_price_L
        }

def get_estimated_routes_efficiency_for_barangay(barangay_id: int) -> dict[str, float]:
    fuel_price_L = _get_diesel_price()
    result = {
        "total_distance_km": 0.0,
        "total_liters": 0.0,
        "cost_per_km_php": 0.0,
        "fuel_cost_php": 0.0
    }
    with Session(db_engine) as session:
        routes = session.exec(select(Route).where(Route.for_barangay_id == barangay_id)).all()
        for route in routes:
            route_result = get_estimated_route_efficiency(route.route_id)
            result["total_distance"] += route_result["total_distance"]
    result["total_liters"] = AVG_L_KM * result["total_distance_km"]
    result["cost_per_km_php"] = AVG_L_KM * fuel_price_L
    result["fuel_cost_php"] = AVG_L_KM * result["total_distance_km"] * fuel_price_L
    return result