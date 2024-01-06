import logging
from rightmove_scraper import RightmoveScraper
from floorplan_analyser import FloorplanAnalyser
import pandas as pd
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    # Create 'images' directory if it doesn't exist
    images_dir = "images"
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    london_boroughs = [
        "Newham (London Borough)",
        "Tower Hamlets (London Borough)",
        "Hackney (London Borough)",
        "Southwark (London Borough)",
        "Lambeth (London Borough)",
        "Battersea, South West London",
        "Kensington And Chelsea (Royal Borough)",
        "Hammersmith And Fulham (London Borough)",
        "Richmond Upon Thames (London Borough)",
        "Islington (London Borough)",
        "Brent (London Borough)",
        "Haringey (London Borough)",
        "Merton (London Borough)",
    ]

    final_properties = []

    for borough in london_boroughs:
        logging.info(f"Processing borough: {borough}")
        try:
            # Initialize the scraper
            scraper = RightmoveScraper(borough, "2500", "2800", "2", "3", 2, "flat")

            # Perform the search and get property URLs
            scraper.perform_search()
            property_details = scraper.get_property_details()
            scraper.close()
        except Exception as e:
            logging.error(f"Error processing {borough}: {e}")
            continue

        # Initialize floorplan analyzer and question answering
        analyser = FloorplanAnalyser()

        for property_detail in property_details:
            property_number = property_detail["url"].split("/properties/")[1].split("/")[0].strip("#")
            floorplan_image_path = os.path.join("images", f"{property_number}.jpeg")

            # Check if the image already exists
            if not os.path.exists(floorplan_image_path):
                print("Checking ", floorplan_image_path)
                analyser.download_property_floorplan(property_detail["url"], floorplan_image_path)

            text = analyser.transcribe_image(floorplan_image_path)
            if text:
                area = analyser.get_answer("What is the total gross internal floor area in square feet (sq ft)?", text)
                property_detail.update({"area": area})
                if area >= 780.0:
                    final_properties.append(property_detail)

        logging.info(f"Properties found so far: {len(final_properties)}")

    logging.info(f"Total properties found: {len(final_properties)}")

    if len(final_properties) > 0:
        # Create a DataFrame and save to CSV
        df = pd.DataFrame(final_properties)
        df.sort_values(by=["price_pcm", "area"], ascending=[False, False], inplace=True)
        df.to_csv("properties.csv", index=False)
    else:
        logging.info("No properties found.")


if __name__ == "__main__":
    main()
