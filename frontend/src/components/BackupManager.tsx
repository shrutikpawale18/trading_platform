import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
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

const BackupManager: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchBackups = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/backup/list', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('Failed to fetch backups');
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
      const response = await fetch('http://localhost:8000/api/backup/create', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('Failed to create backup');
      const data = await response.json();
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
      const response = await fetch(`http://localhost:8000/api/backup/restore/${encodeURIComponent(backupPath)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('Failed to restore backup');
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
      const response = await fetch('http://localhost:8000/api/backup/cleanup', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('Failed to cleanup backups');
      setSuccess('Old backups cleaned up successfully');
      fetchBackups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchBackups();
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <div className="text-center text-red-500">Please log in to manage backups</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Database Backups</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <div className="flex space-x-4 mb-6">
        <button
          onClick={createBackup}
          disabled={loading}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          Create Backup
        </button>
        <button
          onClick={cleanupBackups}
          disabled={loading}
          className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          Cleanup Old Backups
        </button>
      </div>

      {loading ? (
        <div className="text-center">Loading...</div>
      ) : (
        <div className="grid gap-4">
          {backups.map((backup) => (
            <div key={backup.path} className="border rounded p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">{backup.path}</h3>
                  <p className="text-sm text-gray-600">
                    Created: {format(new Date(backup.created_at), 'PPpp')}
                  </p>
                  <p className="text-sm text-gray-600">
                    Size: {(backup.size / 1024).toFixed(2)} KB
                  </p>
                </div>
                <button
                  onClick={() => restoreBackup(backup.path)}
                  disabled={loading}
                  className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                >
                  Restore
                </button>
              </div>
              <div className="mt-2 grid grid-cols-4 gap-2 text-sm">
                <div className="bg-gray-100 p-2 rounded">
                  <div className="font-medium">Algorithms</div>
                  <div>{backup.algorithm_count}</div>
                </div>
                <div className="bg-gray-100 p-2 rounded">
                  <div className="font-medium">Signals</div>
                  <div>{backup.signal_count}</div>
                </div>
                <div className="bg-gray-100 p-2 rounded">
                  <div className="font-medium">Positions</div>
                  <div>{backup.position_count}</div>
                </div>
                <div className="bg-gray-100 p-2 rounded">
                  <div className="font-medium">Trades</div>
                  <div>{backup.trade_count}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BackupManager; 