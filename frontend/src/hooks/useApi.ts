import { useState, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { APIError } from '../types/api';

interface UseApiOptions {
  maxRetries?: number;
  retryDelay?: number;
  showLoadingToast?: boolean;
  showErrorToast?: boolean;
}

export const useApi = <T>(options: UseApiOptions = {}) => {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    showLoadingToast = true,
    showErrorToast = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const execute = useCallback(
    async (
      url: string,
      method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
      body?: any,
      pathParams?: Record<string, string>
    ) => {
      setIsLoading(true);
      setError(null);
      let loadingToastId: string | undefined;

      try {
        // Replace path parameters in URL
        let finalUrl = url;
        if (pathParams) {
          Object.entries(pathParams).forEach(([key, value]) => {
            finalUrl = finalUrl.replace(`:${key}`, value);
          });
        }

        // Show loading toast if enabled
        if (showLoadingToast) {
          loadingToastId = toast.loading('Loading...');
        }

        const response = await fetch(finalUrl, {
          method,
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: body ? JSON.stringify(body) : undefined,
        });

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Invalid response format');
        }

        const responseData = await response.json();

        if (!response.ok) {
          const apiError: APIError = {
            message: responseData.detail || 'An error occurred',
            status: response.status,
            code: responseData.code || 'UNKNOWN_ERROR',
          };
          throw apiError;
        }

        setData(responseData);
        setRetryCount(0);
        return responseData;
      } catch (error) {
        const apiError = error as APIError;
        setError(apiError);

        // Handle retries for network errors or 5xx errors
        if (
          (apiError.status && apiError.status >= 500) ||
          !apiError.status
        ) {
          if (retryCount < maxRetries) {
            setRetryCount((prev) => prev + 1);
            await new Promise((resolve) => setTimeout(resolve, retryDelay));
            return execute(url, method, body, pathParams);
          }
        }

        if (showErrorToast) {
          toast.error(apiError.message || 'An error occurred', {
            id: loadingToastId,
          });
        } else if (loadingToastId) {
          toast.dismiss(loadingToastId);
        }

        throw apiError;
      } finally {
        setIsLoading(false);
        if (loadingToastId && !showErrorToast) {
          toast.dismiss(loadingToastId);
        }
      }
    },
    [maxRetries, retryDelay, retryCount, showLoadingToast, showErrorToast]
  );

  return {
    data,
    isLoading,
    error,
    execute,
    retryCount,
  };
};

// Example usage:
// const { data, loading, error, execute } = useApi<Bar[]>('/api/historical-bars/{0}');
// useEffect(() => {
//     execute('AAPL', { timeframe: '1D' });
// }, []); 