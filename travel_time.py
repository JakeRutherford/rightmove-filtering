import os
import requests
from requests.structures import CaseInsensitiveDict
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point
from dotenv import load_dotenv


class IsochroneMapAnalyser:
    def __init__(self, user_agent="rightmove-filtering"):
        load_dotenv()
        self.geolocator = Nominatim(user_agent=user_agent)
        self.api_key = os.getenv("GEOAPIFY_ISOLINE_KEY")
        self.isochrone_map = None

    def create_isochrone_map(self, address, travel_time, mode="approximated_transit"):
        location = self.geolocator.geocode(address)
        if not location:
            raise ValueError(f"Unable to geocode address: {address}")

        lat, lon = location.latitude, location.longitude

        url = f"https://api.geoapify.com/v1/isoline?lat={lat}&lon={lon}&type=time&mode={mode}&range={travel_time}&apiKey={self.api_key}"

        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch isochrone map: {response.text}")

        self.isochrone_map = shape(response.json()["features"][0]["geometry"])

    def is_within_isochrone(self, address):
        if not self.isochrone_map:
            raise ValueError("Isochrone map not created. Call create_isochrone_map first.")

        location = self.geolocator.geocode(address)
        if not location:
            raise ValueError(f"Unable to geocode address: {address}")

        point = Point(location.longitude, location.latitude)
        return self.isochrone_map.contains(point)


# Example usage
try:
    analyzer = IsochroneMapAnalyzer()
    analyzer.create_isochrone_map("Holborn, London", 1800)  # 30 minutes
    is_within = analyzer.is_within_isochrone("Stratford, E15 1DS")
    print(f"Is Stratford within 30 minutes of Holborn? {is_within}")
except Exception as e:
    print(f"Error: {e}")
