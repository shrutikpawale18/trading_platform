import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

const Navbar: React.FC = () => {
  const { isAuthenticated, logout } = useAuth();
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path;

  return (
    <nav className="bg-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex space-x-8">
            <Link
              href="/dashboard"
              className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/dashboard') ? 'text-indigo-600 font-semibold' : 'text-gray-700 hover:text-indigo-600'}`}
            >
              Dashboard
            </Link>
            <Link
              href="/trading"
              className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/trading') ? 'text-indigo-600 font-semibold' : 'text-gray-700 hover:text-indigo-600'}`}
            >
              Trading
            </Link>
            <Link
              href="/history"
              className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/history') ? 'text-indigo-600 font-semibold' : 'text-gray-700 hover:text-indigo-600'}`}
            >
              History
            </Link>
            <Link
              href="/algorithms"
              className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/algorithms') ? 'text-indigo-600 font-semibold' : 'text-gray-700 hover:text-indigo-600'}`}
            >
              Algorithms
            </Link>
          </div>
          <div>
            {isAuthenticated ? (
              <button
                onClick={logout}
                className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                Logout
              </button>
            ) : (
              <Link
                href="/login"
                className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar; 