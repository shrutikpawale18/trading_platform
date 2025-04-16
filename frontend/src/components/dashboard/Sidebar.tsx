'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  HomeIcon, 
  ChartBarIcon, 
  CogIcon, 
  UserIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Algorithms', href: '/algorithms', icon: ChartBarIcon },
  { name: 'Positions', href: '/positions', icon: CurrencyDollarIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
  { name: 'Profile', href: '/profile', icon: UserIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
      <div className="flex flex-col flex-grow bg-white pt-5 pb-4 overflow-y-auto">
        <div className="flex items-center flex-shrink-0 px-4">
          <h1 className="text-2xl font-bold text-gray-900">Trading Algo</h1>
        </div>
        <nav className="mt-5 flex-1 flex flex-col divide-y divide-gray-200 overflow-y-auto">
          <div className="px-2 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                    isActive
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <item.icon
                    className={`mr-3 flex-shrink-0 h-6 w-6 ${
                      isActive ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500'
                    }`}
                    aria-hidden="true"
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
} 