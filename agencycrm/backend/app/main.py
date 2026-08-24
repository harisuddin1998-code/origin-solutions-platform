from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes import auth as auth_routes
from app.routes import contacts as contact_routes
from app.routes import companies as company_routes
from app.routes import pipelines as pipeline_routes
from app.routes import deals as deal_routes
from app.routes import email as email_routes
from app.routes import tasks as task_routes
from app.routes import events as event_routes
from app.routes import projects as project_routes
from app.routes import invoices as invoice_routes
from app.routes import proposals as proposal_routes
from app.routes import quotations as quotation_routes
from app.routes import workflows as workflow_routes
from app.routes import notifications as notification_routes
from app.routes import leads as lead_routes
from app.routes import dashboard as dashboard_routes

app = FastAPI(title='Agency CRM', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Auth
app.include_router(auth_routes.router, prefix='/api/auth', tags=['Auth'])
# Core CRM
app.include_router(contact_routes.router, prefix='/api/contacts', tags=['Contacts'])
app.include_router(company_routes.router, prefix='/api/companies', tags=['Companies'])
# Sales
app.include_router(pipeline_routes.router, prefix='/api/pipelines', tags=['Pipelines'])
app.include_router(deal_routes.router, prefix='/api/deals', tags=['Deals'])
# Email
app.include_router(email_routes.router, prefix='/api/email', tags=['Email'])
# Tasks & Calendar
app.include_router(task_routes.router, prefix='/api/tasks', tags=['Tasks'])
app.include_router(event_routes.router, prefix='/api/events', tags=['Events'])
# Projects
app.include_router(project_routes.router, prefix='/api/projects', tags=['Projects'])
# Invoices
app.include_router(invoice_routes.router, prefix='/api/invoices', tags=['Invoices'])
# Proposals & Quotations
app.include_router(proposal_routes.router, prefix='/api/proposals', tags=['Proposals'])
app.include_router(quotation_routes.router, prefix='/api/quotations', tags=['Quotations'])
# Automation
app.include_router(workflow_routes.router, prefix='/api/workflows', tags=['Workflows'])
# Notifications
app.include_router(notification_routes.router, prefix='/api/notifications', tags=['Notifications'])
# Lead Generation
app.include_router(lead_routes.router, prefix='/api/leads', tags=['Leads'])
# Dashboard
app.include_router(dashboard_routes.router, prefix='/api/dashboard', tags=['Dashboard'])


@app.on_event('startup')
def on_startup():
    init_db()
    # Seed default pipeline
    from app.database import SessionLocal
    from app.models import Pipeline, User
    from app.auth import hash_password
    db = SessionLocal()
    try:
        # Create default user
        existing = db.query(User).filter(User.email == 'admin@agencycrm.com').first()
        if not existing:
            user = User(
                name='Admin User',
                email='admin@agencycrm.com',
                password_hash=hash_password('admin123'),
                role='Admin',
            )
            db.add(user)
            db.commit()

        # Create default pipeline
        existing_pipeline = db.query(Pipeline).filter(Pipeline.name == 'Sales Pipeline').first()
        if not existing_pipeline:
            pipeline = Pipeline(
                name='Sales Pipeline',
                stages=['Discovery', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost'],
            )
            db.add(pipeline)
            db.commit()
    finally:
        db.close()


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'agency-crm'}