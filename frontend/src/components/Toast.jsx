import React, { useEffect, useState } from 'react';
import { CheckCircle, AlertCircle, X } from 'lucide-react';
import clsx from 'clsx';

const Toast = ({ message, type = 'success', onClose, duration = 5000 }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Small delay to trigger animation
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (duration) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        setTimeout(onClose, 300); // Wait for transition out
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(onClose, 300);
  };

  return (
    <div
      className={clsx(
        "fixed top-6 right-6 z-50 flex items-center p-4 rounded-xl shadow-2xl transition-all duration-300 transform",
        type === 'success' 
          ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white border-l-4 border-emerald-200" 
          : "bg-gradient-to-r from-red-500 to-rose-500 text-white border-l-4 border-rose-200",
        isVisible ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"
      )}
    >
      <div className="flex-shrink-0 mr-3">
        {type === 'success' ? (
          <CheckCircle className="w-6 h-6 text-white/90" />
        ) : (
          <AlertCircle className="w-6 h-6 text-white/90" />
        )}
      </div>
      <div className="flex-1 mr-2">
        <p className="font-semibold text-sm">{type === 'success' ? 'Success' : 'Error'}</p>
        <p className="text-sm text-white/90">{message}</p>
      </div>
      <button 
        onClick={handleClose}
        className="p-1 hover:bg-white/20 rounded-full transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default Toast;
