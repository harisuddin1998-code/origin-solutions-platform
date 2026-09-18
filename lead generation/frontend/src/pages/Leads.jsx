import React, { useState, useEffect } from 'react';
import LeadTable from '../components/LeadTable';
import api from '../services/api';

function Leads() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchHistory, setSearchHistory] = useState([]);
  
  useEffect(() => {
    loadLeads();
    loadSearchHistory();
  }, []);
  
  const loadLeads = async () => {
    try {
      const response = await api.getLeads({});
      setLeads(response.leads);
    } catch (error) {
      console.error('Failed to load leads:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const loadSearchHistory = async () => {
    try {
      const response = await api.getSearchHistory();
      setSearchHistory(response.history);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };
  
  const filteredLeads = statusFilter === 'all' 
    ? leads 
    : leads.filter(lead => lead.lead_quality === statusFilter);
  
  const stats = {
    total: leads.length,
    hot: leads.filter(l => l.lead_quality === 'hot').length,
    warm: leads.filter(l => l.lead_quality === 'warm').length,
    cold: leads.filter(l => l.lead_quality === 'cold').length,
    noWebsite: leads.filter(l => !l.has_website).length
  };
  
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Leads</h3>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
        </div>
        <div className="card border-l-4 border-red-500">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Hot Leads</h3>
          <p className="text-2xl font-bold text-red-600">{stats.hot}</p>
        </div>
        <div className="card border-l-4 border-yellow-500">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Warm Leads</h3>
          <p className="text-2xl font-bold text-yellow-600">{stats.warm}</p>
        </div>
        <div className="card border-l-4 border-blue-500">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Cold Leads</h3>
          <p className="text-2xl font-bold text-blue-600">{stats.cold}</p>
        </div>
        <div className="card border-l-4 border-purple-500">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">No Website</h3>
          <p className="text-2xl font-bold text-purple-600">{stats.noWebsite}</p>
        </div>
      </div>
      
      {/* Filters */}
      <div className="card">
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-4 py-2 rounded-md ${
              statusFilter === 'all' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setStatusFilter('hot')}
            className={`px-4 py-2 rounded-md ${
              statusFilter === 'hot' 
                ? 'bg-red-600 text-white' 
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            Hot
          </button>
          <button
            onClick={() => setStatusFilter('warm')}
            className={`px-4 py-2 rounded-md ${
              statusFilter === 'warm' 
                ? 'bg-yellow-600 text-white' 
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            Warm
          </button>
          <button
            onClick={() => setStatusFilter('cold')}
            className={`px-4 py-2 rounded-md ${
              statusFilter === 'cold' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            Cold
          </button>
        </div>
        
        <LeadTable leads={filteredLeads} />
      </div>
      
      {/* Search History */}
      {searchHistory.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            Recent Searches
          </h3>
          <div className="space-y-2">
            {searchHistory.slice(0, 5).map((search) => (
              <div key={search.id} className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {search.city}, {search.country}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {search.keywords || 'All businesses'} • {search.total_leads_found} leads found
                  </p>
                </div>
                <span className="text-sm text-gray-500">
                  {new Date(search.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Leads;