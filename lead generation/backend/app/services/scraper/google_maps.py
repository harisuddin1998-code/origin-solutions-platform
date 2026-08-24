from playwright.async_api import async_playwright
import asyncio
from typing import List, Dict, Optional
import re
from datetime import datetime
import logging

from ..base import BaseScraper
from app.utils.proxy_manager import ProxyManager
from app.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class GoogleMapsScraper(BaseScraper):
    """Scraper for Google Maps business listings"""
    
    def __init__(self):
        super().__init__()
        self.proxy_manager = ProxyManager()
        self.rate_limiter = RateLimiter(requests_per_minute=30)
        self.base_url = "https://www.google.com/maps"
    
    async def search_businesses(self, location: str, keyword: str = None) -> List[Dict]:
        """Search for businesses on Google Maps"""
        businesses = []
        
        async with async_playwright() as p:
            # Use proxy if available
            proxy = await self.proxy_manager.get_proxy()
            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                # Navigate to Google Maps
                await self.rate_limiter.wait()
                await page.goto(self.base_url)
                
                # Search for businesses
                search_query = f"{keyword} in {location}" if keyword else f"businesses in {location}"
                await page.fill('input[aria-label="Search"]', search_query)
                await page.keyboard.press('Enter')
                
                # Wait for results to load
                await page.wait_for_selector('div[role="feed"]', timeout=10000)
                
                # Scroll to load more results
                await self._scroll_results(page)
                
                # Extract business listings
                businesses = await self._extract_businesses(page)
                
            except Exception as e:
                logger.error(f"Error scraping Google Maps: {e}")
            finally:
                await browser.close()
        
        return businesses
    
    async def _scroll_results(self, page, max_scrolls=50):
        """Scroll through search results to load more"""
        for i in range(max_scrolls):
            await page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(0.5)
            
            # Check if reached the end
            end_of_results = await page.query_selector('div[role="feed"] div:last-child')
            if end_of_results:
                break
    
    async def _extract_businesses(self, page) -> List[Dict]:
        """Extract business information from results"""
        businesses = []
        
        # Wait for business cards to load
        cards = await page.query_selector_all('div[role="feed"] > div > div > a')
        
        for card in cards[:100]:  # Limit to 100 results per search
            try:
                # Click to open business details
                await card.click()
                await asyncio.sleep(1)
                
                # Extract business details
                business = await self._extract_business_details(page)
                if business:
                    businesses.append(business)
                    
            except Exception as e:
                logger.warning(f"Error extracting business card: {e}")
                continue
        
        return businesses
    
    async def _extract_business_details(self, page) -> Optional[Dict]:
        """Extract detailed information for a business"""
        try:
            business = {}
            
            # Business name
            name_element = await page.query_selector('h1')
            business['business_name'] = await name_element.inner_text() if name_element else None
            
            # Address
            address_element = await page.query_selector('button[data-item-id="address"]')
            if address_element:
                business['address'] = await address_element.get_attribute('aria-label')
            
            # Phone number
            phone_element = await page.query_selector('button[data-item-id="phone:tel"]')
            if phone_element:
                business['phone_number'] = await phone_element.get_attribute('aria-label')
            
            # Website
            website_element = await page.query_selector('a[data-item-id="authority"]')
            if website_element:
                business['website'] = await website_element.get_attribute('href')
            
            # Rating and reviews
            rating_element = await page.query_selector('div[aria-label*="stars"]')
            if rating_element:
                rating_text = await rating_element.get_attribute('aria-label')
                if rating_text:
                    match = re.search(r'([\d.]+) stars', rating_text)
                    business['rating'] = float(match.group(1)) if match else None
            
            reviews_element = await page.query_selector('button[aria-label*="reviews"]')
            if reviews_element:
                reviews_text = await reviews_element.inner_text()
                match = re.search(r'(\d+)', reviews_text)
                business['reviews_count'] = int(match.group(1)) if match else 0
            
            # Category
            category_element = await page.query_selector('button[aria-label*="category"]')
            if category_element:
                business['category'] = await category_element.inner_text()
            
            # Opening hours
            hours_element = await page.query_selector('div[aria-label*="hours"]')
            if hours_element:
                business['opening_hours'] = await hours_element.inner_text()
            
            # Google Maps URL
            current_url = page.url
            business['google_maps_url'] = current_url
            
            return business
            
        except Exception as e:
            logger.error(f"Error extracting business details: {e}")
            return None