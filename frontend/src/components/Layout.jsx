import React from 'react';
import Sidebar from './Sidebar';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';

const Layout = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-canvas)] selection:bg-primary/30">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto h-full">
            <AnimatePresence mode="wait">
                <motion.div
                    key={location.pathname}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="h-full"
                >
                    <Outlet />
                </motion.div>
            </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default Layout;
