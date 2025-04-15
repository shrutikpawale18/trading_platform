'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useEffect } from 'react';
import { getCookie } from 'cookies-next';

export default function LandingPage() {
  const router = useRouter();
  const token = getCookie('token');

  useEffect(() => {
    if (token) {
      router.push('/dashboard');
    }
  }, [token, router]);

  if (token) {
    return null; // Will redirect to dashboard
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      <div className="container mx-auto px-4 py-16">
        <div className="flex flex-col items-center justify-center text-center space-y-8">
          <h1 className="text-5xl font-bold tracking-tight text-primary">
            Algorithmic Trading Platform
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl">
            Automate your trading strategies with our advanced algorithmic trading platform.
            Backtest, optimize, and deploy your trading algorithms with ease.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Button
              size="lg"
              onClick={() => router.push('/auth/register')}
              className="bg-primary hover:bg-primary/90"
            >
              Get Started
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => router.push('/auth/login')}
            >
              Sign In
            </Button>
          </div>
        </div>

        <div className="mt-32 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-6 rounded-lg border bg-card">
            <h3 className="text-xl font-semibold mb-2">Backtesting</h3>
            <p className="text-muted-foreground">
              Test your strategies against historical data to validate performance
            </p>
          </div>
          <div className="p-6 rounded-lg border bg-card">
            <h3 className="text-xl font-semibold mb-2">Live Trading</h3>
            <p className="text-muted-foreground">
              Deploy your algorithms for live trading with real-time monitoring
            </p>
          </div>
          <div className="p-6 rounded-lg border bg-card">
            <h3 className="text-xl font-semibold mb-2">Risk Management</h3>
            <p className="text-muted-foreground">
              Advanced risk controls and position management tools
            </p>
          </div>
        </div>
      </div>
    </div>
  );
} 