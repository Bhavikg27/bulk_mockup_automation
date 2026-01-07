import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, Image as ImageIcon } from 'lucide-react';
import { clsx } from 'clsx';

const Sidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'New Mockup', path: '/editor/new', icon: PlusCircle },
    { name: 'Gallery', path: '/gallery', icon: ImageIcon },
  ];

  return (
    <div className="h-screen w-64 bg-slate-900/50 backdrop-blur-xl border-r border-white/5 flex flex-col shadow-2xl relative z-10">
      <div className="p-6 border-b border-white/5">
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-400 drop-shadow-sm">
          MockupGen
        </h1>
        <p className="text-xs text-slate-500 mt-1 uppercase tracking-wider font-semibold">Premium Studio</p>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-all duration-300 border border-transparent',
                isActive
                  ? 'bg-primary/10 text-primary border-primary/20 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white hover:border-white/5'
              )
            }
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-white/5">
        <div className="bg-gradient-to-br from-indigo-900/50 to-slate-900/50 backdrop-blur border border-white/10 rounded-lg p-4 text-white relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
            <LayoutDashboard className="w-12 h-12" />
          </div>
          <p className="text-xs font-bold text-primary mb-1 uppercase tracking-wider">Pro Tip</p>
          <p className="text-xs text-slate-300 leading-relaxed">Drag dots to adjust perspective perfectly.</p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
