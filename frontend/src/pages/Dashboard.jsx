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
      <div className="flex justify-between items-end mb-12">
        <div className="relative">
          <div className="absolute -left-4 -top-4 w-20 h-20 bg-primary/20 rounded-full blur-2xl opacity-50 animate-pulse-glow"></div>
          <h1 className="text-5xl font-display font-bold text-white tracking-tight relative z-10">
            Dashboard
            <span className="text-primary">.</span>
          </h1>
          <p className="text-muted mt-2 text-lg relative z-10 font-light">Manage your mockup templates with style.</p>
        </div>
        <Link
          to="/editor/new"
          className="btn-primary flex items-center group"
        >
          <Plus className="w-5 h-5 mr-2 group-hover:rotate-90 transition-transform duration-300" />
          New Mockup
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-80 bg-zinc-800/30 rounded-2xl animate-pulse border border-white/5"></div>
          ))}
        </div>
      ) : mockups.length === 0 ? (
        <div className="text-center py-32 bg-zinc-900/30 backdrop-blur-sm border border-dashed border-zinc-700 rounded-3xl">
          <h3 className="text-xl font-display font-medium text-white">No mockups yet</h3>
          <p className="text-muted mt-2">Upload a base image to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {mockups.map((mockup, index) => (
            <div
              key={mockup.id}
              className="glass-panel rounded-2xl overflow-hidden hover:border-primary/50 transition-all duration-300 group relative shadow-lg hover:shadow-neon/20 animate-fade-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="h-64 overflow-hidden relative">
                <img
                  src={getImageUrl(`/mockups/${mockup.name}`)}
                  alt={mockup.name}
                  className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-out"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <Link
                  to={`/editor/${mockup.id}`}
                  className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-4 group-hover:translate-y-0"
                >
                  <span className="bg-white/10 backdrop-blur-md text-white px-8 py-3 rounded-full border border-white/20 hover:bg-primary hover:border-primary transition-all duration-300 font-medium shadow-xl hover:shadow-primary/50">
                    Configure
                  </span>
                </Link>
              </div>
              <div className="p-6 relative">
                <div className="absolute -top-10 right-4 w-12 h-12 bg-zinc-900 rounded-full flex items-center justify-center border border-white/10 shadow-xl opacity-0 group-hover:opacity-100 transition-all duration-500 translate-y-4 group-hover:translate-y-0 delay-75 pointer-events-none">
                  <ArrowRight className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-display font-bold text-xl text-white truncate group-hover:text-primary transition-colors" title={mockup.name}>{mockup.name}</h3>
                <div className="mt-4 flex justify-between items-center pt-4 border-t border-white/5">
                  <div className="text-xs text-muted font-mono tracking-wider">ID: {mockup.id.substring(0, 8)}...</div>
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
