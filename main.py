import logging
from rightmove_scraper import RightmoveScraper
from floorplan_analyser import FloorplanAnalyser
from travel_time import IsochroneMapAnalyser
import pandas as pd
import os
import yaml
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_config(config_file):
    with open(config_file, "r") as file:
        return yaml.safe_load(file)


def main():
    config = load_config("config.yaml")

    # Create 'images' directory if it doesn't exist
    if not os.path.exists(config["images_directory"]):
        os.makedirs(config["images_directory"])

    # Initialize floorplan analyser
    floorplan_analyser = FloorplanAnalyser()

    # Initialize travel time analyser only if target location is provided
    travel_analyser = None
    if "target_location" in config and config["target_location"]:
        logging.info("Using travel time analysis.")
        travel_analyser = IsochroneMapAnalyser()
        travel_analyser.create_isochrone_map(config["target_location"], config["travel_time_radius"])
    else:
        logging.info("No target location provided. Not using travel time analysis.")

    final_properties = []

    for borough in config["london_boroughs"]:
        logging.info(f"Processing borough: {borough}")
        try:
            # Initialize the scraper
            scraper = RightmoveScraper(
                location=borough,
                min_price=config["scraper_settings"]["min_price"],
                max_price=config["scraper_settings"]["max_price"],
                min_bedrooms=config["scraper_settings"]["min_bedrooms"],
                max_bedrooms=config["scraper_settings"]["max_bedrooms"],
                min_bathrooms=config["scraper_settings"]["min_bathrooms"],
                property_type=config["scraper_settings"]["property_type"],
                min_let_date=config["scraper_settings"]["min_let_date"],
            )

            # Perform the search and get property URLs
            scraper.perform_search()
            property_details = scraper.get_property_details()
            # scraper.close()
        except Exception as e:
            logging.error(f"Error processing {borough}: {e}")
            continue

        logging.info(f"Found {len(property_details)} potential properties. Performing additional filtering.")

        for property_detail in tqdm(property_details):
            # Perform travel time analysis if analyser is initialized
            within_travel_time = True
            if travel_analyser:
                within_travel_time = travel_analyser.is_within_isochrone(property_detail["address"])

            if not within_travel_time:
                continue

            property_number = property_detail["url"].split("/properties/")[1].split("/")[0].strip("#")
            floorplan_image_path = os.path.join("images", f"{property_number}.jpeg")

            # Check if the image already exists
            if not os.path.exists(floorplan_image_path):
                floorplan_analyser.download_property_floorplan(property_detail["url"], floorplan_image_path)

            area = floorplan_analyser.get_answer(config["qa_prompt"], floorplan_image_path)

            if area < config["floorplan_area_threshold"]:
                continue

            if not scraper.meets_criteria(property_detail["url"]):
                continue

            property_detail.update({"area": area, "within_travel_time": within_travel_time})

            final_properties.append(property_detail)

        logging.info(f"Properties found so far: {len(final_properties)}")
        scraper.close()

    logging.info(f"Total properties found: {len(final_properties)}")

    if len(final_properties) > 0:
        # Create a DataFrame and save to CSV
        df = pd.DataFrame(final_properties)
        df.sort_values(by=["price_pcm", "area"], ascending=[True, False], inplace=True)
        df.drop_duplicates(subset=["url"], inplace=True)
        df.to_csv("properties.csv", index=False)
    else:
        logging.info("No properties found.")


if __name__ == "__main__":
    main()
