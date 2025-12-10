import { useEffect, useState } from 'react';
import { fetchVisionTree } from '../api/client';
import { mockVisionTree } from '../mock/data';
import type { VisionTreeResponse } from '../types';

export function useVisionTree() {
  const [data, setData] = useState<VisionTreeResponse>(mockVisionTree);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const remote = await fetchVisionTree();
        if (mounted && remote?.visions?.length) {
          setData(remote);
        }
      } catch (err) {
        console.warn('Vision tree fetch failed, falling back to mock data', err);
        if (mounted) {
          setError('Vision tree yüklenirken hata oluştu');
        }
      } finally {
        mounted && setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  return { data, loading, error };
}
