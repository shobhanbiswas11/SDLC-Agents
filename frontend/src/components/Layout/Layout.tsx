import React from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useAppSelector } from '@/hooks';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { darkMode } = useAppSelector((state) => state.ui);

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-white dark:bg-gray-950 transition-colors">
        <Header />
        <div className="flex">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <div className="p-4 sm:p-6 lg:p-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};
