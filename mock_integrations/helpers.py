import random

from core.db import execute, query

FAKE_NAMES = ["Ayesha Khan", "Bilal Ahmed", "Sara Malik", "Hamza Iqbal", "Noor Fatima", "Ali Raza"]


def first_tenant_id():
    row = query("SELECT id FROM tenants ORDER BY created_at DESC LIMIT 1", fetchone=True)
    return row["id"] if row else None


def create_fake_lead(tenant_id, source):
    """Fabricates a lead as if it just arrived from Meta/TikTok/WhatsApp and
    inserts it. The Marketing Hub and Sales CRM pick it up on their next poll
    (see static/js/poll-refresh.js) rather than an instant push."""
    if tenant_id is None:
        raise ValueError("No tenant available to attach the demo lead to.")

    name = random.choice(FAKE_NAMES)
    phone = f"+9230{random.randint(10000000, 99999999)}"
    message = f"Auto-generated demo lead from the mock {source} integration."

    lead_id = execute(
        "INSERT INTO leads (tenant_id, source, name, phone, message, status) VALUES (%s, %s, %s, %s, %s, 'New')",
        (tenant_id, source, name, phone, message),
    )

    payload = {
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "source": source,
        "name": name,
        "phone": phone,
        "message": message,
        "status": "New",
    }

    if source == "whatsapp":
        instance = query(
            "SELECT id FROM whatsapp_instances WHERE tenant_id = %s LIMIT 1", (tenant_id,), fetchone=True
        )
        if instance:
            execute(
                """
                INSERT INTO whatsapp_messages (tenant_id, whatsapp_instance_id, lead_id, direction, body)
                VALUES (%s, %s, %s, 'inbound', %s)
                """,
                (tenant_id, instance["id"], lead_id, message),
            )

    return payload
