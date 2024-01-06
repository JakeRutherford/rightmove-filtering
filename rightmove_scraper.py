from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains


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

    def perform_search(self):
        # Go to Rightmove website
        self.driver.get("https://www.rightmove.co.uk")
        # Wait for the cookie popup to be present and then locate the 'Accept all' button
        accept_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Accept all"]')))

        # Click the 'Accept all' button
        accept_button.click()

        # Wait until the search input is present
        search_input = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input.ksc_inputText.ksc_typeAheadInputField"))
        )

        # Clear the search box before entering text
        search_input.clear()
        search_input.send_keys(self.location)

        # Wait for the autocomplete suggestions to appear and use the down arrow key to select the first suggestion
        search_input.send_keys(Keys.DOWN)

        # Use the ENTER key to select the top suggestion from the dropdown
        search_input.send_keys(Keys.ENTER)

        # Wait for the "To Rent" button that contains the text "To Rent" to be clickable
        to_rent_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "To Rent")]')))
        to_rent_button.click()

        # Select the minimum price
        min_price_select = self.wait.until(EC.presence_of_element_located((By.ID, "minPrice")))
        Select(min_price_select).select_by_value(self.min_price)

        # Select the maximum price
        max_price_select = self.wait.until(EC.presence_of_element_located((By.ID, "maxPrice")))
        Select(max_price_select).select_by_value(self.max_price)

        # Select the minimum number of bedrooms
        min_bedrooms_select = self.wait.until(EC.presence_of_element_located((By.ID, "minBedrooms")))
        Select(min_bedrooms_select).select_by_value(self.min_bedrooms)

        # Select the maximum number of bedrooms
        max_bedrooms_select = self.wait.until(EC.presence_of_element_located((By.ID, "maxBedrooms")))
        Select(max_bedrooms_select).select_by_value(self.max_bedrooms)

        # Select the property type
        property_type_select = self.wait.until(EC.presence_of_element_located((By.ID, "displayPropertyType")))
        Select(property_type_select).select_by_visible_text(self.property_type)

        # Wait for the "Find properties" button to be clickable
        find_properties_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Find properties")]'))
        )
        find_properties_button.click()

    def get_property_urls(self):
        # Initialize an empty list to store the URLs
        property_urls = []

        # Start processing pages
        while True:
            # Wait for the properties to be loaded on the page
            properties = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.l-searchResult[data-test*="propertyCard"]'))
            )

            # Iterate over the properties
            for property in properties:
                try:
                    # Check if the property has bathrooms by looking for the bathroom icon
                    bathroom_icon = property.find_element(By.CSS_SELECTOR, "span.no-svg-bathroom-icon + span.text")
                    num_bathrooms = int(bathroom_icon.get_attribute("textContent"))

                    # Check if the property card mentions a floorplan
                    floorplan_element = property.find_element(By.CSS_SELECTOR, 'a[data-test="property-floorplan-icon"]')

                    # If the property has enough bathrooms and a floorplan, get the URL and add to the list
                    if num_bathrooms >= self.min_bathrooms and floorplan_element:
                        property_url_element = property.find_element(By.CSS_SELECTOR, "a.propertyCard-link")
                        property_url = property_url_element.get_attribute("href")
                        property_urls.append(property_url)
                except NoSuchElementException:
                    # If the bathroom element or floorplan is not found, skip this property
                    continue

            # Check if the "Next" button is disabled
            next_button = self.driver.find_element(By.CSS_SELECTOR, "button.pagination-direction--next")
            if next_button.get_attribute("disabled"):
                # If the button is disabled, we are on the last page
                break
            else:
                # If the button is not disabled, click it to go to the next page
                ActionChains(self.driver).move_to_element(next_button).click().perform()

        return property_urls

    def close(self):
        self.driver.quit()
