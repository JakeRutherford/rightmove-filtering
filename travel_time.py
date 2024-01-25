import os
import requests
from requests.structures import CaseInsensitiveDict
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point
from dotenv import load_dotenv
import logging
from typing import Union

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class IsochroneMapAnalyser:
    def __init__(self, user_agent: str = "rightmove-filtering") -> None:
        """
        Initialize the IsochroneMapAnalyser with a specific user agent.

        Args:
        user_agent (str): A user agent string for Nominatim geocoding service.
        """
        load_dotenv()
        self.geolocator = Nominatim(user_agent=user_agent)
        self.api_key = os.getenv("GEOAPIFY_ISOLINE_KEY")
        self.isochrone_map = None

    def create_isochrone_map(self, address: str, travel_time: int, mode: str = "approximated_transit") -> None:
        """
        Creates an isochrone map based on the given address, travel time, and mode of transport.

        Args:
        address (str): The address to base the isochrone map on.
        travel_time (int): The travel time in seconds.
        mode (str): The mode of transport, default is 'approximated_transit'.

        Raises:
        ValueError: If the address cannot be geocoded.
        ConnectionError: If the API call is unsuccessful.
        """
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

    def is_within_isochrone(self, address: str) -> Union[bool, str]:
        """
        Checks if the given address is within the previously created isochrone map.

        Args:
        address (str): The address to check.

        Returns:
        bool or str: True if within the isochrone map, False if not, 'unknown' if address cannot be geocoded.

        Raises:
        ValueError: If the isochrone map is not yet created.
        """
        if not self.isochrone_map:
            raise ValueError("Isochrone map not created. Call create_isochrone_map first.")

        location = self.geolocator.geocode(address)
        if not location:
            logging.info(f"Unable to geocode address: {address}")
            return "unknown"

        point = Point(location.longitude, location.latitude)
        return self.isochrone_map.contains(point)
