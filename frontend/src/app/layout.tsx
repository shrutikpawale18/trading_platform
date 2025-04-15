'use client';

import { Inter } from 'next/font/google';
import './globals.css';
import { useRouter } from 'next/navigation';
import { deleteCookie, getCookie } from 'cookies-next';
import Link from 'next/link';
import { AuthProvider } from '@/contexts/AuthContext';
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const token = getCookie('token');

  const handleLogout = () => {
    deleteCookie('token');
    router.push('/');
  };

  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          {token && (
            <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <div className="container flex h-16 items-center">
                <Link href="/" className="flex items-center space-x-2">
                  <span className="text-2xl font-bold text-primary">
                    Trading Platform
                  </span>
                </Link>
                <nav className="ml-auto flex items-center space-x-4">
                  <Link href="/dashboard" className="text-sm font-medium">
                    Dashboard
                  </Link>
                  <Link href="/trading" className="text-sm font-medium">
                    Trading
                  </Link>
                  <Link href="/algorithms" className="text-sm font-medium">
                    Algorithms
                  </Link>
                  <Link href="/backups" className="text-sm font-medium">
                    Backups
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-sm font-medium text-red-500 hover:text-red-700"
                  >
                    Logout
                  </button>
                </nav>
              </div>
            </header>
          )}
          {children}
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  );
} 