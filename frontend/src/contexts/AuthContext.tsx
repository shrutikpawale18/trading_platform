'use client'

import { createContext, useContext, useState, useEffect } from 'react'
import { getCookie, setCookie, deleteCookie } from 'cookies-next'

interface AuthContextType {
  isAuthenticated: boolean
  login: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Check for token in cookies on initial load
    const token = getCookie('token')
    if (token) {
      setIsAuthenticated(true)
    }
  }, [])

  const login = (token: string) => {
    setCookie('token', token)
    setIsAuthenticated(true)
  }

  const logout = () => {
    deleteCookie('token')
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
} 