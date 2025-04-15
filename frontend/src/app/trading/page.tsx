'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getCookie } from 'cookies-next'
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { toast } from 'sonner'

interface MarketData {
  symbol: string
  price: number
  change: number
  changePercent: number
  volume: number
}

interface OrderForm {
  symbol: string
  quantity: number | string // Allow string for input field, convert later
  orderType: 'buy' | 'sell'
}

interface PortfolioData {
    balance: number;
    // Include other fields if your API returns them
}

interface Position {
  id: number;
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  status: string;
  entry_time: string;
  last_updated: string;
  additional_data?: Record<string, any> | null;
  pnl?: number;
}

// Example static market data - Replace with actual fetched data
const staticMarketData: MarketData[] = [
  { symbol: 'AAPL', price: 175.20, change: 1.50, changePercent: 0.86, volume: 55000000 },
  { symbol: 'GOOGL', price: 140.10, change: -0.80, changePercent: -0.57, volume: 22000000 },
  { symbol: 'MSFT', price: 330.50, change: 2.10, changePercent: 0.64, volume: 30000000 },
];

export default function TradingPage() {
  const router = useRouter()
  // Initialize marketData with static data or empty array if fetching immediately
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [marketData, _setMarketData] = useState<MarketData[]>(staticMarketData)
  const [loading, setLoading] = useState(false)
  const [submitLoading, setSubmitLoading] = useState(false);
  const [error, setError] = useState('')
  const [orderForm, setOrderForm] = useState<OrderForm>({
    symbol: '',
    quantity: '', // Start quantity as empty string
    orderType: 'buy'
  })
  const [balance, setBalance] = useState(0)
  const [positions, setPositions] = useState<Position[]>([])

  useEffect(() => {
    const token = getCookie('token')
    if (!token) {
      router.push('/login')
      return
    }

    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        // Fetch market data (replace with actual API call if needed)
        // const marketResponse = await fetch('http://localhost:3001/api/market-data', { headers: { 'Authorization': `Bearer ${token}` }})
        // if (!marketResponse.ok) throw new Error('Failed to fetch market data')
        // const fetchedMarketData = await marketResponse.json()
        // setMarketData(fetchedMarketData) // Uncomment to use fetched data

        // Fetch user balance from the main backend
        // Updated URL to port 8000 and new endpoint
        const balanceResponse = await fetch('http://localhost:8000/api/portfolio/balance', { 
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!balanceResponse.ok) throw new Error('Failed to fetch balance');
        const portfolioData = await balanceResponse.json(); 
        setBalance(portfolioData.balance ?? 0); // Use nullish coalescing for default

        // Fetch positions from the main backend (URL was already correct)
        const positionsResponse = await fetch('http://localhost:8000/api/positions', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!positionsResponse.ok) {
          let errorDetail = 'Failed to fetch positions';
          try {
              const errorData = await positionsResponse.json();
              errorDetail = errorData.detail || errorDetail;
          } catch {}
          throw new Error(`${positionsResponse.status}: ${errorDetail}`);
        }

        const data = await positionsResponse.json();
        setPositions(data);

      } catch (err: any) {
        console.error("Error fetching trading data:", err);
        setError(err.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setOrderForm(prev => ({
      ...prev,
      [name]: name === 'symbol' ? value.toUpperCase() : value // Uppercase symbol
    }));
  };

  const handleOrderTypeChange = (value: string) => {
    if (value === 'buy' || value === 'sell') { // Ensure value is valid
      setOrderForm(prev => ({
        ...prev,
        orderType: value
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitLoading(true);

    // Validate quantity
    const quantityNum = Number(orderForm.quantity);
    if (isNaN(quantityNum) || quantityNum <= 0) {
        setError('Please enter a valid positive quantity.');
        setSubmitLoading(false);
        return;
    }
    if (!orderForm.symbol) {
        setError('Please select a symbol.');
        setSubmitLoading(false);
        return;
    }

    try {
      const token = getCookie('token');
      const response = await fetch('http://localhost:8000/place-order', { 
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            symbol: orderForm.symbol,
            quantity: quantityNum,
            side: orderForm.orderType
        })
      });

      if (!response.ok) {
        let errorDetail = 'Failed to place order';
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
        } catch {}
        throw new Error(`Failed to place order: ${response.status} - ${errorDetail}`);
      }

      toast.success(`Order placed successfully!`);
      setOrderForm({ symbol: '', quantity: '', orderType: 'buy' });

      try {
           const balanceResponse = await fetch('http://localhost:8000/api/portfolio/balance', { headers: { 'Authorization': `Bearer ${token}` } });
           if (balanceResponse.ok) {
               const portfolioData = await balanceResponse.json();
               setBalance(portfolioData.balance ?? 0);
           }
       } catch (balanceError: any) {
           console.error("Failed to refresh balance after order:", balanceError);
       }
      const positionsResponse = await fetch('http://localhost:8000/api/positions', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!positionsResponse.ok) {
          let errorDetail = 'Failed to fetch updated positions';
          try {
              const errorData = await positionsResponse.json();
              errorDetail = errorData.detail || errorDetail;
          } catch {}
          throw new Error(`${positionsResponse.status}: ${errorDetail}`);
      }
      const data = await positionsResponse.json();
      setPositions(data);

    } catch (err: any) {
      console.error("Error placing order:", err);
      setError(err.message || 'Failed to place order');
      toast.error(err.message || 'Failed to place order');
    } finally {
      setSubmitLoading(false);
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  // Show loading spinner only on initial data fetch
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
                <Link href="/trading" className="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">Trading</Link>
                <Link href="/history" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">History</Link>
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-gray-700 mr-4">Balance: ${balance.toFixed(2)}</span>
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Order Form */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Place Trade</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                     <label className="text-sm font-medium">
                        Action
                      </label>
                     <ToggleGroup 
                        type="single" 
                        variant="outline" 
                        value={orderForm.orderType} 
                        onValueChange={handleOrderTypeChange}
                        className="grid grid-cols-2"
                      >
                        <ToggleGroupItem value="buy" aria-label="Select Buy">
                          Buy
                        </ToggleGroupItem>
                        <ToggleGroupItem value="sell" aria-label="Select Sell">
                          Sell
                        </ToggleGroupItem>
                      </ToggleGroup>
                   </div>

                  <div className="space-y-2">
                    <label htmlFor="symbol" className="text-sm font-medium">
                      Symbol
                    </label>
                    <Input
                      id="symbol"
                      name="symbol"
                      value={orderForm.symbol}
                      onChange={handleInputChange}
                      required
                      className="w-full"
                      placeholder="e.g., AAPL"
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="quantity" className="text-sm font-medium">
                      Quantity
                    </label>
                    <Input
                      id="quantity"
                      name="quantity"
                      type="number"
                      value={orderForm.quantity}
                      onChange={handleInputChange}
                      required
                      className="w-full"
                      placeholder="e.g., 10"
                    />
                  </div>
                  <Button
                    type="submit"
                    className={`w-full ${orderForm.orderType === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
                    disabled={submitLoading}
                  >
                    {submitLoading ? 'Placing Trade...' : `Place ${orderForm.orderType === 'buy' ? 'Buy' : 'Sell'} Order`}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Update Current Positions Card */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Current Positions</CardTitle>
              </CardHeader>
              <CardContent>
                {positions.length === 0 ? (
                  <div className="text-center text-gray-500 py-4">No open positions.</div>
                ) : (
                  <div className="space-y-4">
                    {positions.map((position) => {
                       // Calculate PnL (ensure current_price and entry_price exist)
                       const entryValue = position.entry_price * position.quantity;
                       const currentValue = position.current_price * position.quantity;
                       // Handle potential division by zero or invalid entry value
                       const pnl = entryValue !== 0 ? currentValue - entryValue : 0;
                       const pnlPercent = entryValue !== 0 ? (pnl / entryValue) * 100 : 0;
                      
                       return (
                          <div
                            key={position.id} // Use position ID as key if available, otherwise symbol
                            className="flex items-center justify-between p-4 bg-gray-50 rounded-lg shadow-sm"
                          >
                            <div>
                              <div className="font-semibold text-lg text-indigo-700">{position.symbol}</div>
                              <div className="text-sm text-gray-600">
                                {position.quantity} shares @ avg ${position.entry_price?.toFixed(2)}
                              </div>
                              <div className="text-xs text-gray-500">
                                Current Price: ${position.current_price?.toFixed(2)}
                              </div>
                            </div>
                            <div className={`text-right ${pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              <div className="font-bold text-lg">${pnl.toFixed(2)}</div>
                              <div className="text-sm">
                                {pnlPercent.toFixed(2)}%
                              </div>
                            </div>
                          </div>
                       );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}