import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RightmoveScraper:
    def __init__(self, location, min_price, max_price, min_bedrooms, max_bedrooms, min_bathrooms, property_type):
        self.location = location
        self.min_price = min_price
        self.max_price = max_price
        self.min_bedrooms = min_bedrooms
        self.max_bedrooms = max_bedrooms
        self.min_bathrooms = min_bathrooms
        self.property_type = property_type
        self.driver = self._init_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def _init_driver(self):
        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def accept_cookies(self):
        # Wait for the cookie popup to be present and then locate the 'Accept all' button
        wait = WebDriverWait(self.driver, 10)
        accept_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Accept all"]')))

        # Click the 'Accept all' button
        accept_button.click()

    def get_location_identifier(self):
        # Perform initial search to get the location identifier
        self.driver.get("https://www.rightmove.co.uk")

        self.accept_cookies()

        search_input = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input.ksc_inputText.ksc_typeAheadInputField"))
        )
        search_input.clear()
        search_input.send_keys(self.location)
        search_input.send_keys(Keys.DOWN)
        search_input.send_keys(Keys.ENTER)
        to_rent_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "To Rent")]')))
        to_rent_button.click()
        current_url = self.driver.current_url

        # Extract location identifier from URL
        location_identifier_match = re.search(r"locationIdentifier=([^&]+)", current_url)
        return location_identifier_match.group(1) if location_identifier_match else None

    def construct_search_url(self):
        location_identifier = self.get_location_identifier()
        if location_identifier:
            search_url = f"https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier={location_identifier}&maxBedrooms={self.max_bedrooms}&minBedrooms={self.min_bedrooms}&maxPrice={self.max_price}&minPrice={self.min_price}&propertyTypes={self.property_type}&includeLetAgreed=false&mustHave=&dontShow=houseShare%2Cretirement%2Cstudent&furnishTypes=&keywords="
            logging.info(f"Constructed search URL: {search_url}")
            return search_url
        logging.warning("Failed to construct search URL. Check location identifier.")
        return None

    def perform_search(self):
        search_url = self.construct_search_url()
        if search_url:
            self.driver.get(search_url)
        else:
            logging.error("Search URL is not available.")

    def get_property_details(self):
        # Initialize an empty list to store property details
        property_details = []

        # Start processing pages
        page_number = 1
        while True:
            logging.info(f"Processing page number: {page_number}")
            # Wait for the properties to be loaded on the page
            properties = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.l-searchResult[data-test*="propertyCard"]'))
            )

            # Iterate over the properties
            for property in properties:
                try:
                    # Check if the property has enough bathrooms
                    bathroom_icon = property.find_element(By.CSS_SELECTOR, "span.no-svg-bathroom-icon + span.text")
                    num_bathrooms = int(bathroom_icon.get_attribute("textContent"))

                    # Check if the property card mentions a floorplan
                    floorplan_element = property.find_element(By.CSS_SELECTOR, 'a[data-test="property-floorplan-icon"]')

                    # Process only if the property has enough bathrooms and a floorplan
                    if num_bathrooms >= self.min_bathrooms and floorplan_element:
                        # Extract property URL
                        property_url_element = property.find_element(By.CSS_SELECTOR, "a.propertyCard-link")
                        property_url = property_url_element.get_attribute("href")

                        # Extract price
                        price_element = property.find_element(By.CSS_SELECTOR, "span.propertyCard-priceValue")
                        price_pcm = price_element.text

                        # Extract number of bedrooms
                        bedrooms_element = property.find_element(By.CSS_SELECTOR, "span.no-svg-bed-icon + span.text")
                        bedrooms = bedrooms_element.get_attribute("textContent").strip()

                        # Extract address
                        address_element = property.find_element(By.CSS_SELECTOR, "address.propertyCard-address")
                        address = address_element.text

                        # Append the details to the list
                        property_details.append(
                            {
                                "url": property_url,
                                "price_pcm": price_pcm,
                                "bedrooms": bedrooms,
                                "bathrooms": str(num_bathrooms),
                                "address": address,
                            }
                        )

                except NoSuchElementException:
                    # If an element is not found, skip this property
                    continue

            # Check if the "Next" button is disabled
            next_button = self.driver.find_element(By.CSS_SELECTOR, "button.pagination-direction--next")
            if next_button.get_attribute("disabled"):
                # If the button is disabled, we are on the last page
                logging.info(f"Reached final page.")
                break
            else:
                # If the button is not disabled, click it to go to the next page
                page_number += 1
                ActionChains(self.driver).move_to_element(next_button).click().perform()

        return property_details

    def close(self):
        self.driver.quit()
