import React, { useEffect, useRef } from 'react';

function LogViewer({ logs }) {
  const logContainerRef = useRef(null);
  
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);
  
  const getLogColor = (level) => {
    switch(level) {
      case 'ERROR': return 'text-red-600 dark:text-red-400';
      case 'WARNING': return 'text-yellow-600 dark:text-yellow-400';
      case 'SUCCESS': return 'text-green-600 dark:text-green-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };
  
  return (
    <div className="mt-4">
      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
        Live Logs
      </h4>
      <div
        ref={logContainerRef}
        className="bg-gray-900 text-gray-100 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs"
      >
        {logs.length === 0 ? (
          <p className="text-gray-500">Waiting for discovery to start...</p>
        ) : (
          logs.map((log, index) => {
            const match = log.match(/(\d{4}-\d{2}-\d{2}[\s\S]*?) - (ERROR|WARNING|INFO|SUCCESS): (.*)/);
            if (match) {
              return (
                <div key={index} className="mb-1">
                  <span className="text-gray-500">{match[1]}</span>
                  <span className={`ml-2 ${getLogColor(match[2])}`}>
                    [{match[2]}]
                  </span>
                  <span className="ml-2">{match[3]}</span>
                </div>
              );
            }
            return <div key={index} className="mb-1">{log}</div>;
          })
        )}
      </div>
    </div>
  );
}

export default LogViewer;