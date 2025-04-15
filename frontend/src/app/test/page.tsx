'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

export default function TestPage() {
  return (
    <div className="container mx-auto p-4">
      <Card className="mb-4">
        <CardHeader>
          <h2 className="text-2xl font-semibold">Test Page</h2>
        </CardHeader>
        <CardContent>
          <Button>Test Button</Button>
        </CardContent>
      </Card>
    </div>
  )
} 