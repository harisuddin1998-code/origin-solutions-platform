from core.db import execute, query

def create_notification(user_id, title, message="", link=None):
    return execute("INSERT INTO notifications (user_id, title, message, link) VALUES (%s, %s, %s, %s)", (user_id, title, message, link))

def list_notifications(user_id, limit=8):
    return query("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s", (user_id, limit))

def unread_count(user_id):
    return query("SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s AND is_read = FALSE", (user_id,), fetchone=True)["total"]

def mark_all_read(user_id):
    return execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (user_id,))


def get_or_create_company(name, **fields):
    row=query("SELECT * FROM companies WHERE name = %s", (name,), fetchone=True)
    if row: return row
    i=execute("INSERT INTO companies (name, domain, industry, phone, website, city, country, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (name,fields.get("domain"),fields.get("industry"),fields.get("phone"),fields.get("website"),fields.get("city"),fields.get("country"),fields.get("notes")))
    return query("SELECT * FROM companies WHERE id = %s", (i,), fetchone=True)

def create_contact(company_id, name, email="", phone="", job_title="", owner_id=None, lead_id=None):
    return execute("INSERT INTO contacts (company_id, lead_id, name, email, phone, job_title, owner_id, status) VALUES (%s,%s,%s,%s,%s,%s,%s,'qualified')", (company_id,lead_id,name,email,phone,job_title,owner_id))

def create_deal(company_id, name, amount=0, contact_id=None, owner_id=None, stage="qualified", probability=50):
    return execute("INSERT INTO deals (company_id, contact_id, name, amount, stage, probability, owner_id) VALUES (%s,%s,%s,%s,%s,%s,%s)", (company_id,contact_id,name,amount,stage,probability,owner_id))

def create_proposal(deal_id,title,content=""): return execute("INSERT INTO proposals (deal_id,title,content,status) VALUES (%s,%s,%s,'sent')", (deal_id,title,content))

def create_quotation(deal_id,items,total): return execute("INSERT INTO quotations (deal_id,items,total,status) VALUES (%s,%s,%s,'sent')", (deal_id,__import__('json').dumps(items),total))

def create_invoice(company_id,total,deal_id=None,due_date=None,tax=0,discount=0,items=None): return execute("INSERT INTO client_invoices (deal_id,company_id,number,items,subtotal,tax,discount,total,status,due_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'sent',%s)", (deal_id,company_id,'INV-'+str(company_id),__import__('json').dumps(items or []),total,tax,discount,total,due_date))

def record_payment(invoice_id,amount,method="bank_transfer",transaction_ref=""): execute("INSERT INTO client_payments (invoice_id,amount,method,transaction_ref) VALUES (%s,%s,%s,%s)", (invoice_id,amount,method,transaction_ref)); execute("UPDATE client_invoices SET status='paid' WHERE id=%s", (invoice_id,))

def update_deal_stage(deal_id,new_stage,lost_reason=None): execute("UPDATE deals SET stage=%s,lost_reason=%s WHERE id=%s", (new_stage,lost_reason,deal_id)); return {"deal_id":deal_id,"stage":new_stage}

def get_agency_revenue_summary():
    a=query("SELECT COALESCE(SUM(total),0) AS total FROM client_invoices",fetchone=True)["total"]; b=query("SELECT COALESCE(SUM(total),0) AS total FROM client_invoices WHERE status='paid'",fetchone=True)["total"]; return {"total_invoiced":float(a),"total_paid":float(b),"outstanding":float(a)-float(b)}

def get_financial_report(period="month"): return {"period":period,"active_tenants":query("SELECT COUNT(*) AS total FROM tenants WHERE status='active'",fetchone=True)["total"],"gross_pos_revenue":0.0}
