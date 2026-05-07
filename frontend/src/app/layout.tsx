import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'Coding Standards Enforcer',
  description:
    'Multi-language AI agent for code-quality enforcement across Python, C++, Java, JS/TS, Go, and Rust.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
