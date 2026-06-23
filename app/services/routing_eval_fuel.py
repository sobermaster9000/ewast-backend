from bs4 import BeautifulSoup
import requests

from pyproj import Geod

from sqlmodel import Session

from app.schemas import Route
from app.services.database import db_engine

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

def get_est_route_efficiency(route_id: int) -> dict[str, float]:
    fuel_price_L = _get_diesel_price()
    with Session(db_engine) as session:
        route = session.get(Route, route_id)
        if not route:
            raise Exception(f"Route with ID {route_id} not found")
        route_dist_km = _get_route_distance(route.waypoints)
        avg_L_km = (1.26 + 1.8) / 2 # some legit numbers 💯
        return {
            "total_distance_km": route_dist_km,
            "est_total_liters": avg_L_km * route_dist_km,
            "est_cost_per_km_php": avg_L_km * fuel_price_L,
            "est_fuel_cost_php": avg_L_km * route_dist_km * fuel_price_L
        }