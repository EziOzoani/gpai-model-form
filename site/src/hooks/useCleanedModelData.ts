import { useState, useEffect } from 'react';
import { Model } from '@/types/model';

interface CleanedDataResponse {
  models: any[];
  total: number;
  signatories_count: number;
  cutoff_date: string;
  last_updated: string;
}

export const useCleanedModelData = (
  regionFilter: string,
  sizeFilter: string,
  codeOfPracticeFilter: string,
  dateCutoff: string
) => {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [signatoriesCount, setSignatoriesCount] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Build query parameters
        const params = new URLSearchParams({
          region: regionFilter,
          size: sizeFilter,
          code_of_practice: codeOfPracticeFilter,
          cutoff: dateCutoff
        });

        // Try to fetch from API first
        try {
          const response = await fetch(`http://localhost:5002/api/models/cleaned?${params}`);
          if (response.ok) {
            const data: CleanedDataResponse = await response.json();
            
            // Transform cleaned data to Model format
            const transformedModels = data.models.map((model: any) => ({
              model_name: model.name,
              provider: model.provider,
              region: model.region || 'Unknown',
              size: model.size || 'Unknown',
              release_date: model.release_date || 'Unknown',
              transparency_score: {
                overall: model.transparency_score || 0,
                sections: model.section_data ? {
                  general: model.sections_list?.includes('general') ? 1 : 0,
                  properties: model.sections_list?.includes('properties') ? 1 : 0,
                  distribution: model.sections_list?.includes('distribution') ? 1 : 0,
                  use: model.sections_list?.includes('use') ? 1 : 0,
                  data: model.sections_list?.includes('data') ? 1 : 0,
                  training: model.sections_list?.includes('training') ? 1 : 0,
                  compute: model.sections_list?.includes('compute') ? 1 : 0,
                  energy: model.sections_list?.includes('energy') ? 1 : 0,
                } : {}
              },
              section_data: model.section_data || {},
              code_of_practice_signatory: model.code_of_practice_signatory,
              stars: model.bonus_stars || 0
            }));
            
            setModels(transformedModels);
            setSignatoriesCount(data.signatories_count);
            setLastUpdated(data.last_updated);
            setLoading(false);
            return;
          }
        } catch (apiError) {
          console.log('API not available, falling back to static data');
        }

        // Fallback to original data if API is not available
        const response = await fetch('/data/models.json');
        if (!response.ok) {
          throw new Error('Failed to fetch model data');
        }
        const data = await response.json();
        
        // Filter based on parameters
        let filteredModels = data.models || [];
        
        if (regionFilter !== 'all') {
          filteredModels = filteredModels.filter((m: any) => m.region === regionFilter);
        }
        
        if (sizeFilter !== 'all') {
          if (sizeFilter === 'big') {
            filteredModels = filteredModels.filter((m: any) => 
              m.size === 'Big' || m.size?.includes('Large')
            );
          } else {
            filteredModels = filteredModels.filter((m: any) => 
              m.size === 'Small' || m.size?.includes('Medium')
            );
          }
        }
        
        setModels(filteredModels);
        setLastUpdated(data.last_updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [regionFilter, sizeFilter, codeOfPracticeFilter, dateCutoff]);

  return { models, loading, error, lastUpdated, signatoriesCount };
};