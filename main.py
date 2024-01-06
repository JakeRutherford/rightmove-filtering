from rightmove_scraper import RightmoveScraper
from floorplan_analyser import FloorplanAnalyser
import pandas as pd
import os


def main():
    # Create 'images' directory if it doesn't exist
    images_dir = "images"
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    # Initialize the scraper
    scraper = RightmoveScraper("London", "3000", "3000", "3", "3", 2, "Flats / Apartments")

    # Perform the search and get property URLs
    scraper.perform_search()
    property_urls = scraper.get_property_urls()
    scraper.close()

    # Initialize floorplan analyzer and question answering
    analyser = FloorplanAnalyser()

    final_properties = []

    for property_url in property_urls:
        property_number = property_url.split("/properties/")[1].split("/")[0].strip("#")
        floorplan_image_path = os.path.join("images", f"{property_number}.jpeg")

        # Check if the image already exists
        if not os.path.exists(floorplan_image_path):
            print("Checking ", floorplan_image_path)
            analyser.download_property_floorplan(property_url, floorplan_image_path)

        text = analyser.transcribe_image(floorplan_image_path)
        if text:
            floor_space = analyser.get_answer("What is the total gross internal area in square feet (sq ft)?", text)
            if floor_space >= 780.0:
                final_properties.append((property_url, floor_space))

    # Create a DataFrame and save to CSV
    df = pd.DataFrame(final_properties)
    df.columns = ["Property URL", "Square Feet"]
    df.to_csv("properties.csv", index=False)


if __name__ == "__main__":
    main()
