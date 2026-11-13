import { useCallback, useEffect, useState } from 'react';

import { errorMessage } from '../api';

interface PollingResult<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

/**
 * 定时拉取数据；deps 变化时立即重新拉取并重设定时器，intervalMs 为 null 时只拉一次。
 */
export function usePolling<T>(
    loader: () => Promise<T>,
    intervalMs: number | null,
    deps: unknown[] = []
): PollingResult<T> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        setLoading(true);
        try {
            const result = await loader();
            setData(result);
            setError(null);
        } catch (err) {
            setError(errorMessage(err));
        } finally {
            setLoading(false);
        }
        // loader 由调用方按 deps 重新创建，这里显式只依赖 deps
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    useEffect(() => {
        void refresh();
    }, [refresh]);

    useEffect(() => {
        if (intervalMs === null) {
            return;
        }
        const timer = window.setInterval(() => {
            void refresh();
        }, intervalMs);
        return () => window.clearInterval(timer);
    }, [refresh, intervalMs]);

    return { data, loading, error, refresh };
}
