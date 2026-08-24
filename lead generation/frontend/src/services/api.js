const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class API {
  constructor() {
    this.baseURL = API_BASE_URL;
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async startSearch(searchParams) {
    return this.request('/api/search', {
      method: 'POST',
      body: JSON.stringify(searchParams),
    });
  }
  
  async getSearchStatus(searchId) {
    return this.request(`/api/search/${searchId}/status`);
  }
  
  async getLeads(filters) {
    const queryParams = new URLSearchParams(filters).toString();
    return this.request(`/api/leads?${queryParams}`);
  }
  
  async exportLeads(exportParams) {
    const response = await fetch(`${this.baseURL}/api/export`, {
      method: 'POST',
      body: JSON.stringify(exportParams),
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Export failed');
    }
    
    return response;
  }
  
  async getSearchHistory() {
    return this.request('/api/searches/history');
  }
  
  async getSettings() {
    return this.request('/api/settings');
  }
  
  async updateSettings(settings) {
    return this.request('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }
  
  async updateLead(leadId, updates) {
    return this.request(`/api/leads/${leadId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }
}

export default new API();