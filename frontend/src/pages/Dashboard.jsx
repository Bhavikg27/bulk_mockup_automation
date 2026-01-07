import React, { useEffect, useState } from 'react';
import { getMockups, getImageUrl } from '../services/api';
import { Link } from 'react-router-dom';
import { Plus, ArrowRight } from 'lucide-react';

const Dashboard = () => {
  const [mockups, setMockups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMockups();
  }, []);

  const fetchMockups = async () => {
    try {
      const data = await getMockups();
      setMockups(data);
    } catch (error) {
      console.error("Failed to load mockups", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-slate-400 mt-1">Manage your mockup templates.</p>
        </div>
        <Link 
          to="/editor/new"
          className="bg-primary hover:bg-cyan-400 text-white px-5 py-2.5 rounded-lg flex items-center transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_25px_rgba(6,182,212,0.5)] font-medium"
        >
          <Plus className="w-5 h-5 mr-2" />
          New Mockup
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-72 bg-slate-800/50 rounded-xl animate-pulse border border-white/5"></div>
          ))}
        </div>
      ) : mockups.length === 0 ? (
        <div className="text-center py-20 bg-slate-900/50 backdrop-blur border border-dashed border-slate-700 rounded-xl">
          <h3 className="text-lg font-medium text-white">No mockups yet</h3>
          <p className="text-slate-500 mt-1">Upload a base image to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mockups.map((mockup) => (
            <div key={mockup.id} className="glass-panel rounded-xl overflow-hidden hover:border-primary/30 transition-all duration-300 group relative">
              <div className="h-48 overflow-hidden relative">
                <img 
                  src={getImageUrl(`/mockups/${mockup.name}`)} 
                  alt={mockup.name}
                  className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700" 
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-300" />
                 <Link 
                    to={`/editor/${mockup.id}`}
                    className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                 >
                    <span className="bg-black/50 backdrop-blur-md text-white px-6 py-2 rounded-full border border-white/20 hover:bg-primary hover:border-primary transition-colors font-medium">
                        Configure
                    </span>
                 </Link>
              </div>
              <div className="p-5">
                <h3 className="font-semibold text-lg text-white truncate group-hover:text-primary transition-colors" title={mockup.name}>{mockup.name}</h3>
                <div className="mt-4 flex justify-between items-center border-t border-white/5 pt-4">
                   <div className="text-xs text-slate-500 font-mono">ID: {mockup.id.substring(0,8)}...</div>
                   <Link 
                    to={`/editor/${mockup.id}`}
                    className="text-sm font-medium text-slate-400 hover:text-white flex items-center transition-colors"
                   >
                     Edit <ArrowRight className="w-4 h-4 ml-1" />
                   </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
