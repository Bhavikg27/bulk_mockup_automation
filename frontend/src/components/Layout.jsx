import React from 'react';
import Sidebar from './Sidebar';
import { Outlet, useLocation } from 'react-router-dom';
// import { AnimatePresence, motion } from 'framer-motion';

const Layout = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-background text-zinc-100 selection:bg-primary/30 font-sans relative">
      {/* Ambient Background */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] animate-float opacity-40"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-secondary/20 rounded-full blur-[120px] animate-float opacity-40 delay-1000"></div>
      </div>

      <Sidebar />

      <main className="flex-1 overflow-y-auto relative z-10 scroll-smooth">
        <div className="p-8 max-w-7xl mx-auto h-full min-h-screen">
          <div className="h-full">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Layout;
