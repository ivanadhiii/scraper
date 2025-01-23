from playwright.sync_api import sync_playwright, TimeoutError
from dataclasses import dataclass, asdict, field
import pandas as pd
import os
import logging
import time
import re 

# Set up logging
logging.basicConfig(level=logging.INFO)

@dataclass
class Business:
    """Holds business data."""
    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: float = None
    longitude: float = None

@dataclass
class BusinessList:
    """Holds list of Business objects and saves to both Excel and CSV."""
    business_list: list[Business] = field(default_factory=list)
    save_at = 'output'

    def dataframe(self):
        """Transform business_list to pandas DataFrame."""
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """Saves pandas DataFrame to Excel (xlsx) file."""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"{self.save_at}/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """Saves pandas DataFrame to CSV file."""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"{self.save_at}/{filename}.csv", index=False)

def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """Extract coordinates from Google Maps URL."""
    try:
        # Use regex to extract latitude and longitude after !3d and !4d
        lat_lon_pattern = r'!3d([-+]?[0-9]*\.?[0-9]+)!4d([-+]?[0-9]*\.?[0-9]+)'
        match = re.search(lat_lon_pattern, url)

        if match:
            lat = float(match.group(1))  # Extract latitude
            lon = float(match.group(2))  # Extract longitude
            return lat, lon

        # If not found, check for coordinates after '@'
        at_pattern = r'@([-+]?[0-9]*\.?[0-9]+),([-+]?[0-9]*\.?[0-9]+)'
        at_match = re.search(at_pattern, url)

        if at_match:
            lat = float(at_match.group(1))  # Extract latitude
            lon = float(at_match.group(2))  # Extract longitude
            return lat, lon

        # If no coordinates found, return None
        logging.error("No coordinates found in the URL.")
        return None, None

    except Exception as e:
        logging.error(f"Error extracting coordinates: {e}")
        return None, None

def scrape_business_data(search_for: str, total: int) -> BusinessList:
    """Main scraping function."""
    business_list = BusinessList()

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.google.com/maps", timeout=3000)

             # Tunggu hingga tombol zoom out terskedia
        try:
            page.wait_for_selector('button[aria-label="Perkecil"]', timeout=2000)
            for _ in range(2):  # Klik tombol zoom out 3 kali
                page.evaluate("document.querySelector('button[aria-label=\"Perkecil\"]').click()")
                page.wait_for_timeout(1000)  # Tunggu sebentar setelah setiap klik
        except Exception as e:
            print(f"Error while trying to zoom out: {e}")

        # Search for businesses
        page.wait_for_selector('#searchboxinput', timeout=4000)
        page.locator('#searchboxinput').fill(search_for)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)

   

        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
        previously_counted = 0
        while True:
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(2000)

            if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() >= total:
                listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                print(f"Total Scraped: {len(listings)}")
                break
            else:
                if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() == previously_counted:
                    listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
                    print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                    break
                else:
                    previously_counted = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                    print(f"Currently Scraped: {previously_counted}")

        business_list = BusinessList()

            # Scrape data for each listing
        for listing in listings:
            try:
                business = Business()
                listing.click()
                page.wait_for_timeout(1500)  # Allow time for the pane to load

                name_attribute = 'aria-label'
                address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                review_count_xpath = '//button[@jsaction="pane.reviewChart.moreReviews"]//span'
                reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'
                
                business = Business()
               
                if len(listing.get_attribute(name_attribute)) >= 1:
                    business.name = listing.get_attribute(name_attribute)
                else:
                    business.name = ""
                if page.locator(address_xpath).count() > 0:
                    business.address = page.locator(address_xpath).all()[0].inner_text()
                else:
                    business.address = ""
                if page.locator(website_xpath).count() > 0:
                    business.website = page.locator(website_xpath).all()[0].inner_text()
                else:
                    business.website = ""
                if page.locator(phone_number_xpath).count() > 0:
                    business.phone_number = page.locator(phone_number_xpath).all()[0].inner_text()
                else:
                     business.phone_number = ""
                if page.locator(review_count_xpath).count() > 0:
                    business.reviews_count = int(
                    page.locator(review_count_xpath).inner_text()
                    .split()[0]
                    .replace(',', '')
                    .strip()
                    )
                else:
                    business.reviews_count = ""
                    
                if page.locator(reviews_average_xpath).count() > 0:
                    business.reviews_average = float(
                        page.locator(reviews_average_xpath).get_attribute(name_attribute)
                        .split()[0]
                        .replace(',', '.')
                        .strip())
                else:
                    business.reviews_average = ""
         

                business.latitude, business.longitude = extract_coordinates_from_url(page.url)

                business_list.business_list.append(business)
                print(f"Added business: {business.name}")  # Debugging statement
            except Exception as e:
                print(f'Error occurred while scraping listing: {e}')

        browser.close()

    return business_list