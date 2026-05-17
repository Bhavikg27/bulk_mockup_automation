import React from 'react';
import Sidebar from './Sidebar';
import { Outlet } from 'react-router-dom';

const Layout = () => {
  return (
    <div className="relative flex h-dvh overflow-hidden bg-[#ECE9E0] font-sans text-[#454036] selection:bg-[#DBD1C0]">
      <Sidebar />

      <main className="relative z-10 flex-1 overflow-y-auto scroll-smooth">
        <div className="mx-auto h-full min-h-dvh max-w-7xl p-6 lg:p-8">
          <div className="h-full">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Layout;
