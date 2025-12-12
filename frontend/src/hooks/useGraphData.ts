import { useEffect, useState } from 'react';
import { fetchGraph } from '../api/client';
import { mockGraphResponse } from '../mock/data';
import type { GraphResponse } from '../types';
import { useAuthStore } from '../store/authStore';
import { useRefreshStore } from '../store/dataRefreshStore';
import { useGraphStore } from '../store/graphStore';

export function useGraphData() {
  const [data, setData] = useState<GraphResponse>(mockGraphResponse);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = useAuthStore((state) => state.token);
  const graphKey = useRefreshStore((state) => state.graphKey);
  const setGraph = useGraphStore((state) => state.setGraph);

  useEffect(() => {
    let mounted = true;
    if (!token) {
      setData(mockGraphResponse);
      setGraph(mockGraphResponse);
      setError(null);
      setLoading(false);
      return () => {
        mounted = false;
      };
    }

    async function load() {
      setLoading(true);
      try {
        const remote = await fetchGraph();
        if (mounted && remote?.nodes?.length) {
          setData(remote);
          setGraph(remote);
          setError(null);
        }
      } catch (err) {
        console.warn('Graph fetch failed', err);
        if (mounted) {
          if (import.meta.env.PROD) {
            setError('Ağ verisi yüklenemedi. Lütfen bağlantınızı kontrol edin.');
            setData({ nodes: [], links: [] });
            setGraph({ nodes: [], links: [] });
          } else {
            setError('Graph yüklenemedi, mock veri gösteriliyor (DEV MODE)');
            setData(mockGraphResponse);
            setGraph(mockGraphResponse);
          }
        }
      } finally {
        mounted && setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [token, graphKey]);

  return { data, loading, error };
}
