import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI Job Assistant - Enterprise Application & Match Intelligence',
  description: 'Production-quality AI-powered job search, match scoring, and application assistant.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden bg-slate-50 text-slate-900 antialiased">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
