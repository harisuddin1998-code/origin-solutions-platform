const API_BASE_URL = (import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL || ''

export interface DashboardSummary {
  agency_name: string
  contact_count: number
  deal_count: number
  pipeline_value: number
  won_value: number
  recent_activity: Array<{ title: string; type: string }>
}

export interface Contact {
  id: string
  name: string
  company: string
  email: string
  status: string
  phone?: string
  website?: string
  social_links?: string[]
}

export interface Lead {
  id: string
  company_name: string
  email: string
  contact_number: string
  website: string
  social_links: string[]
  source: string
  city: string
  state: string
  niche: string
}

export interface EmailCadence {
  id: string
  name: string
  subject: string
  channel: string
  days_after: number
  status: string
}

export interface EmailSettings {
  smtp_host: string
  from_email: string
  reply_to: string
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/summary`)
  if (!response.ok) {
    throw new Error('Failed to load dashboard summary')
  }
  return response.json()
}

export async function fetchContacts(): Promise<Contact[]> {
  const response = await fetch(`${API_BASE_URL}/api/contacts/`)
  if (!response.ok) {
    throw new Error('Failed to load contacts')
  }
  return response.json()
}

export async function createContact(payload: Omit<Contact, 'id'>): Promise<Contact> {
  const response = await fetch(`${API_BASE_URL}/api/contacts/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Failed to create contact')
  }
  return response.json()
}

export async function updateContact(id: string, payload: Omit<Contact, 'id'>): Promise<Contact> {
  const response = await fetch(`${API_BASE_URL}/api/contacts/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Failed to update contact')
  }
  return response.json()
}

export async function deleteContact(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/contacts/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error('Failed to delete contact')
  }
}

export async function fetchLeads(): Promise<Lead[]> {
  const response = await fetch(`${API_BASE_URL}/api/leads/`)
  if (!response.ok) {
    throw new Error('Failed to load leads')
  }
  return response.json()
}

export async function generateLeads(payload: { api_key: string; niche: string; city: string; state: string; limit?: number }): Promise<{ generated: number; leads: Lead[] }> {
  const response = await fetch(`${API_BASE_URL}/api/leads/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Failed to generate leads')
  }
  return response.json()
}

export async function fetchEmailCadences(): Promise<EmailCadence[]> {
  const response = await fetch(`${API_BASE_URL}/api/email/cadences`)
  if (!response.ok) {
    throw new Error('Failed to load email cadences')
  }
  return response.json()
}

export async function createEmailCadence(payload: Omit<EmailCadence, 'id'>): Promise<EmailCadence> {
  const response = await fetch(`${API_BASE_URL}/api/email/cadences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Failed to create email cadence')
  }
  return response.json()
}

export async function fetchEmailSettings(): Promise<EmailSettings> {
  const response = await fetch(`${API_BASE_URL}/api/email/settings`)
  if (!response.ok) {
    throw new Error('Failed to load email settings')
  }
  return response.json()
}

export async function updateEmailSettings(payload: EmailSettings & { role: string }): Promise<EmailSettings> {
  const response = await fetch(`${API_BASE_URL}/api/email/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Failed to update email settings')
  }
  return response.json()
}