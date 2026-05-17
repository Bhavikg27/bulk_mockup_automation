import React, { useEffect, useState } from 'react';
import { getJobs, getMockups, getImageUrl } from '../services/api';
import { Link } from 'react-router-dom';
import { Plus, ArrowRight, Activity, Image as ImageIcon, Sparkles } from 'lucide-react';

const Dashboard = () => {
  const [mockups, setMockups] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMockups();
  }, []);

  const fetchMockups = async () => {
    try {
      const [data, recentJobs] = await Promise.all([getMockups(), getJobs(6)]);
      setMockups(data);
      setJobs(recentJobs);
    } catch (error) {
      console.error("Failed to load mockups", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-[#454036]">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-[#625F59]">Mockup Studio V2</p>
          <h1 className="relative z-10 text-4xl font-bold tracking-tight text-[#201F1D]">
            Production dashboard
          </h1>
          <p className="relative z-10 mt-2 text-base text-[#625F59]">Build mockups, optimize WebP, and watch real batch progress.</p>
        </div>
        <Link
          to="/editor/new"
          className="btn-primary flex items-center"
        >
          <Plus className="mr-2 size-5" />
          New Mockup
        </Link>
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-3">
        <div className="rounded-[15px] border border-stone-300 bg-[#DBD1C0] p-4">
          <ImageIcon className="mb-3 size-5 text-[#625F59]" />
          <p className="text-3xl font-bold tabular-nums text-[#201F1D]">{mockups.length}</p>
          <p className="text-sm text-[#625F59]">Templates calibrated</p>
        </div>
        <div className="rounded-[15px] border border-stone-300 bg-[#DBD1C0] p-4">
          <Activity className="mb-3 size-5 text-[#625F59]" />
          <p className="text-3xl font-bold tabular-nums text-[#201F1D]">{jobs.filter((job) => job.status === 'running').length}</p>
          <p className="text-sm text-[#625F59]">Jobs running</p>
        </div>
        <Link to="/optimizer" className="rounded-[15px] border border-stone-300 bg-[#0F0F10] p-4 text-white">
          <Sparkles className="mb-3 size-5" />
          <p className="text-xl font-bold">Optimizer</p>
          <p className="text-sm text-white/70">Convert and downsize images</p>
        </Link>
      </div>

      {!!jobs.length && (
        <div className="mb-8 rounded-[15px] border border-stone-300 bg-[#ECE9E0]">
          <div className="border-b border-stone-300 px-4 py-3 text-sm font-semibold text-[#201F1D]">Recent jobs</div>
          {jobs.map((job) => (
            <div key={job.id} className="grid grid-cols-[1fr_auto_auto] gap-3 border-b border-stone-200 px-4 py-3 text-sm last:border-b-0">
              <span className="font-medium">{job.kind.replace('_', ' ')}</span>
              <span className="text-[#625F59]">{job.status}</span>
              <span className="font-mono tabular-nums">{job.percent}%</span>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-80 rounded-[15px] border border-stone-300 bg-[#DBD1C0]"></div>
          ))}
        </div>
      ) : mockups.length === 0 ? (
        <div className="rounded-[15px] border border-dashed border-stone-400 bg-[#ECE9E0] py-24 text-center">
          <h3 className="text-xl font-medium text-[#201F1D]">No mockups yet</h3>
          <p className="mt-2 text-[#625F59]">Upload a base image to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {mockups.map((mockup) => (
            <div
              key={mockup.id}
              className="glass-panel group relative overflow-hidden rounded-[15px]"
            >
              <div className="h-64 overflow-hidden relative">
                <img
                  src={getImageUrl(`/mockups/${mockup.name}`)}
                  alt={mockup.name}
                  className="h-full w-full object-cover transition-transform duration-150 group-hover:scale-[1.02]"
                />
                <div className="absolute inset-0 bg-black/45 opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
                <Link
                  to={`/editor/${mockup.id}`}
                  className="absolute inset-0 flex items-center justify-center opacity-0 transition-opacity duration-150 group-hover:opacity-100"
                >
                  <span className="rounded-[3px] bg-white px-5 py-2 text-sm font-medium text-[#201F1D]">
                    Configure
                  </span>
                </Link>
              </div>
              <div className="p-6 relative">
                <div className="pointer-events-none absolute -top-9 right-4 flex size-10 items-center justify-center rounded-[3px] border border-stone-300 bg-[#ECE9E0] opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                  <ArrowRight className="size-5 text-[#625F59]" />
                </div>
                <h3 className="truncate text-xl font-bold text-[#201F1D]" title={mockup.name}>{mockup.name}</h3>
                <div className="mt-4 flex items-center justify-between border-t border-stone-300 pt-4">
                  <div className="font-mono text-xs tracking-wide text-[#625F59]">ID: {mockup.id.substring(0, 8)}...</div>
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
