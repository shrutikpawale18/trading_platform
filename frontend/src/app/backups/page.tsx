'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { getCookie } from 'cookies-next';
import { format } from 'date-fns';

interface BackupInfo {
  path: string;
  size: number;
  created_at: string;
  algorithm_count: number;
  signal_count: number;
  position_count: number;
  trade_count: number;
}

export default function BackupsPage() {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const router = useRouter();

  useEffect(() => {
    const token = getCookie('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchBackups();
  }, [router]);

  const fetchBackups = async () => {
    try {
      setLoading(true);
      const token = getCookie('token');
      const response = await fetch('http://localhost:8000/api/backup/list', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch backups');
      }

      const data = await response.json();
      setBackups(data.backups);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const createBackup = async () => {
    try {
      setLoading(true);
      const token = getCookie('token');
      const response = await fetch('http://localhost:8000/api/backup/create', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to create backup');
      }

      setSuccess('Backup created successfully');
      fetchBackups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const restoreBackup = async (backupPath: string) => {
    if (!window.confirm('Are you sure you want to restore this backup? This will overwrite the current database.')) {
      return;
    }

    try {
      setLoading(true);
      const token = getCookie('token');
      const response = await fetch(`http://localhost:8000/api/backup/restore/${encodeURIComponent(backupPath)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to restore backup');
      }

      setSuccess('Backup restored successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const cleanupBackups = async () => {
    try {
      setLoading(true);
      const token = getCookie('token');
      const response = await fetch('http://localhost:8000/api/backup/cleanup', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to cleanup backups');
      }

      setSuccess('Old backups cleaned up successfully');
      fetchBackups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Database Backups</h1>
        <div className="space-x-4">
          <Button onClick={createBackup} disabled={loading}>
            Create Backup
          </Button>
          <Button onClick={cleanupBackups} disabled={loading} variant="outline">
            Cleanup Old Backups
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-100 text-green-700 rounded-lg">
          {success}
        </div>
      )}

      <div className="grid gap-4">
        {backups.map((backup) => (
          <Card key={backup.path}>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>{backup.path}</CardTitle>
                <Button
                  onClick={() => restoreBackup(backup.path)}
                  disabled={loading}
                  variant="outline"
                >
                  Restore
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-sm font-medium">Created</div>
                  <div className="text-sm text-gray-500">
                    {format(new Date(backup.created_at), 'PPpp')}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Size</div>
                  <div className="text-sm text-gray-500">
                    {(backup.size / 1024).toFixed(2)} KB
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Algorithms</div>
                  <div className="text-sm text-gray-500">
                    {backup.algorithm_count}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Trades</div>
                  <div className="text-sm text-gray-500">
                    {backup.trade_count}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
} 