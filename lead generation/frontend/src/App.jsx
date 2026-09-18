import React, { useState } from 'react';
import Dashboard from './pages/Dashboard';
import Leads from './pages/Leads';
import Settings from './pages/Settings';
import { ThemeProvider } from './context/ThemeContext';
import { SocketProvider } from './context/SocketContext';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  
  return (
    <ThemeProvider>
      <SocketProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          {/* Navigation Bar */}
          <nav className="bg-white dark:bg-gray-800 shadow-lg sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <div className="flex-shrink-0 flex items-center">
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                      🎯 LeadGen AI Platform
                    </h1>
                  </div>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <button
                      onClick={() => setCurrentPage('dashboard')}
                      className={`${
                        currentPage === 'dashboard'
                          ? 'border-blue-500 text-gray-900 dark:text-white'
                          : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
                    >
                      Dashboard
                    </button>
                    <button
                      onClick={() => setCurrentPage('leads')}
                      className={`${
                        currentPage === 'leads'
                          ? 'border-blue-500 text-gray-900 dark:text-white'
                          : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
                    >
                      Leads Database
                    </button>
                    <button
                      onClick={() => setCurrentPage('settings')}
                      className={`${
                        currentPage === 'settings'
                          ? 'border-blue-500 text-gray-900 dark:text-white'
                          : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
                    >
                      Settings
                    </button>
                  </div>
                </div>
                
                {/* Theme Toggle */}
                <div className="flex items-center">
                  <button
                    onClick={() => {
                      const isDark = document.documentElement.classList.contains('dark');
                      if (isDark) {
                        document.documentElement.classList.remove('dark');
                      } else {
                        document.documentElement.classList.add('dark');
                      }
                    }}
                    className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700"
                  >
                    🌓
                  </button>
                </div>
              </div>
            </div>
          </nav>
          
          {/* Main Content */}
          <main className="py-10">
            <div className="max-w-7xl mx-auto sm:px-6 lg:px-8">
              {currentPage === 'dashboard' && <Dashboard />}
              {currentPage === 'leads' && <Leads />}
              {currentPage === 'settings' && <Settings />}
            </div>
          </main>
        </div>
      </SocketProvider>
    </ThemeProvider>
  );
}

export default App;