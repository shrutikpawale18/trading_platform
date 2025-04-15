'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Trash2, PlusCircle, ToggleLeft, ToggleRight } from "lucide-react"
import { toast } from 'sonner'
import { Badge } from "@/components/ui/badge"

// Interface matching backend's AlgorithmRead
interface Algorithm {
  id: number;
  user_id: string;
  symbol: string;
  type: string; // Enum as string
  parameters: Record<string, any>; // Dictionary/JSON
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function AlgorithmsPage() {
  const router = useRouter();
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // --- Fetch Algorithms --- 
  const fetchAlgorithms = async () => {
    setLoading(true);
    setError('');
    const token = getCookie('token');
    if (!token) {
      router.push('/login');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/algorithms', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        let errorDetail = 'Failed to fetch algorithms';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch { /* Ignore */ }
        throw new Error(`${response.status}: ${errorDetail}`);
      }

      const data: Algorithm[] = await response.json();
      setAlgorithms(data);
    } catch (err: any) {
      console.error("Error fetching algorithms:", err);
      setError(err.message || 'Failed to load algorithms');
      toast.error(err.message || 'Failed to load algorithms');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlgorithms();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Remove router dependency if only needed for token check

  // --- Toggle Algorithm Status --- 
  const handleToggleStatus = async (algorithm: Algorithm) => {
    const token = getCookie('token');
    if (!token) {
      router.push('/login');
      return;
    }
    
    const newStatus = !algorithm.is_active;
    const action = newStatus ? 'activate' : 'deactivate';

    if (!confirm(`Are you sure you want to ${action} the ${algorithm.type} algorithm for ${algorithm.symbol}?`)) {
        return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/algorithms/${algorithm.id}/status`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json', 
        },
        body: JSON.stringify({ is_active: newStatus }),
      });

      if (!response.ok) {
        let errorDetail = `Failed to ${action} algorithm`;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch { /* Ignore */ }
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      
      toast.success(`Algorithm ${action}d successfully`);
      fetchAlgorithms(); // Refresh list

    } catch (err: any) {
      console.error(`Error ${action}ing algorithm:`, err);
      setError(err.message || `Failed to ${action} algorithm`);
      toast.error(err.message || `Failed to ${action} algorithm`);
    }
  };

  // --- Logout --- 
  const handleLogout = () => {
    const { deleteCookie } = require('cookies-next');
    deleteCookie('token');
    router.push('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-indigo-600">Trading Platform</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link href="/dashboard" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">Dashboard</Link>
                <Link href="/trading" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">Trading</Link>
                <Link href="/history" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">History</Link>
                 <Link href="/algorithms" className="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">Algorithms</Link>
              </div>
            </div>
            <div className="flex items-center">
              <button onClick={handleLogout} className="ml-4 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Error:</strong>
            <span className="block sm:inline"> {error}</span>
          </div>
        )}

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">Manage Algorithms</h2>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Your Algorithms</CardTitle>
          </CardHeader>
          <CardContent>
            {algorithms.length === 0 && !loading ? (
              <div className="text-center text-gray-500 py-4">No algorithms found for this user.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Parameters</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {algorithms.map((algo) => (
                    <TableRow key={algo.id}>
                      <TableCell>{algo.id}</TableCell>
                      <TableCell className="font-medium">{algo.symbol}</TableCell>
                      <TableCell>{algo.type}</TableCell>
                      <TableCell>
                          <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">{JSON.stringify(algo.parameters, null, 2)}</pre>
                      </TableCell>
                      <TableCell>
                        <Badge variant={algo.is_active ? "default" : "outline"} className={algo.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}>
                          {algo.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>{new Date(algo.created_at).toLocaleString()}</TableCell>
                      <TableCell>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => handleToggleStatus(algo)}
                          aria-label={algo.is_active ? "Deactivate algorithm" : "Activate algorithm"}
                          className={`flex items-center ${algo.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'}`}
                        >
                           {algo.is_active ? <ToggleLeft className="mr-2 h-4 w-4"/> : <ToggleRight className="mr-2 h-4 w-4"/>}
                           {algo.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
} 