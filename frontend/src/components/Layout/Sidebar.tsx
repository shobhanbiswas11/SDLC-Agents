import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAppSelector } from '@/hooks';

const NAVIGATION_ITEMS = [
  { href: '/', label: 'Dashboard', icon: '📊' },
  { href: '/agents', label: 'All Agents', icon: '🧠' },
  { href: '/dependency-resolver', label: 'Dependency Resolver', icon: '📦' },
  { href: '/text-processing', label: 'Text Processing', icon: '📝' },
  { href: '/data-analysis', label: 'Data Analysis', icon: '📈' },
  { href: '/code-generation', label: 'Code Generation', icon: '⚙️' },
  { href: '/image-processing', label: 'Image Processing', icon: '🖼️' },
  { href: '/translation', label: 'Translation', icon: '🌐' },
  { href: '/execution-history', label: 'History', icon: '⏱️' },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const { sidebarOpen } = useAppSelector((state) => state.ui);

  return (
    <aside
      className={`${
        sidebarOpen ? 'w-64' : 'w-0'
      } bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 overflow-hidden`}
    >
      <nav className="flex flex-col gap-2 p-4">
        {NAVIGATION_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
                isActive
                  ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 font-semibold'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="text-sm whitespace-nowrap">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
};
