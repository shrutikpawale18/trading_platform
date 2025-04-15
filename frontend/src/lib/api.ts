import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if it exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const auth = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const response = await api.post('/token', formData);
    return response.data;
  },
  register: async (email: string, password: string, alpacaApiKey?: string, alpacaSecretKey?: string) => {
    const response = await api.post('/register', {
      email,
      password,
      alpaca_api_key: alpacaApiKey,
      alpaca_secret_key: alpacaSecretKey,
    });
    return response.data;
  },
};

export const trading = {
  placeOrder: async (symbol: string, quantity: number, side: 'buy' | 'sell') => {
    const response = await api.post('/place-order', {
      symbol,
      quantity,
      side,
    });
    return response.data;
  },
  getTradeStatus: async (orderId: string) => {
    const response = await api.get(`/trade-status/${orderId}`);
    return response.data;
  },
  getAccountInfo: async () => {
    const response = await api.get('/account-info');
    return response.data;
  },
  runAlgorithm: async (prices: number[], shortWindow: number, longWindow: number) => {
    const response = await api.post('/run-algo', {
      prices,
      short_window: shortWindow,
      long_window: longWindow,
    });
    return response.data;
  },
}; 