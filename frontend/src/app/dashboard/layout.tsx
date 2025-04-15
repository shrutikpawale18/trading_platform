import { Metadata } from "next"

export const metadata: Metadata = {
  title: "Trading Dashboard",
  description: "Advanced algorithmic trading platform dashboard.",
}

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <>
      {children}
    </>
  )
} 