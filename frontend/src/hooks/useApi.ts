import { useAuth } from '@/contexts/AuthContext'

interface ApiOptions {
  method?: string
  body?: any
  headers?: Record<string, string>
}

export function useApi() {
  const { token } = useAuth()
  const baseUrl = 'http://localhost:8000'

  const fetchWithAuth = async (endpoint: string, options: ApiOptions = {}) => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    })

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`)
    }

    return response.json()
  }

  return { fetchWithAuth }
} 