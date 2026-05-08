import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'Dependency Resolver Agent',
  description: 'AI-powered dependency conflict resolver with Human-in-the-Loop approval.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-white text-gray-900 antialiased h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
