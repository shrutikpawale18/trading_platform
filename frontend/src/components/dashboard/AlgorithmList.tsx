'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Play, Pause, Settings } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { getCookie } from 'cookies-next';
import { toast } from 'sonner';

interface Algorithm {
  id: number;
  symbol: string;
  type: string;
  is_active: boolean;
  parameters: Record<string, any>;
}

interface AlgorithmListProps {
  algorithms: Algorithm[];
  onAlgorithmStatusChange?: (algorithmId: number, newStatus: boolean) => void;
}

export function AlgorithmList({ algorithms, onAlgorithmStatusChange }: AlgorithmListProps) {
  const router = useRouter();

  const handleManageClick = () => {
    router.push('/algorithms');
  };

  const handleToggleStatus = async (algorithmId: number, currentStatus: boolean) => {
    const token = getCookie('token');
    if (!token) {
      toast.error("Authentication required.");
      router.push('/login');
      return;
    }

    const action = currentStatus ? 'deactivate' : 'activate';
    
    try {
      const response = await fetch(`http://localhost:8000/api/algorithms/${algorithmId}/status`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (!response.ok) {
        let errorDetail = `Failed to ${action} algorithm`;
        try { 
          const errorData = await response.json(); 
          errorDetail = errorData.detail || errorDetail; 
        } catch {} 
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      
      toast.success(`Algorithm ${action}d successfully`);
      if (onAlgorithmStatusChange) {
        onAlgorithmStatusChange(algorithmId, !currentStatus);
      }

    } catch (err: any) {
      console.error(`Error ${action}ing algorithm ${algorithmId}:`, err);
      toast.error(err.message || `Failed to ${action} algorithm`);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Active Algorithms</CardTitle>
        <Button variant="outline" size="sm" onClick={handleManageClick}>
          <Settings className="mr-2 h-4 w-4" />
          Manage
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {algorithms.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground">
              No active algorithms
            </div>
          ) : (
            algorithms.map((algorithm) => (
              <div
                key={algorithm.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{algorithm.symbol}</span>
                    <Badge variant="outline">{algorithm.type}</Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {Object.entries(algorithm.parameters)
                      .map(([key, value]) => `${key}: ${value}`)
                      .join(', ')}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge
                    variant={algorithm.is_active ? 'default' : 'secondary'}
                    className={algorithm.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
                  >
                    {algorithm.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleToggleStatus(algorithm.id, algorithm.is_active)}
                  >
                    {algorithm.is_active ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
} 