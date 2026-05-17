import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, Image as ImageIcon, Sparkles } from 'lucide-react';
import { clsx } from 'clsx';

const Sidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'New Mockup', path: '/editor/new', icon: PlusCircle },
    { name: 'Optimizer', path: '/optimizer', icon: Sparkles },
    { name: 'Gallery', path: '/gallery', icon: ImageIcon },
  ];

  return (
    <div className="relative z-10 flex h-dvh w-64 flex-col border-r border-stone-300 bg-[#DBD1C0] text-[#454036] shadow-sm">
      <div className="border-b border-stone-300 p-5">
        <h1 className="text-2xl font-bold text-[#201F1D]">
          MockupGen
        </h1>
        <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-[#625F59]">Production Studio</p>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'mx-2 my-1 flex items-center rounded-[3px] border border-transparent px-4 py-3 text-sm font-medium transition-colors',
                isActive
                  ? 'border-stone-500 bg-[#0F0F10] text-white'
                  : 'text-[#625F59] hover:border-stone-300 hover:bg-[#ECE9E0] hover:text-[#201F1D]'
              )
            }
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-stone-300 p-4">
        <div className="rounded-[15px] border border-stone-300 bg-[#ECE9E0] p-4">
          <p className="mb-1 text-xs font-bold uppercase tracking-wide text-[#625F59]">Live feedback</p>
          <p className="text-xs leading-relaxed text-[#454036]">Bulk jobs now report backend stage, file, and real percent.</p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
