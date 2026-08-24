import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# --- DATABASE SETUP ---
conn = sqlite3.connect('agency_crm.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, 
    email TEXT, company TEXT, phone TEXT, source TEXT, status TEXT DEFAULT 'New')''')

c.execute('''CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, amount REAL, 
    stage TEXT DEFAULT 'Discovery Call', close_date TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, subject TEXT, 
    body TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# --- SALESFORCE STYLE CSS ---
st.markdown("""
<style>
    /* Top Blue Header */
    .sf-header {
        background-color: #0176D3;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .sf-header h1 { margin: 0; font-size: 24px; }
    .sf-header p { margin: 0; opacity: 0.8; }
    
    /* Salesforce Blue Buttons */
    .stButton>button {
        background-color: #0176D3;
        color: white;
        border: none;
        border-radius: 4px;
    }
    .stButton>button:hover {
        background-color: #014486;
        color: white;
    }
    
    /* Clean Dataframes */
    .dataframe { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div class="sf-header">
    <div>
        <h1>Agency CRM</h1>
        <p>Sales & Marketing Cloud</p>
    </div>
    <div style="font-size: 20px;">👤 User</div>
</div>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
menu = st.sidebar.radio("⚡ Navigation", ["🏠 Dashboard", "👥 Leads", "🔄 Sales Pipeline", "✉️ Cold Email"], label_visibility="collapsed")

# --- HELPER FUNCTIONS ---
def add_lead(fn, ln, email, company, phone, source):
    c.execute('INSERT INTO leads (first_name, last_name, email, company, phone, source, status) VALUES (?,?,?,?,?,?,?)',
              (fn, ln, email, company, phone, source, 'New'))
    conn.commit()

def log_email(lead_id, subject, body):
    c.execute('INSERT INTO email_log (lead_id, subject, body) VALUES (?,?,?)', (lead_id, subject, body))
    conn.commit()

# ==========================================
# 1. DASHBOARD
# ==========================================
if menu == "🏠 Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    
    lead_count = len(c.execute('SELECT * FROM leads').fetchall())
    new_leads = len(c.execute('SELECT * FROM leads WHERE status="New"').fetchall())
    pipeline_value = c.execute('SELECT SUM(amount) FROM opportunities WHERE stage NOT IN ("Closed Won", "Closed Lost")').fetchone()[0] or 0
    won_value = c.execute('SELECT SUM(amount) FROM opportunities WHERE stage="Closed Won"').fetchone()[0] or 0
    
    col1.metric("Total Leads", lead_count)
    col2.metric("New Leads", new_leads, delta="Action Required")
    col3.metric("Pipeline Value", f"${pipeline_value:,.0f}")
    col4.metric("Closed Won (Revenue)", f"${won_value:,.0f}")
    
    st.markdown("### Recent Activity")
    recent_emails = pd.read_sql_query("SELECT subject, sent_at FROM email_log ORDER BY sent_at DESC LIMIT 5", conn)
    if not recent_emails.empty:
        st.dataframe(recent_emails, use_container_width=True, hide_index=True)
    else:
        st.info("No emails sent yet.")

# ==========================================
# 2. LEAD MANAGEMENT (Salesforce Style)
# ==========================================
elif menu == "👥 Leads":
    st.subheader("Lead List View")
    leads_df = pd.read_sql_query("SELECT * FROM leads", conn)
    
    # Salesforce Style Table
    st.dataframe(leads_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("➕ New Lead"):
            with st.form("lead_form"):
                fn = st.text_input("First Name")
                ln = st.text_input("Last Name")
                email = st.text_input("Email")
                company = st.text_input("Company")
                phone = st.text_input("Phone")
                source = st.selectbox("Lead Source", ["Website", "Referral", "LinkedIn", "Cold Outbound"])
                submit = st.form_submit_button("Save Lead")
                if submit and fn and email:
                    add_lead(fn, ln, email, company, phone, source)
                    st.success("Lead Saved!")
                    st.experimental_rerun()

    with col2:
        with st.expander("🚀 Convert to Opportunity"):
            if not leads_df.empty:
                lead_ids = leads_df['id'].tolist()
                selected_lead = st.selectbox("Select Lead ID", lead_ids)
                deal_name = st.text_input("Opportunity Name")
                deal_amount = st.number_input("Deal Value ($)", min_value=0.0)
                if st.button("Convert"):
                    c.execute('INSERT INTO opportunities (name, amount, stage) VALUES (?,?,?)', (deal_name, deal_amount, 'Discovery Call'))
                    c.execute('UPDATE leads SET status = "Qualified" WHERE id = ?', (selected_lead,))
                    conn.commit()
                    st.success("Converted! Check Pipeline.")
                    st.experimental_rerun()
            else:
                st.warning("Add leads first.")

# ==========================================
# 3. SALES PIPELINE
# ==========================================
elif menu == "🔄 Sales Pipeline":
    st.subheader("Sales Pipeline")
    stages = ['Discovery Call', 'Proposal Sent', 'Negotiation', 'Closed Won', 'Closed Lost']
    
    with st.expander("➡️ Move Deal Stage"):
        opps_df = pd.read_sql_query("SELECT * FROM opportunities", conn)
        if not opps_df.empty:
            opp_ids = opps_df['id'].tolist()
            selected_opp = st.selectbox("Select Deal ID", opp_ids)
            new_stage = st.selectbox("Move to Stage", stages)
            if st.button("Update Stage"):
                c.execute('UPDATE opportunities SET stage = ? WHERE id = ?', (new_stage, selected_opp))
                conn.commit()
                st.success("Stage Updated!")
                st.experimental_rerun()
    
    cols = st.columns(len(stages))
    for i, stage in enumerate(stages):
        with cols[i]:
            # Card style for pipeline
            if "Closed Lost" in stage: st.markdown(f"**❌ {stage}**")
            elif "Closed Won" in stage: st.markdown(f"**🟢 {stage}**")
            else: st.markdown(f"**🔵 {stage}**")
            
            stage_opps = c.execute('SELECT name, amount FROM opportunities WHERE stage=?', (stage,)).fetchall()
            for opp in stage_opps:
                st.markdown(f"""
                <div style="background-color: #f4f6f9; padding: 10px; border-radius: 5px; border-left: 4px solid #0176D3; margin-bottom: 10px;">
                    <strong>{opp[0]}</strong><br>
                    <span style="color: green; font-weight: bold;">${opp[1]:,.0f}</span>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# 4. COLD EMAIL ENGINE
# ==========================================
elif menu == "✉️ Cold Email":
    st.subheader("Cold Email Outbound")
    
    # SMTP Configuration
    with st.expander("⚙️ Email Settings (SMTP)"):
        st.warning("If using Gmail, you MUST use an App Password, not your regular password.")
        sender_email = st.text_input("Your Email (Sender)", value=st.session_state.get('smtp_email', ''))
        sender_pass = st.text_input("Password / App Password", type="password", value=st.session_state.get('smtp_pass', ''))
        if st.button("Save Settings"):
            st.session_state['smtp_email'] = sender_email
            st.session_state['smtp_pass'] = sender_pass
            st.success("Settings saved for this session!")

    st.markdown("---")
    leads_df = pd.read_sql_query("SELECT id, first_name, last_name, email, company FROM leads", conn)
    
    if leads_df.empty:
        st.info("You need leads to send emails!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Compose Email")
            recipient_id = st.selectbox("Select Lead", leads_df['id'], format_func=lambda x: f"{leads_df[leads_df['id']==x]['first_name'].values[0]} {leads_df[leads_df['id']==x]['last_name'].values[0]} ({leads_df[leads_df['id']==x]['email'].values[0]})")
            
            subject = st.text_input("Subject Line", value="Ideas for your brand's digital presence")
            
            # Dynamic template
            lead_data = leads_df[leads_df['id']==recipient_id].iloc[0]
            default_body = f"""Hi {lead_data['first_name']},

I was checking out {lead_data['company'] or 'your company'} and noticed you guys are doing some really interesting things in your space. 

We run a design agency that specializes in taking brands like yours to the next level—whether that's a high-converting website, a fresh logo, or custom software to automate your workflows.

Would you be open to a quick 10-minute chat next week to see if there's a fit?

Best,
[Your Name]
"""
            body = st.text_area("Email Body", value=default_body, height=300)

            if st.button("🚀 Send Email"):
                if not st.session_state.get('smtp_email') or not st.session_state.get('smtp_pass'):
                    st.error("Please configure your Email Settings above first!")
                else:
                    try:
                        # Send Email Logic
                        msg = MIMEMultipart()
                        msg['From'] = st.session_state['smtp_email']
                        msg['To'] = lead_data['email']
                        msg['Subject'] = subject
                        msg.attach(MIMEText(body, 'plain'))

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(st.session_state['smtp_email'], st.session_state['smtp_pass'])
                        server.send_message(msg)
                        server.quit()

                        # Log the email
                        log_email(recipient_id, subject, body)
                        st.success(f"Email sent successfully to {lead_data['email']}!")
                        
                    except Exception as e:
                        st.error(f"Failed to send email. Error: {e}")

        with col2:
            st.markdown("### Email History")
            history = pd.read_sql_query(f"SELECT subject, sent_at FROM email_log WHERE lead_id={recipient_id} ORDER BY sent_at DESC", conn)
            if not history.empty:
                st.dataframe(history, use_container_width=True, hide_index=True)
            else:
                st.info("No emails sent to this lead yet.")