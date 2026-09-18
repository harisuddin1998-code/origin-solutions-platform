import React, { useState } from 'react';

function LeadTable({ leads }) {
  const [sortField, setSortField] = useState('lead_score');
  const [sortDirection, setSortDirection] = useState('desc');
  const [filter, setFilter] = useState('');
  const [selectedLeads, setSelectedLeads] = useState([]);
  
  const sortedLeads = [...leads].sort((a, b) => {
    let aVal = a[sortField] || 0;
    let bVal = b[sortField] || 0;
    
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    
    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });
  
  const filteredLeads = sortedLeads.filter(lead =>
    lead.business_name?.toLowerCase().includes(filter.toLowerCase()) ||
    lead.category?.toLowerCase().includes(filter.toLowerCase()) ||
    lead.phone_number?.includes(filter)
  );
  
  const getScoreColor = (score) => {
    if (score >= 70) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    if (score >= 40) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
  };
  
  const getQualityBadge = (quality) => {
    const colors = {
      hot: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      warm: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      cold: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    };
    return colors[quality] || colors.cold;
  };
  
  const toggleSelectAll = () => {
    if (selectedLeads.length === filteredLeads.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads(filteredLeads.map(l => l.id));
    }
  };
  
  const toggleSelectLead = (leadId) => {
    if (selectedLeads.includes(leadId)) {
      setSelectedLeads(selectedLeads.filter(id => id !== leadId));
    } else {
      setSelectedLeads([...selectedLeads, leadId]);
    }
  };
  
  return (
    <div className="overflow-x-auto">
      {/* Filters and Search */}
      <div className="mb-4 flex gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="🔍 Filter by business name, category, or phone..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setSortField('lead_score')}
            className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-md"
          >
            Sort by Score
          </button>
          <button
            onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
            className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-md"
          >
            {sortDirection === 'asc' ? '↑' : '↓'}
          </button>
        </div>
      </div>
      
      {/* Selected Count */}
      {selectedLeads.length > 0 && (
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
          <span className="text-sm text-blue-700 dark:text-blue-300">
            {selectedLeads.length} leads selected
          </span>
        </div>
      )}
      
      {/* Leads Table */}
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-3 py-3 text-left">
              <input
                type="checkbox"
                checked={selectedLeads.length === filteredLeads.length && filteredLeads.length > 0}
                onChange={toggleSelectAll}
                className="rounded border-gray-300"
              />
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Business Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Category
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Phone
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Email
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Score/Quality
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Website
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Needs
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
          {filteredLeads.map((lead) => (
            <tr key={lead.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <td className="px-3 py-4">
                <input
                  type="checkbox"
                  checked={selectedLeads.includes(lead.id)}
                  onChange={() => toggleSelectLead(lead.id)}
                  className="rounded border-gray-300"
                />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                {lead.business_name}
               </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {lead.category || 'N/A'}
               </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {lead.phone_number || '-'}
               </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {lead.email || '-'}
               </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getScoreColor(lead.lead_score)}`}>
                    {lead.lead_score || 0}
                  </span>
                  {lead.lead_quality && (
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getQualityBadge(lead.lead_quality)}`}>
                      {lead.lead_quality}
                    </span>
                  )}
                </div>
               </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {lead.has_website ? (
                  <a href={lead.website} target="_blank" rel="noopener noreferrer" className="text-green-600 hover:text-green-800">
                    ✓ Visit
                  </a>
                ) : (
                  <span className="text-red-600 font-semibold">⚠️ No Website</span>
                )}
               </td>
              <td className="px-6 py-4 text-sm">
                <div className="flex flex-wrap gap-1">
                  {lead.needs_website && <span className="px-1 py-0.5 bg-red-100 text-red-800 text-xs rounded">Website</span>}
                  {lead.needs_seo && <span className="px-1 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded">SEO</span>}
                  {lead.needs_digital_marketing && <span className="px-1 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">Marketing</span>}
                </div>
               </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button
                  onClick={() => console.log('View details', lead.id)}
                  className="text-blue-600 hover:text-blue-900 dark:text-blue-400 mr-3"
                >
                  View
                </button>
                <button
                  onClick={() => console.log('Edit notes', lead.id)}
                  className="text-gray-600 hover:text-gray-900 dark:text-gray-400"
                >
                  Notes
                </button>
               </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {filteredLeads.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No leads found matching your filters
        </div>
      )}
    </div>
  );
}

export default LeadTable;