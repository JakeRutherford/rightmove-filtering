import os
import requests
from requests.structures import CaseInsensitiveDict
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point
from dotenv import load_dotenv
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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

    def process_address(self, address):
        # Regex pattern for a full UK postcode
        postcode_pattern = r"\b([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z]))))\s?[0-9][A-Za-z]{2})\b"

        # Search for the postcode in the address
        match = re.search(postcode_pattern, address)
        if match:
            # Full postcode found, return the address as is
            return address
        else:
            # Remove partial postcode (if any) from the address
            cleaned_address = re.sub(r"\b[A-Za-z]{1,2}[0-9]{1,2}\b", "", address).strip()
            return cleaned_address

    def is_within_isochrone(self, address):
        if not self.isochrone_map:
            raise ValueError("Isochrone map not created. Call create_isochrone_map first.")

        address = self.process_address(address)

        location = self.geolocator.geocode(address)
        if not location:
            logging.info(f"Unable to geocode address: {address}")
            return "unknown"

        point = Point(location.longitude, location.latitude)
        return self.isochrone_map.contains(point)
