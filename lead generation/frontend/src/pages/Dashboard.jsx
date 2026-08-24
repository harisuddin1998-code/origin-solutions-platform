// frontend/src/pages/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import SearchForm from '../components/SearchForm';
import ProgressBar from '../components/ProgressBar';
import LogViewer from '../components/LogViewer';
import LeadTable from '../components/LeadTable';
import { useSocket } from '../context/SocketContext';
import api from '../services/api';

function Dashboard() {
  const [searchActive, setSearchActive] = useState(false);
  const [searchId, setSearchId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [leads, setLeads] = useState([]);
  const [logs, setLogs] = useState([]);
  const socket = useSocket();

  useEffect(() => {
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          setLogs(prev => [...prev, `${data.timestamp} - ${data.level}: ${data.message}`]);
        }
      };
    }
  }, [socket]);

  const handleSearch = async (searchParams) => {
    try {
      setSearchActive(true);
      setLogs([]);
      
      const response = await api.startSearch(searchParams);
      setSearchId(response.search_id);
      
      // Poll for updates
      const interval = setInterval(async () => {
        const status = await api.getSearchStatus(response.search_id);
        setProgress(status.progress);
        
        if (status.status === 'completed') {
          clearInterval(interval);
          setSearchActive(false);
          await loadLeads(response.search_id);
        } else if (status.status === 'failed') {
          clearInterval(interval);
          setSearchActive(false);
          alert('Search failed. Check logs for details.');
        }
      }, 2000);
      
    } catch (error) {
      console.error('Search failed:', error);
      setSearchActive(false);
    }
  };

  const loadLeads = async (searchId) => {
    const response = await api.getLeads({ search_id: searchId });
    setLeads(response.leads);
  };

  const handleExport = async (format) => {
    try {
      const response = await api.exportLeads({
        lead_ids: leads.map(l => l.id),
        format: format
      });
      
      // Download file
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `leads_export.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">
          Business Discovery Engine
        </h2>
        <SearchForm onSearch={handleSearch} isLoading={searchActive} />
      </div>
      
      {searchActive && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
            Search Progress
          </h3>
          <ProgressBar progress={progress} />
          <LogViewer logs={logs} />
        </div>
      )}
      
      {leads.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Discovered Leads ({leads.length})
            </h3>
            <div className="space-x-2">
              <button
                onClick={() => handleExport('excel')}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Export Excel
              </button>
              <button
                onClick={() => handleExport('csv')}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Export CSV
              </button>
              <button
                onClick={() => handleExport('json')}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Export JSON
              </button>
            </div>
          </div>
          <LeadTable leads={leads} />
        </div>
      )}
    </div>
  );
}

export default Dashboard;