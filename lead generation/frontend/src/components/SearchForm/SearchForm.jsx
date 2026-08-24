import React, { useState } from 'react';

function SearchForm({ onSearch, isLoading }) {
  const [formData, setFormData] = useState({
    country: '',
    city: '',
    keywords: '',
    platforms: {
      google_maps: true,
      facebook: true,
      instagram: true,
      yelp: true,
      yellow_pages: true,
      linkedin: true
    }
  });
  
  const countries = [
    'United States', 'Canada', 'United Kingdom', 'Australia', 'Germany',
    'France', 'Spain', 'Italy', 'Netherlands', 'Singapore', 'India'
  ];
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.country && formData.city) {
      onSearch(formData);
    } else {
      alert('Please select country and enter city/area');
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Country *
          </label>
          <select
            value={formData.country}
            onChange={(e) => setFormData({...formData, country: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            required
          >
            <option value="">Select Country</option>
            {countries.map(country => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            City/Area *
          </label>
          <input
            type="text"
            value={formData.city}
            onChange={(e) => setFormData({...formData, city: e.target.value})}
            placeholder="e.g., New York, Manhattan, Brooklyn"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            required
          />
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Keywords (Optional)
        </label>
        <input
          type="text"
          value={formData.keywords}
          onChange={(e) => setFormData({...formData, keywords: e.target.value})}
          placeholder="e.g., Restaurants, Plumbers, or leave empty for 'All Businesses'"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
        />
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Leave empty to discover ALL businesses in the area
        </p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Search Platforms
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {Object.entries(formData.platforms).map(([platform, enabled]) => (
            <label key={platform} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setFormData({
                  ...formData,
                  platforms: {...formData.platforms, [platform]: e.target.checked}
                })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {platform.replace('_', ' ').toUpperCase()}
              </span>
            </label>
          ))}
        </div>
      </div>
      
      <button
        type="submit"
        disabled={isLoading}
        className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Searching...' : '🔍 Start Business Discovery'}
      </button>
    </form>
  );
}

export default SearchForm;