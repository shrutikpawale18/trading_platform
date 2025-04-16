'use client';

import React, { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { PortfolioStats } from '@/components/dashboard/PortfolioStats';
import { AlgorithmList } from '@/components/dashboard/AlgorithmList';
import { RecentSignals } from '@/components/dashboard/RecentSignals';
import { PositionList } from '@/components/dashboard/PositionList';
import { AlgorithmResults } from '@/components/dashboard/AlgorithmResults';
import { getCookie } from 'cookies-next';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

interface Algorithm {
  id: number;
  symbol: string;
  type: string;
  is_active: boolean;
  parameters: Record<string, any>;
}

export default function DashboardPage() {
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchAlgorithms = async () => {
    const token = getCookie('token');
    if (!token) {
      toast.error("Authentication required. Redirecting to login...");
      router.push('/login');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/algorithms', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch algorithms');
      }

      const data = await response.json();
      setAlgorithms(data);
    } catch (error) {
      console.error('Error fetching algorithms:', error);
      toast.error('Failed to load algorithms');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlgorithms();
  }, [router]);

  const handleAlgorithmStatusChange = (algorithmId: number, newStatus: boolean) => {
    setAlgorithms(prevAlgorithms => 
      prevAlgorithms.map(algo => 
        algo.id === algorithmId ? { ...algo, is_active: newStatus } : algo
      )
    );
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <PortfolioStats activeAlgorithms={algorithms.filter(a => a.is_active).length} />
        </div>
        
        <div className="grid grid-cols-1 gap-6">
          <AlgorithmResults algorithmId={1} />
        </div>
        
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <AlgorithmList 
            algorithms={algorithms.filter(a => a.is_active)} 
            onAlgorithmStatusChange={handleAlgorithmStatusChange}
          />
          <RecentSignals />
        </div>
        
        <div className="grid grid-cols-1 gap-6">
          <PositionList />
        </div>
      </div>
    </DashboardLayout>
  );
}