'use client';

import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface PriceData {
  timestamp: string;
  price: number;
}

interface Signal {
  timestamp: string;
  type: 'BUY' | 'SELL';
  price: number;
}

interface AlgorithmResultsProps {
  algorithmId: number;
}

export function AlgorithmResults({ algorithmId }: AlgorithmResultsProps) {
  const [priceData, setPriceData] = useState<PriceData[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlgorithmResults = async () => {
      try {
        const response = await fetch(`/api/algorithms/${algorithmId}/results`);
        const data = await response.json();
        
        setPriceData(data.priceData || []);
        setSignals(data.signals || []);
      } catch (error) {
        console.error('Error fetching algorithm results:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlgorithmResults();
  }, [algorithmId]);

  const chartData = {
    labels: priceData.map(point => new Date(point.timestamp).toLocaleTimeString()),
    datasets: [
      {
        label: 'Price',
        data: priceData.map(point => point.price),
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
      },
      ...signals.map(signal => ({
        label: signal.type,
        data: [signal.price],
        pointBackgroundColor: signal.type === 'BUY' ? 'green' : 'red',
        pointRadius: 6,
        showLine: false,
      })),
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Algorithm Performance',
      },
    },
    scales: {
      y: {
        beginAtZero: false,
      },
    },
  };

  if (loading) {
    return <div className="p-4">Loading algorithm results...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">Algorithm Results</h2>
      
      <div className="h-96 mb-6">
        <Line data={chartData} options={options} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-medium mb-2">Recent Signals</h3>
          <div className="space-y-2">
            {signals.slice(0, 5).map((signal, index) => (
              <div key={index} className="flex justify-between items-center">
                <span className={`px-2 py-1 rounded ${
                  signal.type === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {signal.type}
                </span>
                <span className="text-gray-600">
                  {new Date(signal.timestamp).toLocaleString()}
                </span>
                <span className="font-medium">${signal.price.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-medium mb-2">Performance Metrics</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Trades</span>
              <span className="font-medium">{signals.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Buy Signals</span>
              <span className="font-medium text-green-600">
                {signals.filter(s => s.type === 'BUY').length}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Sell Signals</span>
              <span className="font-medium text-red-600">
                {signals.filter(s => s.type === 'SELL').length}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 