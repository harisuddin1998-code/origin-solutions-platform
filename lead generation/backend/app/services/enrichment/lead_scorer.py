from typing import Dict, List
import re
from datetime import datetime
import math

class LeadScorer:
    """AI-powered lead scoring and qualification"""
    
    def __init__(self):
        self.score_weights = {
            'has_website': 10,
            'has_social_media': 8,
            'has_phone': 12,
            'has_email': 15,
            'rating_score': 20,
            'reviews_count': 15,
            'website_quality': 20
        }
    
    async def score_lead(self, lead_data: Dict) -> Dict:
        """Calculate lead score from 1-100"""
        scores = {}
        
        # Website presence (or lack thereof)
        if not lead_data.get('website'):
            # High score for businesses without website (potential client)
            scores['has_website'] = 20
            lead_data['needs_website'] = True
        else:
            scores['has_website'] = 5
            # Analyze website quality
            website_score = await self._analyze_website_quality(lead_data['website'])
            scores['website_quality'] = website_score
            lead_data['needs_seo'] = website_score < 50
            lead_data['needs_digital_marketing'] = website_score < 60
            
            # Check for SSL
            lead_data['has_ssl'] = lead_data.get('has_ssl', False)
            if not lead_data['has_ssl']:
                lead_data['needs_tracking'] = True
        
        # Social media presence
        social_score = 0
        if lead_data.get('facebook_url'):
            social_score += 3
        if lead_data.get('instagram_url'):
            social_score += 3
        if lead_data.get('linkedin_url'):
            social_score += 4
        scores['has_social_media'] = social_score
        
        # Contact information availability
        contact_score = 0
        if lead_data.get('phone_number'):
            contact_score += 6
            # Check if WhatsApp number exists
            if lead_data.get('whatsapp_number'):
                contact_score += 6
        if lead_data.get('email'):
            contact_score += 8
        
        scores['has_phone'] = contact_score if lead_data.get('phone_number') else 0
        scores['has_email'] = 8 if lead_data.get('email') else 0
        
        # Rating and reviews
        rating = lead_data.get('rating', 0)
        reviews = lead_data.get('reviews_count', 0)
        
        rating_score = (rating / 5) * 20 if rating else 0
        reviews_score = min(15, (reviews / 100) * 15) if reviews > 0 else 0
        
        scores['rating_score'] = rating_score
        scores['reviews_count'] = reviews_score
        
        # Calculate total score
        total_score = sum(scores.values())
        
        # Normalize to 0-100 scale
        final_score = min(100, max(0, total_score))
        
        # Determine lead quality
        if final_score >= 70:
            quality = "hot"
        elif final_score >= 40:
            quality = "warm"
        else:
            quality = "cold"
        
        # Identify service needs
        needs = {
            'needs_website': not lead_data.get('website'),
            'needs_seo': scores.get('website_quality', 0) < 50,
            'needs_digital_marketing': scores.get('website_quality', 0) < 60,
            'needs_crm': reviews > 200,  # Businesses with many reviews likely need CRM
            'needs_tracking': not lead_data.get('has_ssl', False),
            'needs_automation': lead_data.get('reviews_count', 0) > 500
        }
        
        return {
            'lead_score': int(final_score),
            'lead_quality': quality,
            **needs
        }
    
    async def _analyze_website_quality(self, website_url: str) -> int:
        """Analyze website quality and return score 0-100"""
        # This would be implemented with actual website analysis
        # For now, return a placeholder score
        import random
        return random.randint(20, 90)
    
    async def categorize_business(self, lead_data: Dict) -> str:
        """Categorize business based on name, description, and keywords"""
        # Business categorization logic
        business_name = lead_data.get('business_name', '').lower()
        category = lead_data.get('category', '').lower()
        
        # Define category keywords
        categories = {
            'restaurant': ['restaurant', 'cafe', 'bakery', 'pizza', 'sushi', 'coffee'],
            'retail': ['store', 'shop', 'mart', 'boutique', 'market'],
            'healthcare': ['clinic', 'dental', 'medical', 'doctor', 'hospital'],
            'professional_services': ['lawyer', 'attorney', 'consultant', 'accountant', 'real estate'],
            'automotive': ['auto', 'car', 'mechanic', 'repair', 'dealership'],
            'beauty': ['salon', 'spa', 'barber', 'nails', 'cosmetics'],
            'fitness': ['gym', 'fitness', 'yoga', 'studio', 'training'],
            'technology': ['tech', 'software', 'it', 'computer', 'digital']
        }
        
        for main_category, keywords in categories.items():
            for keyword in keywords:
                if keyword in business_name or keyword in category:
                    return main_category
        
        return 'other'
    
    async def generate_outreach_email(self, lead_data: Dict, service_type: str) -> str:
        """Generate personalized outreach email using AI"""
        business_name = lead_data.get('business_name', 'Business')
        owner_name = lead_data.get('owner_name', 'Owner')
        
        templates = {
            'website': f"""Subject: Transform {business_name}'s Online Presence

Dear {owner_name},

I noticed that {business_name} currently doesn't have a website. In today's digital age, this is a significant missed opportunity.

We specialize in creating professional, high-converting websites that help businesses like yours attract more customers and increase revenue.

Would you be open to a quick 10-minute call to discuss how we can build a website that drives real results for {business_name}?

Best regards,
[Your Name]""",
            
            'seo': f"""Subject: Boost {business_name}'s Search Rankings

Hi {owner_name},

I analyzed {business_name}'s online presence and found opportunities to improve your search engine visibility.

Our SEO services can help:
• Rank higher on Google Maps
• Get more local customers
• Increase online reviews

Would you like to see a free SEO audit for {business_name}?

Best regards,
[Your Name]""",
            
            'digital_marketing': f"""Subject: Digital Marketing Solutions for {business_name}

Dear {owner_name},

I see that {business_name} could benefit from a comprehensive digital marketing strategy.

We help businesses like yours with:
• Social media management
• Paid advertising
• Content marketing
• Email campaigns

Let's schedule a call to discuss how we can grow {business_name}'s online presence.

Best regards,
[Your Name]"""
        }
        
        return templates.get(service_type, templates['website'])