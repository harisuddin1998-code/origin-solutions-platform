from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, Dict, List
import uuid
import json

Base = declarative_base()

class LeadModel(Base):
    __tablename__ = "leads"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_id = Column(String(36), index=True)
    business_name = Column(String(500), nullable=False)
    owner_name = Column(String(200))
    phone_number = Column(String(50))
    whatsapp_number = Column(String(50))
    email = Column(String(200), index=True)
    website = Column(String(500))
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    linkedin_url = Column(String(500))
    google_maps_url = Column(String(500))
    address = Column(Text)
    postal_code = Column(String(20))
    rating = Column(Float)
    reviews_count = Column(Integer)
    category = Column(String(200))
    coordinates = Column(JSON)  # {"lat": float, "lng": float}
    opening_hours = Column(JSON)  # {"monday": "9-5", ...}
    
    # AI Enrichment fields
    lead_score = Column(Integer, default=0)  # 1-100
    lead_quality = Column(String(50))  # hot, warm, cold
    needs_website = Column(Boolean, default=False)
    needs_seo = Column(Boolean, default=False)
    needs_digital_marketing = Column(Boolean, default=False)
    needs_crm = Column(Boolean, default=False)
    needs_tracking = Column(Boolean, default=False)
    needs_automation = Column(Boolean, default=False)
    
    # Website analysis
    has_website = Column(Boolean, default=False)
    website_broken = Column(Boolean, default=False)
    has_ssl = Column(Boolean, default=False)
    mobile_responsive = Column(Boolean, default=False)
    website_speed_score = Column(Integer)  # 0-100
    
    # Status and tracking
    status = Column(String(50), default="new")  # new, contacted, qualified, lost
    notes = Column(Text)
    tags = Column(JSON, default=list)  # ["tag1", "tag2"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class SearchModel(Base):
    __tablename__ = "searches"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    country = Column(String(100), nullable=False)
    city = Column(String(200), nullable=False)
    keywords = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    total_leads_found = Column(Integer, default=0)
    progress = Column(Integer, default=0)  # 0-100
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    config = Column(JSON, default=dict)
    
class LeadDatabase:
    def __init__(self, db_url="sqlite:///./leads.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    async def save_lead(self, lead_data: Dict) -> str:
        """Save a single lead to database"""
        session = self.SessionLocal()
        try:
            lead = LeadModel(**lead_data)
            session.add(lead)
            session.commit()
            return lead.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def get_leads(self, **filters) -> List[Dict]:
        """Get leads with filters"""
        session = self.SessionLocal()
        try:
            query = session.query(LeadModel)
            for key, value in filters.items():
                if value is not None:
                    query = query.filter(getattr(LeadModel, key) == value)
            
            leads = query.all()
            return [self._lead_to_dict(lead) for lead in leads]
        finally:
            session.close()
    
    async def update_lead(self, lead_id: str, update_data: Dict):
        """Update lead information"""
        session = self.SessionLocal()
        try:
            lead = session.query(LeadModel).filter(LeadModel.id == lead_id).first()
            if lead:
                for key, value in update_data.items():
                    setattr(lead, key, value)
                session.commit()
                return self._lead_to_dict(lead)
        finally:
            session.close()
    
    def _lead_to_dict(self, lead: LeadModel) -> Dict:
        """Convert lead model to dictionary"""
        return {
            "id": lead.id,
            "business_name": lead.business_name,
            "owner_name": lead.owner_name,
            "phone_number": lead.phone_number,
            "whatsapp_number": lead.whatsapp_number,
            "email": lead.email,
            "website": lead.website,
            "facebook_url": lead.facebook_url,
            "instagram_url": lead.instagram_url,
            "linkedin_url": lead.linkedin_url,
            "google_maps_url": lead.google_maps_url,
            "address": lead.address,
            "postal_code": lead.postal_code,
            "rating": lead.rating,
            "reviews_count": lead.reviews_count,
            "category": lead.category,
            "coordinates": lead.coordinates,
            "opening_hours": lead.opening_hours,
            "lead_score": lead.lead_score,
            "lead_quality": lead.lead_quality,
            "needs_website": lead.needs_website,
            "needs_seo": lead.needs_seo,
            "needs_digital_marketing": lead.needs_digital_marketing,
            "needs_crm": lead.needs_crm,
            "needs_tracking": lead.needs_tracking,
            "needs_automation": lead.needs_automation,
            "has_website": lead.has_website,
            "website_broken": lead.website_broken,
            "has_ssl": lead.has_ssl,
            "mobile_responsive": lead.mobile_responsive,
            "website_speed_score": lead.website_speed_score,
            "status": lead.status,
            "notes": lead.notes,
            "tags": lead.tags,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
        }

# Initialize database
db = LeadDatabase()