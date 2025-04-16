'use client'

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { getCookie } from 'cookies-next';
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
// Import table components if needed later
// import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// TODO: Define interface for Algorithm data matching backend model
interface Algorithm {
  id: number;
  symbol: string;
  type: string; // Consider using an enum matching the backend
  parameters: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  user_id: number;
}

// Interface for the creation form data
interface AlgorithmFormData {
  symbol: string;
  type: string; // Keep as string for form state, map later
  timeframe: string;
  lookback_days: string; // Keep as string for input
  short_window: string;  // Keep as string for input
  long_window: string;   // Keep as string for input
}

// Define available types (matching backend Enum values)
const ALGORITHM_TYPES = [
  { value: "moving_average_crossover", label: "Moving Average Crossover" },
  // { value: "rsi", label: "RSI" }, // Add other types later
  // { value: "macd", label: "MACD" },
];

const DEFAULT_FORM_DATA: AlgorithmFormData = {
    symbol: '',
    type: ALGORITHM_TYPES[0].value, // Default to first type
    timeframe: '1D', 
    lookback_days: '60',
    short_window: '10',
    long_window: '20'
};

export default function AlgorithmsPage() {
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false); // For form submission
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false); // State for dialog
  const [formData, setFormData] = useState<AlgorithmFormData>(DEFAULT_FORM_DATA);
  const [actionLoading, setActionLoading] = useState<Record<number, boolean>>({}); // Loading state per algorithm ID
  const router = useRouter();

  // --- Fetch Algorithms Logic (Moved outside useEffect) --- 
  const fetchAlgorithms = useCallback(async () => { // Use useCallback
      const token = getCookie('token');
      if (!token) { 
          toast.error("Authentication required. Redirecting to login...");
          router.push('/login'); // Redirect if token missing during fetch
          return; 
      }
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('http://localhost:8000/api/algorithms', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
          let errorDetail = 'Failed to fetch algorithms';
          try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
          } catch {}
          throw new Error(`${response.status}: ${errorDetail}`);
        }
        const data: Algorithm[] = await response.json();
        setAlgorithms(data);
      } catch (err: any) {
        console.error("Algorithm fetch error:", err);
        const errorMsg = err.message || 'Failed to load algorithms';
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setIsLoading(false);
      }
    }, [router]); // Add router dependency for redirect

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;
    fetchAlgorithms(); // Initial fetch
  }, [isMounted, fetchAlgorithms]); // Add fetchAlgorithms dependency

  // --- Form Input Handler --- 
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (name: string, value: string) => {
      setFormData(prev => ({ ...prev, [name]: value }));
  };

  // --- Create Algorithm Handler --- 
  const handleCreateAlgorithm = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); // Prevent default form submission
    setIsSubmitting(true);
    const token = getCookie('token');
    if (!token) {
      toast.error("Authentication expired. Please login again.");
      setIsSubmitting(false);
      router.push('/login');
      return;
    }

    // Basic Validation
    if (!formData.symbol || !formData.short_window || !formData.long_window || !formData.lookback_days) {
        toast.error("Please fill in all required fields.");
        setIsSubmitting(false);
        return;
    }

    // Construct payload matching backend model
    const payload = {
      symbol: formData.symbol.toUpperCase(),
      type: formData.type,
      parameters: {
        timeframe: formData.timeframe,
        lookback_days: parseInt(formData.lookback_days, 10),
        short_window: parseInt(formData.short_window, 10),
        long_window: parseInt(formData.long_window, 10),
      }
    };
    
    // Validate parsed numbers
    if (isNaN(payload.parameters.lookback_days) || isNaN(payload.parameters.short_window) || isNaN(payload.parameters.long_window)) {
        toast.error("Lookback days, short window, and long window must be valid numbers.");
        setIsSubmitting(false);
        return;
    }
    if (payload.parameters.short_window >= payload.parameters.long_window) {
        toast.error("Short window must be less than long window.");
        setIsSubmitting(false);
        return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/algorithms', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        let errorDetail = 'Failed to create algorithm';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch {}
        throw new Error(`${response.status}: ${errorDetail}`);
      }

      toast.success(`Algorithm for ${payload.symbol} created successfully!`);
      setIsCreateDialogOpen(false); // Close dialog on success
      setFormData(DEFAULT_FORM_DATA); // Reset form using constant
      await fetchAlgorithms(); // Refresh the list

    } catch (err: any) {
      console.error("Create algorithm error:", err);
      toast.error(err.message || 'Failed to create algorithm');
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Activate/Deactivate Handler --- 
  const handleToggleStatus = async (algoId: number, currentStatus: boolean) => {
    const token = getCookie('token');
    if (!token) {
      toast.error("Authentication required.");
      router.push('/login');
      return;
    }

    const action = currentStatus ? 'deactivate' : 'activate';
    setActionLoading(prev => ({ ...prev, [algoId]: true }));

    try {
      const response = await fetch(`http://localhost:8000/api/algorithms/${algoId}/status`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (!response.ok) {
        let errorDetail = `Failed to ${action} algorithm`;
        try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch {} 
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      
      toast.success(`Algorithm ${action}d successfully`);
      await fetchAlgorithms(); // Refresh list

    } catch (err: any) {
      console.error(`Error ${action}ing algorithm ${algoId}:`, err);
      toast.error(err.message || `Failed to ${action} algorithm`);
    } finally {
      setActionLoading(prev => ({ ...prev, [algoId]: false }));
    }
  };

  // --- Run Once Handler --- 
  const handleRunOnce = async (algoId: number) => {
     const token = getCookie('token');
    if (!token) {
      toast.error("Authentication required.");
      router.push('/login');
      return;
    }

    setActionLoading(prev => ({ ...prev, [algoId]: true }));
    toast.info(`Requesting run for algorithm ${algoId}...`);

    try {
      const response = await fetch(`http://localhost:8000/api/algorithms/${algoId}/run`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        let errorDetail = 'Failed to run algorithm';
        try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch {} 
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      
      const result = await response.json(); // Might be null if no signal generated
      if (result && result.id) {
        toast.success(`Algorithm ${algoId} ran successfully. Signal generated: ${result.signal_type}`);
      } else {
        toast.warning(`Algorithm ${algoId} ran, but no new signal was generated (e.g., conditions not met, insufficient data).`);
      }

    } catch (err: any) {
      console.error(`Error running algorithm ${algoId}:`, err);
      toast.error(err.message || 'Failed to run algorithm');
    } finally {
      setActionLoading(prev => ({ ...prev, [algoId]: false }));
    }
  };

  // --- Delete Handler --- 
  const handleDelete = async (algoId: number) => {
    const token = getCookie('token');
    if (!token) {
      toast.error("Authentication required.");
      router.push('/login');
      return;
    }
    
    setActionLoading(prev => ({ ...prev, [algoId]: true }));

    try {
      const response = await fetch(`http://localhost:8000/api/algorithms/${algoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
         // Handle 404 specifically?
        let errorDetail = 'Failed to delete algorithm';
        if (response.status !== 404) { // Don't try to parse JSON for 404
           try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch {} 
        }
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      
      toast.success(`Algorithm ${algoId} deleted successfully`);
      await fetchAlgorithms(); // Refresh list

    } catch (err: any) {
      console.error(`Error deleting algorithm ${algoId}:`, err);
      toast.error(err.message || 'Failed to delete algorithm');
    } finally {
       // Keep loading false on delete, as the item will disappear
       // Or manage loading state differently if needed
       setActionLoading(prev => {
          const newState = { ...prev };
          delete newState[algoId];
          return newState;
       });
    }
  };

  return (
    <div className="container mx-auto p-4 md:p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Manage Algorithms</h1>
        
        {/* --- Create Algorithm Button & Dialog --- */}
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create New Algorithm</Button> 
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create New Algorithm</DialogTitle>
              <DialogDescription>
                Configure the details for your new trading algorithm.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateAlgorithm} className="grid gap-4 py-4">
              {/* Symbol Input */}
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="symbol" className="text-right">
                  Symbol
                </Label>
                <Input 
                  id="symbol" 
                  name="symbol" 
                  value={formData.symbol}
                  onChange={handleInputChange}
                  className="col-span-3"
                  placeholder="e.g., AAPL"
                  required
                />
              </div>
              {/* Algorithm Type Select */}
              <div className="grid grid-cols-4 items-center gap-4">
                 <Label htmlFor="type" className="text-right">
                   Type
                 </Label>
                 <Select 
                    name="type"
                    value={formData.type} 
                    onValueChange={(value) => handleSelectChange('type', value)}
                 >
                   <SelectTrigger className="col-span-3">
                     <SelectValue placeholder="Select algorithm type" />
                   </SelectTrigger>
                   <SelectContent>
                     {ALGORITHM_TYPES.map(type => (
                       <SelectItem key={type.value} value={type.value}>
                         {type.label}
                       </SelectItem>
                     ))}
                   </SelectContent>
                 </Select>
              </div>
              {/* Parameters (Example for MA Crossover) */}
              {/* TODO: Make parameters dynamic based on selected type */}
              <div className="grid grid-cols-4 items-center gap-4">
                 <Label htmlFor="timeframe" className="text-right">
                   Timeframe
                 </Label>
                 <Select 
                    name="timeframe"
                    value={formData.timeframe} 
                    onValueChange={(value) => handleSelectChange('timeframe', value)}
                 >
                   <SelectTrigger className="col-span-3">
                     <SelectValue placeholder="Select timeframe" />
                   </SelectTrigger>
                   <SelectContent>
                     <SelectItem value="1Min">1 Minute</SelectItem>
                     <SelectItem value="5Min">5 Minutes</SelectItem>
                     <SelectItem value="15Min">15 Minutes</SelectItem>
                     <SelectItem value="1H">1 Hour</SelectItem>
                     <SelectItem value="1D">1 Day</SelectItem>
                   </SelectContent>
                 </Select>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                 <Label htmlFor="lookback_days" className="text-right">
                   Lookback (Days)
                 </Label>
                 <Input
                   id="lookback_days"
                   name="lookback_days"
                   type="number"
                   value={formData.lookback_days}
                   onChange={handleInputChange}
                   className="col-span-3"
                   required
                   min="1"
                 />
              </div>
               <div className="grid grid-cols-4 items-center gap-4">
                 <Label htmlFor="short_window" className="text-right">
                   Short Window
                 </Label>
                 <Input
                   id="short_window"
                   name="short_window"
                   type="number"
                   value={formData.short_window}
                   onChange={handleInputChange}
                   className="col-span-3"
                   required
                   min="1"
                 />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                 <Label htmlFor="long_window" className="text-right">
                   Long Window
                 </Label>
                 <Input
                   id="long_window"
                   name="long_window"
                   type="number"
                   value={formData.long_window}
                   onChange={handleInputChange}
                   className="col-span-3"
                   required
                   min="2"
                 />
              </div>
              <DialogFooter>
                 <DialogClose asChild>
                      <Button type="button" variant="outline">Cancel</Button>
                 </DialogClose>
                 <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? 'Creating...' : 'Create Algorithm'}
                 </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

      </div>

      {isLoading && <div className="text-center py-10">Loading algorithms...</div>}
      {error && <div className="text-center py-10 text-red-500">Error: {error}</div>}

      {!isLoading && !error && algorithms.length === 0 && (
        <div className="text-center py-10 text-gray-500">No algorithms found. Create one!</div>
      )}

      {!isLoading && !error && algorithms.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {algorithms.map((algo) => {
            const isLoadingAction = actionLoading[algo.id]; // Check loading state for this specific algo
            return (
                <Card key={algo.id}>
                  <CardHeader>
                    <CardTitle className="flex justify-between items-center">
                      <span>{algo.symbol}</span>
                      {/* TODO: Add status indicator/switch */}
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${algo.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {algo.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </CardTitle>
                    <CardDescription>{algo.type.replace(/_/g, ' ')}</CardDescription> 
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm space-y-2">
                      <p><strong>Parameters:</strong></p>
                      <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(algo.parameters, null, 2)}
                      </pre>
                      <p className="text-xs text-gray-500 pt-2">
                        Created: {new Date(algo.created_at).toLocaleString()}
                      </p>
                      <div className="flex justify-end space-x-2 pt-2">
                          {/* Run Once Button */}
                          <Button 
                             variant="outline" 
                             size="sm" 
                             onClick={() => handleRunOnce(algo.id)}
                             disabled={isLoadingAction}
                          >
                             {isLoadingAction ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                             Run Once
                          </Button>
                          {/* Activate/Deactivate Button */}
                          <Button 
                             variant="secondary" 
                             size="sm" 
                             onClick={() => handleToggleStatus(algo.id, algo.is_active)}
                             disabled={isLoadingAction}
                          >
                              {isLoadingAction ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                              {algo.is_active ? 'Deactivate' : 'Activate'}
                          </Button>
                          {/* Delete Button with Confirmation */}
                          <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="destructive" size="sm" disabled={isLoadingAction}>
                                  {isLoadingAction ? <Loader2 className="h-4 w-4 animate-spin" /> : "Delete"}
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    This action cannot be undone. This will permanently delete the algorithm 
                                    for symbol {algo.symbol} ({algo.type.replace(/_/g, ' ')}).
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction onClick={() => handleDelete(algo.id)} className="bg-red-600 hover:bg-red-700">
                                      Continue
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                          </AlertDialog>
                      </div>
                    </div>
                  </CardContent>
                </Card>
            );
          })}
        </div>
      )}
    </div>
  );
} 