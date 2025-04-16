import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface Signal {
  id: number;
  algorithm_id: number;
  symbol: string;
  type: string;
  timestamp: string;
  confidence: number;
  metadata: Record<string, any>;
}

interface RecentSignalsProps {
  signals?: Signal[];
}

export function RecentSignals({ signals = [] }: RecentSignalsProps) {
  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'BUY':
        return <ArrowUp className="h-4 w-4 text-green-500" />;
      case 'SELL':
        return <ArrowDown className="h-4 w-4 text-red-500" />;
      case 'HOLD':
        return <Minus className="h-4 w-4 text-gray-500" />;
      default:
        return null;
    }
  };

  const getSignalBadge = (type: string) => {
    switch (type) {
      case 'BUY':
        return 'bg-green-100 text-green-800';
      case 'SELL':
        return 'bg-red-100 text-red-800';
      case 'HOLD':
        return 'bg-gray-100 text-gray-800';
      default:
        return '';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Signals</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {signals.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground">
              No recent signals
            </div>
          ) : (
            signals.map((signal) => (
              <div
                key={signal.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center space-x-4">
                  {getSignalIcon(signal.type)}
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">{signal.symbol}</span>
                      <Badge className={getSignalBadge(signal.type)}>
                        {signal.type}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Confidence: {(signal.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  {new Date(signal.timestamp).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
} 