'use client'

import React, { useState, useEffect } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Typography,
  Grid,
  Alert,
} from '@mui/material'

interface TradingStatus {
  is_active: boolean
  current_position: any
  last_trade_time: string
  pnl: number
}

interface AutomatedTradingConfig {
  position_size: number
  max_loss_percent: number
  is_active: boolean
}

const AutomatedTrading: React.FC = () => {
  const [config, setConfig] = useState<AutomatedTradingConfig>({
    position_size: 0.1,
    max_loss_percent: 0.02,
    is_active: false,
  })

  const [status, setStatus] = useState<TradingStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/automated-trading/status')
        if (!response.ok) throw new Error('Failed to fetch trading status')
        const data = await response.json()
        setStatus(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch status')
      }
    }

    // Fetch initial status and then every 5 seconds
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleConfigSubmit = async () => {
    try {
      const response = await fetch('/api/automated-trading/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })

      if (!response.ok) throw new Error('Failed to update trading configuration')
      const data = await response.json()
      setConfig(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update configuration')
    }
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          Automated Trading
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography gutterBottom>Position Size (% of buying power)</Typography>
            <Slider
              value={config.position_size * 100}
              onChange={(_, value) =>
                setConfig({ ...config, position_size: (value as number) / 100 })
              }
              min={1}
              max={100}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => `${value}%`}
            />

            <Typography gutterBottom>Max Loss Percent</Typography>
            <Slider
              value={config.max_loss_percent * 100}
              onChange={(_, value) =>
                setConfig({ ...config, max_loss_percent: (value as number) / 100 })
              }
              min={0.1}
              max={10}
              step={0.1}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => `${value}%`}
            />

            <Button
              variant="contained"
              color={config.is_active ? "error" : "primary"}
              onClick={() => {
                setConfig({ ...config, is_active: !config.is_active })
                handleConfigSubmit()
              }}
              sx={{ mt: 2 }}
            >
              {config.is_active ? "Stop Trading" : "Start Trading"}
            </Button>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              Trading Status
            </Typography>
            {status && (
              <Box>
                <Typography>
                  Status: {status.is_active ? "Active" : "Inactive"}
                </Typography>
                {status.current_position && (
                  <Typography>
                    Current Position: {JSON.stringify(status.current_position)}
                  </Typography>
                )}
                {status.last_trade_time && (
                  <Typography>
                    Last Trade: {new Date(status.last_trade_time).toLocaleString()}
                  </Typography>
                )}
                <Typography>
                  P&L: ${status.pnl.toFixed(2)}
                </Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
}

export default AutomatedTrading 