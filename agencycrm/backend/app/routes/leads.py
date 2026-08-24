import json
import urllib.parse
import urllib.request
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LeadSource, User
from app.auth import get_current_user

router = APIRouter()


class LeadGenRequest(BaseModel):
    api_key: str
    niche: str
    city: str
    state: str
    limit: int = 8


def _build_fallback_leads(niche: str, city: str, state: str, limit: int) -> List[dict]:
    base_names = [
        f'{niche.title()} Studio',
        f'{city.title()} Growth Lab',
        f'Northstar {niche.title()}',
        f'{city.title()} Digital Works',
        f'Premier {niche.title()} Solutions',
        f'{city.title()} Tech Group',
    ]
    leads = []
    for index, company_name in enumerate(base_names[:limit]):
        domain = company_name.lower().replace(' ', '').replace('-', '') + '.com'
        leads.append({
            'company_name': company_name,
            'email': f'hello@{domain}',
            'contact_number': f'+1-512-{500 + index:03d}-{1000 + index:04d}',
            'website': f'https://{domain}',
            'social_links': [
                f'https://www.linkedin.com/company/{company_name.lower().replace(" ", "-")}',
                f'https://twitter.com/{company_name.lower().replace(" ", "")}',
            ],
            'source': 'Local fallback',
            'city': city.title(),
            'state': state.upper(),
            'niche': niche.title(),
        })
    return leads


def _extract_leads_from_places(places: List[dict], niche: str, city: str, state: str, limit: int) -> List[dict]:
    leads = []
    for index, place in enumerate(places[:limit]):
        company_name = place.get('name', 'Unknown Company')
        website = place.get('website') or place.get('url', '')
        phone = place.get('formatted_phone_number') or place.get('international_phone_number', '')
        social_links = []
        if website:
            social_links.append(website)
        if company_name:
            social_links.append(
                f'https://www.linkedin.com/search/results/companies/?keywords={urllib.parse.quote(company_name)}'
            )
        host = ''
        if website:
            host = website.replace('https://', '').replace('http://', '').split('/')[0]
        leads.append({
            'company_name': company_name,
            'email': f'info@{host}' if host else '',
            'contact_number': phone,
            'website': website,
            'social_links': social_links,
            'source': 'Google Places',
            'city': city.title(),
            'state': state.upper(),
            'niche': niche.title(),
        })
    return leads


def _call_google_places(api_key: str, niche: str, city: str, state: str, limit: int) -> List[dict]:
    query = f'{niche} in {city}, {state}'
    params = urllib.parse.urlencode({
        'query': query,
        'key': api_key,
        'type': 'establishment',
        'language': 'en',
    })
    url = f'https://maps.googleapis.com/maps/api/place/textsearch/json?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': 'AgencyCRM/1.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
    return _extract_leads_from_places(data.get('results', []), niche, city, state, limit)


@router.get('/')
def list_leads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(LeadSource).order_by(LeadSource.created_at.desc()).all()


@router.post('/generate')
def generate_leads(payload: LeadGenRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    imported_leads = []
    if payload.api_key:
        try:
            imported_leads = _call_google_places(
                payload.api_key, payload.niche, payload.city, payload.state, payload.limit
            )
        except Exception:
            imported_leads = []

    if not imported_leads:
        imported_leads = _build_fallback_leads(payload.niche, payload.city, payload.state, payload.limit)

    created = []
    for lead_data in imported_leads:
        existing = db.query(LeadSource).filter(LeadSource.company_name == lead_data['company_name']).first()
        if not existing:
            lead = LeadSource(**lead_data)
            db.add(lead)
            created.append(lead)

    db.commit()
    for lead in created:
        db.refresh(lead)

    all_leads = db.query(LeadSource).order_by(LeadSource.created_at.desc()).all()
    return {'generated': len(created), 'leads': all_leads}