import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from utils import word_ngrams
import re
import datetime
from typing import List, Dict

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RightmoveScraper:
    def __init__(
        self,
        location: str,
        min_price: int,
        max_price: int,
        min_bedrooms: int,
        max_bedrooms: int,
        min_bathrooms: int,
        property_type: str,
        min_let_date: str,
        floorplan_required: bool,
        max_days_since_added: str,
        exclude: list[str],
    ) -> None:
        """
        Initialize the RightmoveScraper with search criteria for property listings.

        Args:
        location (str): The location for the property search.
        min_price (int): Minimum price for the property search.
        max_price (int): Maximum price for the property search.
        min_bedrooms (int): Minimum number of bedrooms required.
        max_bedrooms (int): Maximum number of bedrooms required.
        min_bathrooms (int): Minimum number of bathrooms required.
        property_type (str): Type of property (e.g., 'flat', 'house').
        min_let_date (str): Let available date.
        floorplan_required (bool): Is a floorplan required?
        max_days_since_added (str): Number of days since property added to site. Valid vaues are "Anytime", 1, 3, 7 and 14.
        exclude (list): Filter out properties based on these keywords.
        """
        self.location = location
        self.min_price = min_price
        self.max_price = max_price
        self.min_bedrooms = min_bedrooms
        self.max_bedrooms = max_bedrooms
        self.min_bathrooms = min_bathrooms
        self.property_type = property_type
        self.min_let_date = (
            datetime.datetime.strptime(min_let_date, "%d/%m/%Y") if min_let_date != "Now" else datetime.datetime.now()
        )
        self.floorplan_required = floorplan_required
        self.max_days_since_added = max_days_since_added
        self.exclude = exclude
        self.longest_exclude = max([len(x.split()) for x in exclude])
        self.driver = self._init_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def _init_driver(self) -> webdriver.Chrome:
        """
        Initializes and returns a Chrome WebDriver.

        Returns:
        WebDriver: An instance of Chrome WebDriver.
        """
        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def accept_cookies(self) -> None:
        """
        Accepts cookies on the Rightmove website by clicking the 'Accept all' button.
        """
        # Wait for the cookie popup to be present and then locate the 'Accept all' button
        wait = WebDriverWait(self.driver, 10)
        accept_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Accept all"]')))

        # Click the 'Accept all' button
        accept_button.click()

    def get_location_identifier(self) -> str:
        """
        Retrieves the location identifier from Rightmove based on the search location.

        Returns:
        str: The location identifier if found.
        """
        # Perform initial search to get the location identifier
        self.driver.get("https://www.rightmove.co.uk")

        self.accept_cookies()

        search_input = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input.ksc_inputText.ksc_typeAheadInputField"))
        )
        search_input.clear()
        search_input.send_keys(self.location)
        # Wait for the suggestions to appear and click the first button within the ul element
        first_suggestion_button = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "ul.ksc_resultsList > li:first-child > button"))
        )
        first_suggestion_button.click()
        to_rent_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "To Rent")]')))
        to_rent_button.click()
        current_url = self.driver.current_url

        # Extract location identifier from URL
        location_identifier_match = re.search(r"locationIdentifier=([^&]+)", current_url)
        return location_identifier_match.group(1) if location_identifier_match else ""

    def construct_search_url(self) -> str:
        """
        Constructs the search URL for the property listing based on the given criteria.

        Returns:
        str: The constructed search URL if possible.
        """
        location_identifier = self.get_location_identifier()
        if location_identifier:
            search_url = (
                f"https://www.rightmove.co.uk/property-to-rent/find.html?"
                f"locationIdentifier={location_identifier}&"
                f"maxBedrooms={self.max_bedrooms}&"
                f"minBedrooms={self.min_bedrooms}&"
                f"maxPrice={self.max_price}&"
                f"minPrice={self.min_price}&"
                f"propertyTypes={self.property_type}&"
                f"includeLetAgreed=false&"
                f"mustHave=&"
                f"dontShow=houseShare%2Cretirement%2Cstudent&"
                f"furnishTypes=&"
                f"keywords="
            )

            # Append maxDaysSinceAdded to the URL if it's a specific value
            if self.max_days_since_added in ["1", "3", "7", "14"]:
                search_url += f"&maxDaysSinceAdded={self.max_days_since_added}"

            logging.info(f"Constructed search URL: {search_url}")
            return search_url
        else:
            logging.warning("Failed to construct search URL. Check location identifier.")
            return ""

    def perform_search(self) -> None:
        """
        Navigates to the constructed search URL and initiates the property search.
        """
        search_url = self.construct_search_url()
        if search_url:
            self.driver.get(search_url)
        else:
            logging.error("Search URL is not available.")

    def keyword_filtering(self, text: str) -> bool:
        """
        Checks if the provided text contains any of the excluded keywords.
        """
        n_grams = word_ngrams(text, self.longest_exclude)
        if n_grams & set(self.exclude):
            return True
        else:
            return False

    def get_property_details(self) -> List[Dict[str, str]]:
        """
        Scrapes property details from the search results pages.

        Returns:
        List[Dict[str, str]]: A list of dictionaries, each containing details of a property.
        """
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
                    # Extract address
                    address_element = property.find_element(By.CSS_SELECTOR, "address.propertyCard-address")
                    address = address_element.text

                    # Filter out properties if their address contains an excluded keyword
                    if self.keyword_filtering(address):
                        logging.info(f"Filter out {address}")
                        continue

                    # Check if the property has enough bathrooms
                    bathroom_icon = property.find_element(By.CSS_SELECTOR, "span.no-svg-bathroom-icon + span.text")
                    num_bathrooms = int(bathroom_icon.get_attribute("textContent"))

                    try:
                        # Check if the property card mentions a floorplan
                        floorplan_element = property.find_element(By.CSS_SELECTOR, 'a[data-test="property-floorplan-icon"]')
                    except NoSuchElementException:
                        if self.floorplan_required:
                            continue
                        else:
                            floorplan_element = None

                    # Process only if the property has enough bathrooms
                    if num_bathrooms >= self.min_bathrooms:
                        # Extract property URL
                        property_url_element = property.find_element(By.CSS_SELECTOR, "a.propertyCard-link")
                        property_url = property_url_element.get_attribute("href")

                        # Extract price
                        price_element = property.find_element(By.CSS_SELECTOR, "span.propertyCard-priceValue")
                        price_pcm = price_element.text

                        # Extract number of bedrooms
                        bedrooms_element = property.find_element(By.CSS_SELECTOR, "span.no-svg-bed-icon + span.text")
                        bedrooms = bedrooms_element.get_attribute("textContent").strip()

                        # Append the details to the list
                        property_details.append(
                            {
                                "has_floorplan": True if floorplan_element else False,
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

    def get_property_letting_details(self, url: str) -> Dict[str, str]:
        """
        Extracts letting details from a property's page.

        Args:
        url (str): URL of the property's page.

        Returns:
        Dict[str, str]: Letting details including available date, furnish type, and let type.
        """
        self.driver.get(url)

        # Locate the article element containing "Letting details"
        article_element = self.wait.until(
            EC.presence_of_element_located((By.XPATH, '//article[.//h2[contains(text(), "Letting details")]]'))
        )

        # Extract the details
        details = {
            "let_available_date": self._extract_detail(article_element, "Let available date"),
        }
        return details

    def _extract_detail(self, parent_element, detail_name: str) -> str:
        """
        Extracts a specific detail from the parent element.

        Args:
        parent_element (WebElement): The parent element containing the details.
        detail_name (str): The name of the detail to extract.

        Returns:
        str: The extracted detail.
        """
        try:
            detail_element = parent_element.find_element(
                By.XPATH,
                f'.//dt[contains(text(), "{detail_name}")]/following-sibling::dd',
            )
            return detail_element.text.strip()
        except NoSuchElementException:
            return ""

    def meets_criteria(self, url: str) -> bool:
        """
        Checks if a property meets the specified criteria.

        Args:
        url (str): URL of the property's page.

        Returns:
        bool: True if the property meets the criteria, False otherwise.
        """
        details = self.get_property_letting_details(url)

        # Check let available date
        let_date_str = details["let_available_date"]
        if let_date_str != "Ask agent":
            try:
                let_date = datetime.datetime.strptime(let_date_str, "%d/%m/%Y")
                if let_date < self.min_let_date:
                    return False
            except ValueError:
                # Handle invalid date format
                return False

        return True

    def filter_properties(self, property_urls: List[str]) -> List[str]:
        """
        Filters properties based on criteria only on the property page.

        Args:
        property_urls (List[str]): List of property URLs to process.

        Returns:
        List[str]: URLs of properties that meet the criteria.
        """
        return [url for url in property_urls if self.meets_criteria(url)]

    def close(self) -> None:
        """
        Closes the WebDriver session.
        """
        self.driver.quit()
