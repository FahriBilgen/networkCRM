import { useEffect, useState } from 'react';
import { fetchGraph } from '../api/client';
import { mockGraphResponse } from '../mock/data';
import type { GraphResponse } from '../types';

export function useGraphData() {
  const [data, setData] = useState<GraphResponse>(mockGraphResponse);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const remote = await fetchGraph();
        if (mounted && remote?.nodes?.length) {
          setData(remote);
        }
      } catch (err) {
        console.warn('Graph fetch failed, fallback to mock', err);
        if (mounted) {
          setError('Graph yüklenemedi, mock veri gösteriliyor');
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
