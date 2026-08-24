import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import {
  createContact,
  createEmailCadence,
  deleteContact,
  fetchContacts,
  fetchDashboardSummary,
  fetchEmailCadences,
  fetchEmailSettings,
  fetchLeads,
  generateLeads,
  updateContact,
  updateEmailSettings,
  type Contact,
  type DashboardSummary,
  type EmailCadence,
  type EmailSettings,
  type Lead,
} from './services/api'

type Deal = {
  title: string
  amount: string
  stage: string
  owner: string
  note?: string
}

const modules = [
  { label: 'Dashboard', to: '/' },
  { label: 'Contacts', to: '/contacts' },
  { label: 'Email', to: '/email' },
]

function App() {
  const [user, setUser] = useState<{ name: string; role: string } | null>(null)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchDashboardSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
  }, [])

  if (!user) {
    return <LoginScreen onLogin={setUser} />
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-logo-placeholder">AC</div>
          <div>
            <div className="brand">Agency CRM</div>
            <div className="brand-subtitle">Sales & Marketing</div>
          </div>
        </div>
        <div className="user-pill">
          <strong>{user.name}</strong>
          <span>{user.role}</span>
        </div>
        <nav className="nav-list">
          {modules.map((item) => (
            <NavLink key={item.label} to={item.to} className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button className="secondary-btn" onClick={() => { setUser(null); navigate('/') }}>Sign out</button>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Agency Operations</p>
            <h1>Run your agency with clarity.</h1>
          </div>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <div className="stat-value">{summary?.contact_count ?? 0}</div>
            <div className="stat-label">Active contacts</div>
          </article>
          <article className="stat-card">
            <div className="stat-value">{summary?.deal_count ?? 0}</div>
            <div className="stat-label">Open deals</div>
          </article>
          <article className="stat-card">
            <div className="stat-value">${summary?.pipeline_value ? (summary.pipeline_value / 1000).toFixed(0) + 'k' : '0k'}</div>
            <div className="stat-label">Pipeline value</div>
          </article>
          <article className="stat-card">
            <div className="stat-value">${summary?.won_value ? (summary.won_value / 1000).toFixed(0) + 'k' : '0k'}</div>
            <div className="stat-label">Closed won</div>
          </article>
        </section>

        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/contacts" element={<ContactsView />} />
          <Route path="/email" element={<EmailView userRole={user.role} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function LoginScreen({ onLogin }: { onLogin: (user: { name: string; role: string }) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('Manager')

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!email || !password) return
    const name = email.split('@')[0]
    onLogin({ name: name.replace('.', ' ').replace(/\b\w/g, (char) => char.toUpperCase()), role })
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>Agency CRM</h1>
        <p>Sign in to your agency workspace</p>
        <form className="form-stack" onSubmit={submit}>
          <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" />
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="Admin">Admin</option>
            <option value="Manager">Manager</option>
            <option value="Sales">Sales</option>
            <option value="Client">Client</option>
          </select>
          <button className="primary-btn" type="submit">Enter workspace</button>
        </form>
      </div>
    </div>
  )
}

function DashboardView() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)

  useEffect(() => {
    fetchDashboardSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
  }, [])

  const stages = [
    { key: 'Discovery', title: 'Discovery' },
    { key: 'Proposal', title: 'Proposal' },
    { key: 'Negotiation', title: 'Negotiation' },
    { key: 'Won', title: 'Won' },
  ]

  const [deals, setDeals] = useState<Deal[]>([
    { title: 'Website redesign', amount: '$8,400', stage: 'Discovery', owner: 'Mina', note: 'Discovery call booked' },
    { title: 'SEO retainers', amount: '$4,200', stage: 'Proposal', owner: 'Luis', note: 'Proposal sent yesterday' },
    { title: 'Brand refresh', amount: '$6,900', stage: 'Negotiation', owner: 'Nina', note: 'Waiting on client feedback' },
    { title: 'Mobile app MVP', amount: '$15,000', stage: 'Won', owner: 'Ava', note: 'Kickoff next week' },
  ])
  const [draft, setDraft] = useState({ title: '', amount: '', owner: '', note: '' })
  const [dragging, setDragging] = useState<string | null>(null)

  const onDrop = (stage: string) => {
    if (!dragging) return
    setDeals((current) => current.map((deal) => (deal.title === dragging ? { ...deal, stage } : deal)))
    setDragging(null)
  }

  const addDeal = (event: React.FormEvent) => {
    event.preventDefault()
    if (!draft.title || !draft.amount || !draft.owner) return
    setDeals((current) => [...current, { ...draft, stage: 'Discovery' }])
    setDraft({ title: '', amount: '', owner: '', note: '' })
  }

  return (
    <>
      <section className="content-grid">
        <article className="panel-card">
          <h3>Pipeline health</h3>
          <p>{summary?.agency_name ?? 'Agency CRM'} is tracking {summary?.deal_count ?? 0} live opportunities across the funnel.</p>
        </article>
        <article className="panel-card">
          <h3>Delivery board</h3>
          <p>{summary?.recent_activity?.[0]?.title ?? 'No recent activity yet'} and activity is being captured automatically.</p>
        </article>
      </section>

      <section className="panel-card board-card">
        <div className="board-header">
          <div>
            <h3>Sales pipeline</h3>
            <p>Drag deals between stages</p>
          </div>
        </div>

        <form className="deal-form" onSubmit={addDeal}>
          <input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Deal title" />
          <input value={draft.amount} onChange={(event) => setDraft({ ...draft, amount: event.target.value })} placeholder="Amount" />
          <input value={draft.owner} onChange={(event) => setDraft({ ...draft, owner: event.target.value })} placeholder="Owner" />
          <input value={draft.note} onChange={(event) => setDraft({ ...draft, note: event.target.value })} placeholder="Note" />
          <button className="primary-btn" type="submit">Add deal</button>
        </form>

        <div className="kanban-board">
          {stages.map((stage) => (
            <div key={stage.key} className="kanban-column">
              <div className="kanban-column-header">
                <strong>{stage.title}</strong>
                <span>{deals.filter((deal) => deal.stage === stage.key).length}</span>
              </div>
              <div className="kanban-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={() => onDrop(stage.key)}>
                {deals
                  .filter((deal) => deal.stage === stage.key)
                  .map((deal) => (
                    <div key={deal.title} className="kanban-card" draggable onDragStart={() => setDragging(deal.title)}>
                      <div className="kanban-card-title">{deal.title}</div>
                      <div className="kanban-card-meta">{deal.amount}</div>
                      {deal.note ? <div className="kanban-card-note">{deal.note}</div> : null}
                      <div className="kanban-card-footer">
                        <span>{deal.owner}</span>
                        <span className="pill">{stage.title}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}

function ContactsView() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', company: '', email: '', status: 'New', phone: '', website: '', social_links: '' })
  const [leadForm, setLeadForm] = useState({ api_key: '', niche: '', city: '', state: '', limit: '8' })

  const loadContacts = () => {
    fetchContacts().then(setContacts).catch(() => setContacts([]))
  }

  const loadLeads = () => {
    fetchLeads().then(setLeads).catch(() => setLeads([]))
  }

  useEffect(() => {
    loadContacts()
    loadLeads()
  }, [])

  const resetForm = () => {
    setForm({ name: '', company: '', email: '', status: 'New', phone: '', website: '', social_links: '' })
    setEditingId(null)
  }

  const saveContact = async (resetAfterSave: boolean) => {
    if (!form.name || !form.company || !form.email) return
    const payload = {
      name: form.name,
      company: form.company,
      email: form.email,
      status: form.status,
      phone: form.phone,
      website: form.website,
      social_links: form.social_links.split(',').map((entry) => entry.trim()).filter(Boolean),
    }

    try {
      if (editingId) {
        await updateContact(editingId, payload)
      } else {
        await createContact(payload)
      }

      if (resetAfterSave) {
        resetForm()
      }
      loadContacts()
    } catch (error) {
      window.alert(`Contact save failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    await saveContact(true)
  }

  const saveAndNew = async () => {
    await saveContact(true)
  }

  const remove = async (id: string) => {
    try {
      await deleteContact(id)
      if (editingId === id) {
        resetForm()
      }
      loadContacts()
    } catch (error) {
      window.alert(`Contact delete failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const startEdit = (contact: Contact) => {
    setEditingId(contact.id)
    setForm({
      name: contact.name,
      company: contact.company,
      email: contact.email,
      status: contact.status,
      phone: contact.phone ?? '',
      website: contact.website ?? '',
      social_links: (contact.social_links ?? []).join(', '),
    })
  }

  const downloadLeads = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!leadForm.api_key || !leadForm.niche || !leadForm.city || !leadForm.state) return
    try {
      const result = await generateLeads({
        api_key: leadForm.api_key,
        niche: leadForm.niche,
        city: leadForm.city,
        state: leadForm.state,
        limit: Number(leadForm.limit),
      })
      setLeadForm({ api_key: '', niche: '', city: '', state: '', limit: '8' })
      setLeads(result.leads)
    } catch (error) {
      window.alert(`Lead download failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  return (
    <section className="content-grid wider-grid">
      <div className="content-stack">
        <article className="panel-card">
          <div className="board-header">
            <div>
              <h3>{editingId ? 'Edit contact' : 'Create contact'}</h3>
              <p>Managers can maintain full contact records.</p>
            </div>
            <button className="secondary-btn" type="button" onClick={resetForm}>New contact</button>
          </div>
          <form className="form-stack" onSubmit={submit}>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Name *" />
            <input value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} placeholder="Company *" />
            <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email *" />
            <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="Phone" />
            <input value={form.website} onChange={(event) => setForm({ ...form, website: event.target.value })} placeholder="Website" />
            <input value={form.social_links} onChange={(event) => setForm({ ...form, social_links: event.target.value })} placeholder="Social links (comma separated)" />
            <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
              <option value="New">New</option>
              <option value="Qualified">Qualified</option>
              <option value="Won">Won</option>
            </select>
            <div className="contact-actions">
              <button className="primary-btn" type="submit">{editingId ? 'Save changes' : 'Save contact'}</button>
              <button className="secondary-btn" type="button" onClick={saveAndNew}>Save & new</button>
              {editingId && <button className="secondary-btn" type="button" onClick={resetForm}>Cancel</button>}
            </div>
          </form>
        </article>

        <article className="panel-card">
          <h3>Lead generation</h3>
          <p className="muted">Add a Google Places API key to pull leads by niche and US city directly into the sales lead queue.</p>
          <form className="form-stack" onSubmit={downloadLeads}>
            <input value={leadForm.api_key} onChange={(event) => setLeadForm({ ...leadForm, api_key: event.target.value })} placeholder="Google API key *" />
            <input value={leadForm.niche} onChange={(event) => setLeadForm({ ...leadForm, niche: event.target.value })} placeholder="Niche (e.g. software agency) *" />
            <input value={leadForm.city} onChange={(event) => setLeadForm({ ...leadForm, city: event.target.value })} placeholder="US city *" />
            <input value={leadForm.state} onChange={(event) => setLeadForm({ ...leadForm, state: event.target.value })} placeholder="State *" />
            <input value={leadForm.limit} onChange={(event) => setLeadForm({ ...leadForm, limit: event.target.value })} placeholder="Number of leads (default 8)" />
            <button className="primary-btn" type="submit">Download leads</button>
          </form>
        </article>
      </div>

      <div className="content-stack">
        <article className="panel-card">
          <h3>Contact list</h3>
          {contacts.length === 0 ? (
            <p>No contacts yet. Add the first one to begin building the CRM.</p>
          ) : (
            <div className="contact-list">
              {contacts.map((contact) => (
                <div key={contact.id} className="contact-item">
                  <div>
                    <strong>{contact.name}</strong>
                    <div className="muted">{contact.company}</div>
                    <div className="muted">{contact.email}</div>
                    {contact.phone ? <div className="muted">{contact.phone}</div> : null}
                    {contact.website ? <div className="muted">{contact.website}</div> : null}
                  </div>
                  <div className="contact-actions">
                    <span className="pill">{contact.status}</span>
                    <button className="secondary-btn" onClick={() => startEdit(contact)}>Edit</button>
                    <button className="secondary-btn" onClick={() => remove(contact.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <h3>Sales lead queue</h3>
          {leads.length === 0 ? (
            <p>No leads have been imported yet. Use the lead generation form to download new prospects.</p>
          ) : (
            <div className="contact-list">
              {leads.map((lead) => (
                <div key={lead.id} className="contact-item">
                  <div>
                    <strong>{lead.company_name}</strong>
                    <div className="muted">{lead.email}</div>
                    <div className="muted">{lead.contact_number}</div>
                    {lead.website ? <div className="muted">{lead.website}</div> : null}
                    {lead.social_links?.length > 0 ? <div className="muted">{lead.social_links.join(' • ')}</div> : null}
                  </div>
                  <div className="contact-actions">
                    <span className="pill">{lead.city}, {lead.state}</span>
                    <span className="pill">{lead.source}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>
    </section>
  )
}

function EmailView({ userRole }: { userRole: string }) {
  const [cadences, setCadences] = useState<EmailCadence[]>([])
  const [settings, setSettings] = useState<EmailSettings | null>(null)
  const [form, setForm] = useState({ name: '', subject: '', channel: 'Email', days_after: '3', status: 'Draft' })
  const [settingsForm, setSettingsForm] = useState({ smtp_host: '', from_email: '', reply_to: '' })

  const loadCadences = () => {
    fetchEmailCadences().then(setCadences).catch(() => setCadences([]))
  }

  const loadSettings = () => {
    fetchEmailSettings()
      .then((data) => {
        setSettings(data)
        setSettingsForm(data)
      })
      .catch(() => setSettings(null))
  }

  useEffect(() => {
    loadCadences()
    loadSettings()
  }, [])

  const submitCadence = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!form.name || !form.subject) return
    await createEmailCadence({
      name: form.name,
      subject: form.subject,
      channel: form.channel,
      days_after: Number(form.days_after),
      status: form.status,
    })
    setForm({ name: '', subject: '', channel: 'Email', days_after: '3', status: 'Draft' })
    loadCadences()
  }

  const saveSettings = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!settingsForm.smtp_host || !settingsForm.from_email || !settingsForm.reply_to) return
    await updateEmailSettings({ ...settingsForm, role: userRole })
    loadSettings()
  }

  return (
    <section className="content-grid wider-grid">
      <article className="panel-card">
        <h3>Create email cadence</h3>
        <form className="form-stack" onSubmit={submitCadence}>
          <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Cadence name *" />
          <input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })} placeholder="Email subject *" />
          <select value={form.channel} onChange={(event) => setForm({ ...form, channel: event.target.value })}>
            <option value="Email">Email</option>
            <option value="SMS">SMS</option>
          </select>
          <input value={form.days_after} onChange={(event) => setForm({ ...form, days_after: event.target.value })} placeholder="Days after lead enters" />
          <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
            <option value="Draft">Draft</option>
            <option value="Active">Active</option>
            <option value="Paused">Paused</option>
          </select>
          <button className="primary-btn" type="submit">Save cadence</button>
        </form>
      </article>

      <div className="content-stack">
        <article className="panel-card">
          <h3>Cadence overview</h3>
          {cadences.length === 0 ? (
            <p>No email cadences yet. Create one to start automating your outreach.</p>
          ) : (
            <div className="contact-list">
              {cadences.map((cadence) => (
                <div key={cadence.id} className="contact-item">
                  <div>
                    <strong>{cadence.name}</strong>
                    <div className="muted">{cadence.subject}</div>
                    <div className="muted">{cadence.channel} • {cadence.days_after} days after lead enters</div>
                  </div>
                  <span className="pill">{cadence.status}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel-card">
          <h3>Email settings</h3>
          <p className="muted">Only managers can update SMTP and sender details.</p>
          <form className="form-stack" onSubmit={saveSettings}>
            <input value={settingsForm.smtp_host} onChange={(event) => setSettingsForm({ ...settingsForm, smtp_host: event.target.value })} placeholder="SMTP host *" />
            <input value={settingsForm.from_email} onChange={(event) => setSettingsForm({ ...settingsForm, from_email: event.target.value })} placeholder="From email *" />
            <input value={settingsForm.reply_to} onChange={(event) => setSettingsForm({ ...settingsForm, reply_to: event.target.value })} placeholder="Reply to *" />
            <button className="primary-btn" type="submit" disabled={userRole !== 'Manager'}>
              {userRole === 'Manager' ? 'Save settings' : 'Manager only'}
            </button>
          </form>
          {settings && (
            <div className="muted" style={{ marginTop: '8px' }}>
              Current: {settings.smtp_host} / {settings.from_email}
            </div>
          )}
        </article>
      </div>
    </section>
  )
}

export default App