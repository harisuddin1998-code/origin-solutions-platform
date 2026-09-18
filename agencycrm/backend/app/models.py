import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='Sales')
    avatar = Column(String(500), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    contacts = relationship('Contact', back_populates='owner')
    deals = relationship('Deal', back_populates='owner')
    tasks = relationship('Task', back_populates='assignee')
    notifications = relationship('Notification', back_populates='user')


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String(255), nullable=False)
    company = Column(String(255), default='')
    email = Column(String(255), default='')
    phone = Column(String(50), default='')
    website = Column(String(500), default='')
    social_links = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    notes = Column(Text, default='')
    source = Column(String(100), default='Manual')
    status = Column(String(50), default='New')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner = relationship('User', back_populates='contacts')
    deals = relationship('Deal', back_populates='contact')


class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), default='')
    phone = Column(String(50), default='')
    address = Column(String(500), default='')
    city = Column(String(100), default='')
    state = Column(String(100), default='')
    country = Column(String(100), default='')
    website = Column(String(500), default='')
    linkedin = Column(String(500), default='')
    industry = Column(String(200), default='')
    size = Column(String(50), default='')
    notes = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    deals = relationship('Deal', back_populates='company')


class Pipeline(Base):
    __tablename__ = 'pipelines'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    stages = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    deals = relationship('Deal', back_populates='pipeline')


class Deal(Base):
    __tablename__ = 'deals'

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String(255), nullable=False)
    amount = Column(Float, default=0.0)
    stage = Column(String(100), default='Discovery')
    probability = Column(Integer, default=10)
    expected_close_date = Column(Date, nullable=True)
    lost_reason = Column(String(500), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    pipeline = relationship('Pipeline', back_populates='deals')
    contact = relationship('Contact', back_populates='deals')
    company = relationship('Company', back_populates='deals')
    owner = relationship('User', back_populates='deals')
    tasks = relationship('Task', back_populates='deal')


class EmailTemplate(Base):
    __tablename__ = 'email_templates'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, default='')
    variables = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmailSequence(Base):
    __tablename__ = 'email_sequences'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    steps = Column(JSON, default=list)
    status = Column(String(50), default='Draft')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmailSetting(Base):
    __tablename__ = 'email_settings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    provider = Column(String(50), default='SMTP')
    smtp_host = Column(String(255), default='')
    smtp_port = Column(Integer, default=587)
    username = Column(String(255), default='')
    password = Column(String(500), default='')
    from_email = Column(String(255), default='')
    reply_to = Column(String(255), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmailLog(Base):
    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    template_id = Column(Integer, ForeignKey('email_templates.id'), nullable=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text, default='')
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default='Pending')
    priority = Column(String(20), default='Medium')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assignee = relationship('User', back_populates='tasks')
    deal = relationship('Deal', back_populates='tasks')


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    all_day = Column(Boolean, default=False)
    related_to = Column(String(100), default='')
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    status = Column(String(50), default='Planning')
    start_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    client_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ProjectMember(Base):
    __tablename__ = 'project_members'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    role = Column(String(100), default='Member')


class Milestone(Base):
    __tablename__ = 'milestones'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String(255), nullable=False)
    due_date = Column(Date, nullable=True)
    completed = Column(Boolean, default=False)


class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    number = Column(String(100), unique=True, nullable=False)
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    status = Column(String(50), default='Draft')
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'))
    amount = Column(Float, nullable=False)
    method = Column(String(50), default='Bank Transfer')
    transaction_id = Column(String(500), default='')
    paid_at = Column(DateTime, default=datetime.datetime.utcnow)


class Proposal(Base):
    __tablename__ = 'proposals'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    content = Column(JSON, default=dict)
    status = Column(String(50), default='Draft')
    sent_at = Column(DateTime, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Quotation(Base):
    __tablename__ = 'quotations'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    items = Column(JSON, default=list)
    total = Column(Float, default=0.0)
    status = Column(String(50), default='Draft')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Workflow(Base):
    __tablename__ = 'workflows'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    trigger = Column(JSON, default=dict)
    actions = Column(JSON, default=list)
    status = Column(String(50), default='Active')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(255), nullable=False)
    message = Column(Text, default='')
    type = Column(String(50), default='info')
    read = Column(Boolean, default=False)
    link = Column(String(500), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User', back_populates='notifications')


class LeadSource(Base):
    __tablename__ = 'lead_sources'

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    email = Column(String(255), default='')
    contact_number = Column(String(50), default='')
    website = Column(String(500), default='')
    social_links = Column(JSON, default=list)
    source = Column(String(100), default='Google Places')
    city = Column(String(100), default='')
    state = Column(String(100), default='')
    niche = Column(String(200), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)