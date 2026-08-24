import asyncio
import uuid
from typing import Dict, List, Callable
from datetime import datetime
import logging

from .google_maps import GoogleMapsScraper
from .facebook import FacebookScraper
from .yelp import YelpScraper
from ..enrichment.lead_scorer import LeadScorer
from ..enrichment.contact_finder import ContactFinder
from app.models.lead import db

logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self):
        self.scrapers = {
            'google_maps': GoogleMapsScraper(),
            'facebook': FacebookScraper(),
            'yelp': YelpScraper(),
        }
        self.lead_scorer = LeadScorer()
        self.contact_finder = ContactFinder()
        self.active_searches = {}
        
    async def initialize(self):
        """Initialize all scrapers"""
        for scraper in self.scrapers.values():
            await scraper.initialize()
            
    async def start_search(self, search_config: Dict, log_callback: Callable) -> str:
        """Start a new search"""
        search_id = str(uuid.uuid4())
        
        # Store search config
        self.active_searches[search_id] = {
            'config': search_config,
            'status': 'running',
            'progress': 0,
            'leads_found': 0,
            'started_at': datetime.now()
        }
        
        # Run search in background
        asyncio.create_task(self._run_search(search_id, search_config, log_callback))
        
        return search_id
    
    async def _run_search(self, search_id: str, config: Dict, log_callback: Callable):
        """Execute the search"""
        try:
            await log_callback(f"Starting search in {config['city']}, {config['country']}")
            
            all_leads = []
            platforms = config.get('platforms', self.scrapers.keys())
            
            for idx, platform in enumerate(platforms):
                if platform in self.scrapers:
                    await log_callback(f"Scraping {platform}...")
                    
                    try:
                        leads = await self.scrapers[platform].search_businesses(
                            location=f"{config['city']}, {config['country']}",
                            keyword=config.get('keywords')
                        )
                        
                        # Enrich each lead
                        for lead in leads:
                            # Calculate lead score
                            score_data = await self.lead_scorer.score_lead(lead)
                            lead.update(score_data)
                            
                            # Find contact info
                            if lead.get('website'):
                                contacts = await self.contact_finder.find_contacts(lead['website'])
                                if contacts.get('email'):
                                    lead['email'] = contacts['email']
                                if contacts.get('social_links'):
                                    lead.update(contacts['social_links'])
                            
                            # Save to database
                            await db.save_lead(lead)
                            all_leads.append(lead)
                        
                        await log_callback(f"Found {len(leads)} businesses on {platform}")
                        
                    except Exception as e:
                        await log_callback(f"Error scraping {platform}: {str(e)}", "ERROR")
                    
                    # Update progress
                    progress = ((idx + 1) / len(platforms)) * 100
                    self.active_searches[search_id]['progress'] = progress
                    self.active_searches[search_id]['leads_found'] = len(all_leads)
            
            # Search complete
            self.active_searches[search_id]['status'] = 'completed'
            self.active_searches[search_id]['completed_at'] = datetime.now()
            await log_callback(f"Search completed! Found {len(all_leads)} total leads", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Search {search_id} failed: {e}")
            self.active_searches[search_id]['status'] = 'failed'
            await log_callback(f"Search failed: {str(e)}", "ERROR")
    
    async def get_status(self, search_id: str) -> Dict:
        """Get search status"""
        return self.active_searches.get(search_id, {'status': 'not_found'})
    
    async def cleanup(self):
        """Cleanup resources"""
        for scraper in self.scrapers.values():
            await scraper.cleanup()