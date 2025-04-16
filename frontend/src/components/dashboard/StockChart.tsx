import React, { useEffect, useState } from 'react';
import { useApi } from '../../hooks/useApi';
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
import { Skeleton } from '../../components/ui/skeleton';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface StockChartProps {
  symbol: string;
  timeframe: string;
}

interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor: string;
    tension: number;
  }[];
}

interface Bar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export const StockChart: React.FC<StockChartProps> = ({ symbol, timeframe }) => {
  const [chartData, setChartData] = useState<ChartData>({
    labels: [],
    datasets: [
      {
        label: 'Price',
        data: [],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        tension: 0.1,
      },
    ],
  });

  const { data, isLoading, error, execute } = useApi<Bar[]>({
    maxRetries: 3,
    retryDelay: 1000,
    showLoadingToast: false,
    showErrorToast: true,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await execute(
          `/api/stocks/${symbol}/bars`,
          'GET',
          undefined,
          { timeframe }
        );
        if (response) {
          const labels = response.map((bar: Bar) => new Date(bar.timestamp).toLocaleDateString());
          const prices = response.map((bar: Bar) => bar.close);

          setChartData({
            labels,
            datasets: [
              {
                ...chartData.datasets[0],
                data: prices,
              },
            ],
          });
        }
      } catch (error) {
        console.error('Error fetching chart data:', error);
      }
    };

    fetchData();
  }, [symbol, timeframe, execute]);

  if (isLoading) {
    return <Skeleton className="h-[400px] w-full" />;
  }

  if (error) {
    return <div className="text-red-500">Error loading chart data</div>;
  }

  return (
    <div className="p-4 bg-white rounded-lg shadow">
      <Line
        data={chartData}
        options={{
          responsive: true,
          plugins: {
            legend: {
              position: 'top' as const,
            },
            title: {
              display: true,
              text: `${symbol} Price Chart`,
            },
          },
        }}
      />
    </div>
  );
}; 