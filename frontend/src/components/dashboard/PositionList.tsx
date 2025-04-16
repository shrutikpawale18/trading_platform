import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface Position {
  id: number;
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  status: string;
  entry_time: string;
  last_updated: string;
}

interface PositionListProps {
  positions?: Position[];
}

export function PositionList({ positions = [] }: PositionListProps) {
  const calculatePnL = (position: Position) => {
    const pnl = (position.current_price - position.entry_price) * position.quantity;
    const pnlPercent = ((position.current_price - position.entry_price) / position.entry_price) * 100;
    return { pnl, pnlPercent };
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Open Positions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {positions.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground">
              No open positions
            </div>
          ) : (
            positions.map((position) => {
              const { pnl, pnlPercent } = calculatePnL(position);
              const isProfit = pnl >= 0;

              return (
                <div
                  key={position.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">{position.symbol}</span>
                      <Badge variant="outline">
                        {position.quantity} shares
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Entry: ${position.entry_price.toFixed(2)}
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className="font-medium">
                        ${position.current_price.toFixed(2)}
                      </div>
                      <div
                        className={`text-sm ${
                          isProfit ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {isProfit ? (
                          <TrendingUp className="inline h-4 w-4" />
                        ) : (
                          <TrendingDown className="inline h-4 w-4" />
                        )}
                        ${Math.abs(pnl).toFixed(2)} ({Math.abs(pnlPercent).toFixed(2)}%)
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {new Date(position.entry_time).toLocaleString()}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
} 