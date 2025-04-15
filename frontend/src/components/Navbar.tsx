import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Navbar: React.FC = () => {
  const { isAuthenticated, logout } = useAuth();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex space-x-8">
            <Link
              to="/"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                isActive('/') ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-700 hover:text-white'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/trading"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                isActive('/trading') ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-700 hover:text-white'
              }`}
            >
              Trading
            </Link>
            <Link
              to="/backups"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                isActive('/backups') ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-700 hover:text-white'
              }`}
            >
              Backups
            </Link>
          </div>
          <div>
            {isAuthenticated ? (
              <button
                onClick={logout}
                className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-700 hover:text-white"
              >
                Logout
              </button>
            ) : (
              <Link
                to="/login"
                className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-700 hover:text-white"
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