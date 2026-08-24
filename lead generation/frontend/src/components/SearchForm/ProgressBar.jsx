import React from 'react';

function ProgressBar({ progress }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
        <span>Discovery Progress</span>
        <span>{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-4 dark:bg-gray-700 overflow-hidden">
        <div
          className="bg-gradient-to-r from-blue-500 to-blue-600 h-4 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        >
          <div className="h-full w-full animate-pulse"></div>
        </div>
      </div>
      {progress === 100 && (
        <p className="text-green-600 dark:text-green-400 text-sm font-semibold">
          ✅ Discovery complete! Found businesses ready for export.
        </p>
      )}
    </div>
  );
}

export default ProgressBar;