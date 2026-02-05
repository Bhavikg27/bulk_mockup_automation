import React from 'react';

const ProgressBar = ({ progress }) => {
    return (
        <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mb-4 overflow-hidden">
            <div
                className="bg-primary h-2.5 rounded-full transition-all duration-300 ease-out relative"
                style={{ width: `${progress}%` }}
            >
                <div className="absolute inset-0 bg-white/30 animate-pulse w-full h-full"></div>
            </div>
        </div>
    );
};

export default ProgressBar;
