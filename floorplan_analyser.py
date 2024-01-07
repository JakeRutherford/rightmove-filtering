import requests
from PIL import Image
import pytesseract
from transformers import pipeline
import requests
import json
from bs4 import BeautifulSoup
import re


class FloorplanAnalyser:
    def __init__(self, model="deepset/deberta-v3-large-squad2"):
        self.model = pipeline("question-answering", model=model)

    def download_image(self, image_url, filename):
        try:
            # Send a GET request to the image URL
            response = requests.get(image_url)

            # Check if the request was successful
            response.raise_for_status()

            # Write the image content to a file
            with open(filename, "wb") as file:
                file.write(response.content)

            # print(f"Image downloaded and saved as {filename}")
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")

    def get_floorplan_url(self, property_url):
        # Split the URL on '#'
        parts = property_url.split("#")
        # Insert the floorplan segment before the '?channel=RES_LET' part
        floorplan_url = parts[0] + "#/floorplan" + ("?" + parts[1] if len(parts) > 1 else "")
        return floorplan_url

    def download_property_floorplan(self, property_url, image_path):
        floorplan_url = self.get_floorplan_url(property_url)

        headers = requests.utils.default_headers()

        headers.update(
            {
                "User-Agent": "My User Agent 1.0",
            }
        )

        response = requests.get(floorplan_url, headers=headers)

        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the script tag containing the PAGE_MODEL
        script_tag = soup.find("script", string=lambda t: t and "window.PAGE_MODEL" in t)

        # Extract the JSON string from the script tag
        json_string = script_tag.string.split("=", 1)[1].strip()

        # Remove the trailing semicolon if it exists
        json_string = json_string.rstrip(";")

        # Parse the JSON string
        data = json.loads(json_string)

        # Extract the floorplan image URL
        floorplan_image_url = data["propertyData"]["floorplans"][0]["url"]

        self.download_image(floorplan_image_url, image_path)

    def transcribe_image(self, image_path):
        # Open the image with Pillow
        image = Image.open(image_path)

        # Use Tesseract to do OCR on the image
        return pytesseract.image_to_string(image).strip()

    def get_answer(self, question, context):
        answer = self.model(question=question, context=context)["answer"].strip()
        # print(answer)
        # Regular expression to match both integers and floats
        matches = re.findall(r"\d+\.\d+|\d+", answer)

        # Convert the matches to floats or ints and return the first match
        return float(matches[0]) if matches else 0.0
