/**
 * Custom Hook for Loading Model Data
 * 
 * This hook manages the loading of model documentation data from the
 * generated JSON file. It handles loading states, error conditions,
 * and provides a fallback to mock data during development.
 * 
 * The hook attempts to load from the production data path first,
 * then falls back to mock data if the file isn't available.
 * 
 * @author GPAI Documentation Pipeline
 * @date November 2024
 */

import { useState, useEffect } from 'react';
import { Model } from '@/types/model';
import { mockModels } from '@/data/mockModels';

interface UseModelDataReturn {
  models: Model[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export const useModelData = (): UseModelDataReturn => {
  // State management for data loading
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    const loadModelData = async () => {
      try {
        // Attempt to load from the production data path
        // Use BASE_URL to handle GitHub Pages subdirectory deployment
        const response = await fetch(`${import.meta.env.BASE_URL}data/models.json`);
        
        if (!response.ok) {
          throw new Error(`Failed to load data: ${response.status}`);
        }

        const data = await response.json();
        
        // Extract the last updated timestamp from any model
        // This assumes at least one model has a last_updated field
        const latestUpdate = data.reduce((latest: string | null, model: any) => {
          if (model.last_updated && (!latest || model.last_updated > latest)) {
            return model.last_updated;
          }
          return latest;
        }, null);

        setModels(data);
        setLastUpdated(latestUpdate);
        setError(null);
      } catch (err) {
        // Log the error for debugging purposes
        console.warn('Failed to load production data, falling back to mock data:', err);
        
        // Fall back to mock data for development
        // This ensures the UI remains functional during development
        setModels(mockModels);
        setLastUpdated(new Date().toISOString());
        setError('Using mock data - production data not available');
      } finally {
        setLoading(false);
      }
    };

    loadModelData();
  }, []);

  return { models, loading, error, lastUpdated };
};