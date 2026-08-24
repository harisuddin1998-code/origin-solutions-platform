import React, { useState, useEffect } from 'react';
import api from '../services/api';

function Settings() {
  const [settings, setSettings] = useState({
    notifications: true,
    autoExport: false,
    exportFormat: 'excel',
    darkMode: false,
    scrapingSettings: {
      maxConcurrent: 5,
      requestsPerMinute: 30,
      maxRetries: 3
    }
  });
  
  const [saving, setSaving] = useState(false);
  
  useEffect(() => {
    loadSettings();
  }, []);
  
  const loadSettings = async () => {
    try {
      const response = await api.getSettings();
      setSettings(response);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };
  
  const saveSettings = async () => {
    setSaving(true);
    try {
      await api.updateSettings(settings);
      alert('Settings saved successfully!');
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };
  
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          System Settings
        </h2>
        
        {/* General Settings */}
        <div className="space-y-4 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b pb-2">
            General
          </h3>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700 dark:text-gray-300">Email Notifications</p>
              <p className="text-sm text-gray-500">Receive email alerts for completed searches</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notifications}
                onChange={(e) => setSettings({...settings, notifications: e.target.checked})}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700 dark:text-gray-300">Auto-Export After Search</p>
              <p className="text-sm text-gray-500">Automatically export leads when search completes</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.autoExport}
                onChange={(e) => setSettings({...settings, autoExport: e.target.checked})}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>
          
          <div>
            <label className="block font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Export Format
            </label>
            <select
              value={settings.exportFormat}
              onChange={(e) => setSettings({...settings, exportFormat: e.target.value})}
              className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            >
              <option value="excel">Excel (.xlsx)</option>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
          </div>
        </div>
        
        {/* Scraping Settings */}
        <div className="space-y-4 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b pb-2">
            Scraping Configuration
          </h3>
          
          <div>
            <label className="block font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Concurrent Searches
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={settings.scrapingSettings.maxConcurrent}
              onChange={(e) => setSettings({
                ...settings,
                scrapingSettings: {
                  ...settings.scrapingSettings,
                  maxConcurrent: parseInt(e.target.value)
                }
              })}
              className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
            <p className="text-sm text-gray-500 mt-1">Higher values increase speed but may trigger rate limits</p>
          </div>
          
          <div>
            <label className="block font-medium text-gray-700 dark:text-gray-300 mb-2">
              Requests Per Minute
            </label>
            <input
              type="number"
              min="10"
              max="120"
              value={settings.scrapingSettings.requestsPerMinute}
              onChange={(e) => setSettings({
                ...settings,
                scrapingSettings: {
                  ...settings.scrapingSettings,
                  requestsPerMinute: parseInt(e.target.value)
                }
              })}
              className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
            <p className="text-sm text-gray-500 mt-1">Respect target websites' rate limits</p>
          </div>
          
          <div>
            <label className="block font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Retries on Failure
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={settings.scrapingSettings.maxRetries}
              onChange={(e) => setSettings({
                ...settings,
                scrapingSettings: {
                  ...settings.scrapingSettings,
                  maxRetries: parseInt(e.target.value)
                }
              })}
              className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
        </div>
        
        {/* API Keys */}
        <div className="space-y-4 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b pb-2">
            API Keys (Optional)
          </h3>
          
          <div>
            <label className="block font-medium text-gray-700 dark:text-gray-300 mb-2">
              OpenAI API Key (for AI Outreach)
            </label>
            <input
              type="password"
              placeholder="sk-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
            <p className="text-sm text-gray-500 mt-1">Enables AI-generated personalized outreach emails</p>
          </div>
          
          <div>
            <label className="block font-medium text-gray-700 dark:text-gray-300 mb-2">
              Google Maps API Key
            </label>
            <input
              type="password"
              placeholder="AIza..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
        </div>
        
        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={saveSettings}
            disabled={saving}
            className="btn-primary disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
      
      {/* System Info */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
          System Information
        </h3>
        <div className="space-y-2 text-sm">
          <p><span className="font-medium">Version:</span> 1.0.0</p>
          <p><span className="font-medium">Database:</span> SQLite</p>
          <p><span className="font-medium">Last Backup:</span> {new Date().toLocaleString()}</p>
          <p><span className="font-medium">Total Leads in DB:</span> 0</p>
        </div>
      </div>
    </div>
  );
}

export default Settings;