# Better Rightmove Filtering
## Overview
Rightmove does not let you filter properties by number of bathrooms, floor area or commute time. This is annoying. Hence, this project automates scraping property data from Rightmove, while allowing you to set number of bedrooms, bathrooms, minimum floor area and a maximum commute time to a given destination (e.g. your office).

## Contents
* main.py: Main script integrating scraping, floor plan analysis, and travel time calculations.
* rightmove_scraper.py: Scrapes property data from Rightmove. This performs an initial search, using the basic filters of bedrooms, bathrooms and whether a floor plan is available.
* floorplan_analyser.py: Analyzes floor plans using OCR and question-answering models.
* travel_time.py: Calculates travel times and isochrones for properties.
* open_links.sh: Bash script to open property URLs from a CSV file in batches. After main.py terminates, it will output a properties.csv file. By running `./open_links.sh`, it will open property URLs in batches.

## Installation
* Disclaimer: Rightmove's terms of use does not allow scraping, so do not do the following:
* Make sure you have Tesseract installed:
    * MacOS: `brew install tesseract`
    * Linux: `sudo apt update`, `sudo apt install tesseract-ocr`
* Clone the repository to your local machine.
* Make a Python 3.10 environment: `python3.10 -m venv venv`, then activate it.
* Install required Python libraries: `python3 -m pip install -r requirements.txt`
* Run main.py to start the process: `python3 main.py`