from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, EmailStr


# ===== Auth =====
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    avatar: str
    token: str


# ===== User =====
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    avatar: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Contact =====
class ContactCreate(BaseModel):
    name: str
    company: str = ''
    email: str = ''
    phone: str = ''
    website: str = ''
    social_links: List[str] = []
    tags: List[str] = []
    notes: str = ''
    source: str = 'Manual'
    status: str = 'New'


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    social_links: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None


class ContactOut(BaseModel):
    id: int
    owner_id: Optional[int]
    name: str
    company: str
    email: str
    phone: str
    website: str
    social_links: List[str]
    tags: List[str]
    notes: str
    source: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Company =====
class CompanyCreate(BaseModel):
    name: str
    domain: str = ''
    phone: str = ''
    address: str = ''
    city: str = ''
    state: str = ''
    country: str = ''
    website: str = ''
    linkedin: str = ''
    industry: str = ''
    size: str = ''
    notes: str = ''


class CompanyOut(BaseModel):
    id: int
    name: str
    domain: str
    phone: str
    address: str
    city: str
    state: str
    country: str
    website: str
    linkedin: str
    industry: str
    size: str
    notes: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Pipeline =====
class PipelineCreate(BaseModel):
    name: str
    stages: List[str] = ['Discovery', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']


class PipelineOut(BaseModel):
    id: int
    name: str
    stages: list
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Deal =====
class DealCreate(BaseModel):
    pipeline_id: Optional[int] = None
    contact_id: Optional[int] = None
    company_id: Optional[int] = None
    owner_id: Optional[int] = None
    name: str
    amount: float = 0.0
    stage: str = 'Discovery'
    probability: int = 10
    expected_close_date: Optional[date] = None


class DealOut(BaseModel):
    id: int
    pipeline_id: Optional[int]
    contact_id: Optional[int]
    company_id: Optional[int]
    owner_id: Optional[int]
    name: str
    amount: float
    stage: str
    probability: int
    expected_close_date: Optional[date]
    lost_reason: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Email =====
class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body: str = ''
    variables: List[str] = []


class EmailSequenceCreate(BaseModel):
    name: str
    steps: list = []
    status: str = 'Draft'


class EmailSettingCreate(BaseModel):
    provider: str = 'SMTP'
    smtp_host: str = ''
    smtp_port: int = 587
    username: str = ''
    password: str = ''
    from_email: str = ''
    reply_to: str = ''


# ===== Task =====
class TaskCreate(BaseModel):
    title: str
    description: str = ''
    assigned_to: Optional[int] = None
    deal_id: Optional[int] = None
    due_date: Optional[date] = None
    priority: str = 'Medium'


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    assigned_to: Optional[int]
    deal_id: Optional[int]
    due_date: Optional[date]
    status: str
    priority: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Event =====
class EventCreate(BaseModel):
    title: str
    description: str = ''
    start_time: datetime
    end_time: Optional[datetime] = None
    all_day: bool = False
    related_to: str = ''
    related_id: Optional[int] = None


# ===== Project =====
class ProjectCreate(BaseModel):
    deal_id: Optional[int] = None
    name: str
    description: str = ''
    start_date: Optional[date] = None
    deadline: Optional[date] = None


class ProjectOut(BaseModel):
    id: int
    deal_id: Optional[int]
    name: str
    description: str
    status: str
    start_date: Optional[date]
    deadline: Optional[date]
    client_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Invoice =====
class InvoiceItem(BaseModel):
    description: str
    quantity: int = 1
    unit_price: float = 0.0


class InvoiceCreate(BaseModel):
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    items: List[InvoiceItem] = []
    tax: float = 0.0
    discount: float = 0.0
    due_date: Optional[date] = None


# ===== Notification =====
class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    read: bool
    link: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Lead Generation =====
class LeadGenRequest(BaseModel):
    api_key: str
    niche: str
    city: str
    state: str
    limit: int = 8


# ===== Dashboard =====
class DashboardSummary(BaseModel):
    total_contacts: int
    total_companies: int
    total_deals: int
    pipeline_value: float
    won_value: float
    recent_deals: List[dict] = []
    upcoming_tasks: List[dict] = []