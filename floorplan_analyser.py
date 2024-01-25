import requests
from transformers import pipeline
import json
from bs4 import BeautifulSoup
import re


class FloorplanAnalyser:
    def __init__(self, model: str = "impira/layoutlm-document-qa", task: str = "document-question-answering") -> None:
        """
        Initialize the FloorplanAnalyser with a specified model and task for document-question answering.

        Args:
        model (str): The model to use for the document-question answering pipeline.
        task (str): The task type for the pipeline.
        """
        self.model = pipeline(model=model, task=task)

    def download_image(self, image_url: str, filename: str) -> None:
        """
        Downloads an image from a given URL and saves it to a specified file.

        Args:
        image_url (str): URL of the image to download.
        filename (str): Filename to save the downloaded image.
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            with open(filename, "wb") as file:
                file.write(response.content)
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")

    def get_floorplan_url(self, property_url: str) -> str:
        """
        Constructs the floorplan URL from a given property URL.

        Args:
        property_url (str): The URL of the property.

        Returns:
        str: The modified URL pointing to the property's floorplan.
        """
        parts = property_url.split("#")
        floorplan_url = parts[0] + "#/floorplan" + ("?" + parts[1] if len(parts) > 1 else "")
        return floorplan_url

    def download_property_floorplan(self, property_url: str, image_path: str) -> None:
        """
        Downloads the floorplan image of a property from its URL.

        Args:
        property_url (str): The URL of the property.
        image_path (str): Path where the floorplan image will be saved.
        """
        floorplan_url = self.get_floorplan_url(property_url)
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "My User Agent 1.0"})

        response = requests.get(floorplan_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", string=lambda t: t and "window.PAGE_MODEL" in t)

        json_string = script_tag.string.split("=", 1)[1].strip()
        json_string = json_string.rstrip(";")

        data = json.loads(json_string)
        floorplan_image_url = data["propertyData"]["floorplans"][0]["url"]
        self.download_image(floorplan_image_url, image_path)

    def get_answer(self, question: str, image_path: str) -> float:
        """
        Retrieves an answer to a specified question based on the analysis of a floorplan image.

        Args:
        question (str): The question to be answered based on the floorplan image.
        image_path (str): The path to the floorplan image.

        Returns:
        float: The numerical answer extracted from the analysis, or 0.0 if no answer is found.
        """
        answer = self.model(image=image_path, question=question)
        if not answer:
            return 0.0

        answer = max(answer, key=lambda x: x["score"])["answer"].strip()
        matches = re.findall(r"\d+\.\d+|\d+", answer)
        return float(matches[0]) if matches else 0.0
