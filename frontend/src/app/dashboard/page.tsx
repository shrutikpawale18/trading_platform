'use client'

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, DollarSign, LineChart as LineChartIcon, Power, PowerOff, TrendingUp, Zap } from "lucide-react"
import { Button } from '@/components/ui/button';
import { getCookie } from 'cookies-next';
import { toast } from 'sonner';
import { Badge } from "@/components/ui/badge";

interface DashboardStats {
  user_email: string;
  algorithm_count: number;
  open_position_count: number;
  recent_trade_count: number;
  account_equity: number | null;
  account_buying_power: number | null;
}

// Interface for Trading Status
interface TradingStatusData {
  is_active: boolean;
  // Add other fields if needed later (e.g., config, pnl)
}

// Interface for portfolio history points
interface PortfolioHistoryPointData {
  date: string; 
  equity: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tradingStatus, setTradingStatus] = useState<TradingStatusData | null>(null);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioHistoryPointData[]>([]); // Add state for history
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingStatus, setLoadingStatus] = useState(true); 
  const [loadingHistory, setLoadingHistory] = useState(true); // Add loading state for history
  const [error, setError] = useState('');
  const [isMounted, setIsMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Fetch Dashboard Stats
  const fetchStats = async (token: string) => {
    setLoadingStats(true);
    try {
      const response = await fetch('http://localhost:8000/api/dashboard/stats', { headers: { 'Authorization': `Bearer ${token}` } });
      if (!response.ok) { throw new Error('Failed to fetch dashboard stats'); }
      const data: DashboardStats = await response.json();
      setStats(data);
    } catch (err: any) { 
      console.error("Stats fetch error:", err); 
      if (!error) setError(err.message); // Set error if not already set
      toast.error(err.message || 'Failed to load dashboard stats');
    } finally { setLoadingStats(false); }
  };

  // Fetch Trading Status
  const fetchTradingStatus = async (token: string) => {
    setLoadingStatus(true);
    try {
      const response = await fetch('http://localhost:8000/api/automated-trading/status', { headers: { 'Authorization': `Bearer ${token}` } });
      if (!response.ok) { 
        let errorDetail = 'Failed to fetch trading status';
        if (!error) setError(errorDetail);
        toast.error(errorDetail);
        return;
      }
      const data: TradingStatusData = await response.json();
      setTradingStatus(data);
    } catch (err: any) {
      console.error("Trading status fetch error:", err);
      const errorMsg = err.message || 'Failed to load trading status';
      if (!error) setError(errorMsg);
      toast.error(errorMsg);
    } finally { setLoadingStatus(false); }
  };

  // Add fetch function for portfolio history
  const fetchPortfolioHistory = async (token: string) => {
    setLoadingHistory(true);
    try {
      const response = await fetch('http://localhost:8000/api/portfolio/history', { 
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) { 
        let errorDetail = 'Failed to fetch portfolio history';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch {}
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      const data: PortfolioHistoryPointData[] = await response.json();
      setPortfolioHistory(data);
    } catch (err: any) {
      console.error("Portfolio history fetch error:", err);
      const errorMsg = err.message || 'Failed to load portfolio history';
      if (!error) setError(errorMsg);
      toast.error(errorMsg);
      setPortfolioHistory([]); // Set to empty array on error
    } finally { setLoadingHistory(false); }
  };

  useEffect(() => {
    if (!isMounted) return;
    const token = getCookie('token');
    if (!token) {
      router.push('/login');
      return;
    }
    setError(''); 
    // Fetch all data in parallel
    Promise.all([
      fetchStats(token),
      fetchTradingStatus(token),
      fetchPortfolioHistory(token) // Call history fetch
    ]);
  }, [isMounted, router]);

  // --- Toggle Trading Status --- 
  const handleToggleTrading = async () => {
    const token = getCookie('token');
    if (!token || !tradingStatus) {
        toast.error("Cannot toggle status: Not logged in or status not loaded.");
        return;
    }

    const newStatus = !tradingStatus.is_active;
    const action = newStatus ? "start" : "stop";

    // Define default config when starting (customize as needed)
    const configPayload = newStatus 
      ? { is_active: true, position_size: 0.1, max_loss_percent: 0.05 } 
      : { is_active: false };

    // Add confirmation?
    // if (!confirm(`Are you sure you want to ${action} automated trading?`)) return;

    setLoadingStatus(true); // Use status loading indicator
    try {
        const response = await fetch('http://localhost:8000/api/automated-trading/config', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(configPayload),
        });

        if (!response.ok) {
            let errorDetail = `Failed to ${action} automated trading`;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorDetail;
            } catch { /* Ignore */ }
            throw new Error(`${response.status}: ${errorDetail}`);
        }

        toast.success(`Automated trading ${action}ed successfully.`);
        // Refresh status after successful toggle
        await fetchTradingStatus(token); 

    } catch (err: any) {
        console.error(`Error ${action}ing trading:`, err);
        setError(err.message || `Failed to ${action} trading`);
        toast.error(err.message || `Failed to ${action} trading`);
        setLoadingStatus(false); // Ensure loading stops on error
    }
    // setLoadingStatus(false); // Status is set within fetchTradingStatus
  };

  // Combined Loading Check
  const isLoading = !isMounted || loadingStats || loadingStatus || loadingHistory;

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="flex min-h-screen items-center justify-center text-red-500">Error: {error}</div>;
  }

  if (!stats) {
    return <div className="flex min-h-screen items-center justify-center">No dashboard data available.</div>;
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 max-w-screen-2xl items-center">
          <div className="mr-4 flex">
            <a className="mr-6 flex items-center space-x-2" href="/">
              <span className="font-bold">Trading Platform</span>
            </a>
          </div>
        </div>
      </header>

      <div className="container flex-1 space-y-4 p-8 pt-6">
        <div className="flex items-center justify-between space-y-2">
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-sm text-muted-foreground">Welcome, {stats.user_email}</p>
        </div>

        {/* Stats Overview */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Algorithms</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.algorithm_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.open_position_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Recent Trades (24h)</CardTitle>
              <LineChartIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.recent_trade_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Account Equity</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.account_equity !== null ? `$${stats.account_equity.toFixed(2)}` : 'N/A'}</div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button className="w-full" onClick={() => router.push('/trading')}>
                Start Trading
              </Button>
              <Button className="w-full" onClick={() => router.push('/backups')}>
                Manage Backups
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Buying Power</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.account_buying_power !== null ? `$${stats.account_buying_power.toFixed(2)}` : 'N/A'}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Automated Trading</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
               {tradingStatus ? (
                 <>
                    <div className="flex items-center justify-between">
                       <span className="text-sm font-medium">Status:</span>
                       <Badge variant={tradingStatus.is_active ? "default" : "outline"} className={tradingStatus.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}>
                         {tradingStatus.is_active ? 'Active' : 'Inactive'}
                       </Badge>
                    </div>
                    <Button 
                       className={`w-full flex items-center justify-center ${tradingStatus.is_active ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}
                       onClick={handleToggleTrading}
                       disabled={loadingStatus} // Disable button while toggling
                    >
                      {tradingStatus.is_active ? <PowerOff className="mr-2 h-4 w-4"/> : <Power className="mr-2 h-4 w-4"/>}
                      {loadingStatus ? 'Updating...' : (tradingStatus.is_active ? 'Stop Trading' : 'Start Trading')}
                    </Button>
                 </>
               ) : (
                 <div className="text-center text-gray-500">Trading status unavailable.</div>
               )}
            </CardContent>
          </Card>
        </div>

        {/* Charts and Analysis */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Portfolio Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart 
                  data={portfolioHistory} 
                  margin={{
                    top: 5, right: 30, left: 20, bottom: 5,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis 
                     domain={['dataMin - 500', 'dataMax + 500']} 
                     tickFormatter={(value) => `$${value}`}
                     allowDataOverflow={true}
                  />
                  <Tooltip 
                     formatter={(value: number) => [`$${value.toFixed(2)}`, "Equity"]}
                  />
                  <Legend />
                  <Line 
                     type="monotone" 
                     dataKey="equity" 
                     stroke="#8884d8" 
                     activeDot={{ r: 8 }} 
                     strokeWidth={2}
                     dot={false} // Hide dots for cleaner look with more data
                  />
                </LineChart>
              </ResponsiveContainer>
               {loadingHistory && <div className="text-center text-sm text-gray-500 pt-2">Loading history...</div>}
              {portfolioHistory.length === 0 && !loadingHistory && <div className="text-center text-sm text-gray-500 pt-2">No portfolio history data available.</div>}
            </CardContent>
          </Card>
          <Card className="col-span-3">
            <CardHeader>
              <CardTitle>Recent Trades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                  Recent trades list coming soon...
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Active Algorithms */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Active Trading Algorithms</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex h-[100px] items-center justify-center text-muted-foreground">
                  Algorithm list coming soon...
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="col-span-3">
            <CardHeader>
              <CardTitle>Risk Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex h-[100px] items-center justify-center text-muted-foreground">
                  Risk analysis coming soon...
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}