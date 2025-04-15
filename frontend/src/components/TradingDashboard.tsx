'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useApi } from '@/hooks/useApi'
import { useAuth } from '@/contexts/AuthContext'

console.log("TradingDashboard component is being loaded")

interface TradingConfig {
  symbol: string
  timeframe: string
  lookbackDays: number
  shortWindow: number
  longWindow: number
}

export function TradingDashboard() {
  const { fetchWithAuth } = useApi()
  const { isAuthenticated } = useAuth()
  
  const [isAutomatedTrading, setIsAutomatedTrading] = useState(false)
  const [tradingConfig, setTradingConfig] = useState<TradingConfig>({
    symbol: 'AAPL',
    timeframe: '5Min',
    lookbackDays: 2,
    shortWindow: 5,
    longWindow: 13
  })
  const [tradingStatus, setTradingStatus] = useState('Stopped')
  const [lastSignal, setLastSignal] = useState<string | null>(null)
  const [equity, setEquity] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) {
      fetchTradingStatus()
      fetchEquity()

      const statusInterval = setInterval(fetchTradingStatus, 5000)
      const equityInterval = setInterval(fetchEquity, 60000)

      return () => {
        clearInterval(statusInterval)
        clearInterval(equityInterval)
      }
    }
  }, [isAuthenticated])

  const fetchTradingStatus = async () => {
    try {
      const data = await fetchWithAuth('/api/automated-trading/status')
      setTradingStatus(data.is_active ? 'Active' : 'Stopped')
      setLastSignal(data.current_position?.side || 'None')
    } catch (error) {
      console.error('Error fetching trading status:', error)
    }
  }

  const fetchEquity = async () => {
    try {
      const data = await fetchWithAuth('/account-info')
      setEquity(data.equity)
    } catch (error) {
      console.error('Error fetching equity:', error)
    }
  }

  const handleStartTrading = async () => {
    try {
      await fetchWithAuth('/api/automated-trading/config', {
        method: 'POST',
        body: {
          position_size: 0.1,
          max_loss_percent: 0.02,
          is_active: true
        },
      })
      
      setIsAutomatedTrading(true)
      fetchTradingStatus()
    } catch (error) {
      console.error('Error starting automated trading:', error)
    }
  }

  const handleStopTrading = async () => {
    try {
      await fetchWithAuth('/api/automated-trading/config', {
        method: 'POST',
        body: {
          position_size: 0.1,
          max_loss_percent: 0.02,
          is_active: false
        },
      })
      
      setIsAutomatedTrading(false)
      fetchTradingStatus()
    } catch (error) {
      console.error('Error stopping automated trading:', error)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Card>
          <CardContent className="p-6">
            <h2 className="text-2xl font-semibold mb-4">Please Log In</h2>
            <p className="text-muted-foreground">You need to be logged in to access the trading dashboard.</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Trading Dashboard</h1>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="text-2xl font-semibold">Account Overview</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Current Equity</span>
                <span className="font-semibold">${equity || '---'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Trading Status</span>
                <span className={`font-semibold ${tradingStatus === 'Active' ? 'text-green-500' : 'text-red-500'}`}>
                  {tradingStatus}
                </span>
              </div>
              {lastSignal && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Last Signal</span>
                  <span className="font-semibold">{lastSignal}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-2xl font-semibold">Automated Trading</h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Label htmlFor="automated-trading" className="text-lg">Enable Automated Trading</Label>
                <Switch
                  id="automated-trading"
                  checked={isAutomatedTrading}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      handleStartTrading()
                    } else {
                      handleStopTrading()
                    }
                  }}
                />
              </div>

              <div className="grid gap-4">
                <div className="space-y-2">
                  <Label htmlFor="symbol">Symbol</Label>
                  <Input
                    id="symbol"
                    value={tradingConfig.symbol}
                    onChange={(e) => 
                      setTradingConfig({...tradingConfig, symbol: e.target.value})
                    }
                    disabled={isAutomatedTrading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timeframe">Timeframe</Label>
                  <Select
                    value={tradingConfig.timeframe}
                    onValueChange={(value) => 
                      setTradingConfig({...tradingConfig, timeframe: value})
                    }
                    disabled={isAutomatedTrading}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select timeframe" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="5Min">5 Minutes</SelectItem>
                      <SelectItem value="15Min">15 Minutes</SelectItem>
                      <SelectItem value="1H">1 Hour</SelectItem>
                      <SelectItem value="1D">1 Day</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="lookback">Lookback Days</Label>
                  <Input
                    id="lookback"
                    type="number"
                    value={tradingConfig.lookbackDays}
                    onChange={(e) => 
                      setTradingConfig({...tradingConfig, lookbackDays: parseInt(e.target.value)})
                    }
                    disabled={isAutomatedTrading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="short-window">Short Window</Label>
                  <Input
                    id="short-window"
                    type="number"
                    value={tradingConfig.shortWindow}
                    onChange={(e) => 
                      setTradingConfig({...tradingConfig, shortWindow: parseInt(e.target.value)})
                    }
                    disabled={isAutomatedTrading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="long-window">Long Window</Label>
                  <Input
                    id="long-window"
                    type="number"
                    value={tradingConfig.longWindow}
                    onChange={(e) => 
                      setTradingConfig({...tradingConfig, longWindow: parseInt(e.target.value)})
                    }
                    disabled={isAutomatedTrading}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 