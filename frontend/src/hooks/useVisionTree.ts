import { useEffect, useState } from 'react';
import { fetchVisionTree } from '../api/client';
import { mockVisionTree } from '../mock/data';
import type { VisionTreeResponse } from '../types';
import { useAuthStore } from '../store/authStore';
import { useRefreshStore } from '../store/dataRefreshStore';

export function useVisionTree() {
  const [data, setData] = useState<VisionTreeResponse>(mockVisionTree);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = useAuthStore((state) => state.token);
  const visionKey = useRefreshStore((state) => state.visionKey);

  useEffect(() => {
    let mounted = true;
    if (!token) {
      setData(mockVisionTree);
      setError(null);
      setLoading(false);
      return () => {
        mounted = false;
      };
    }

    async function load() {
      setLoading(true);
      try {
        const remote = await fetchVisionTree();
        if (mounted) {
          if (remote) {
            setData(remote);
            setError(null);
          } else {
            setData(mockVisionTree);
          }
        }
      } catch (err) {
        console.warn('Vision tree fetch failed, falling back to mock data', err);
        if (mounted) {
          setError('Vision tree yüklenirken hata oluştu');
          setData(mockVisionTree);
        }
      } finally {
        mounted && setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [token, visionKey]);

  return { data, loading, error };
}
