import { useState, useEffect } from 'react';

export type BackendStatus = 'connecting' | 'healthy' | 'unhealthy' | 'recovering';

interface BackendHealthState {
    status: BackendStatus;
    lastCheckedAt: number | null;
    error: string | null;
}

let state: BackendHealthState = {
    status: 'connecting',
    lastCheckedAt: null,
    error: null,
};

const listeners = new Set<() => void>();

export const backendHealthStore = {
    getState: () => state,
    setState: (newState: Partial<BackendHealthState>) => {
        state = { ...state, ...newState };
        listeners.forEach(l => l());
    }
};

export function useBackendHealthStore() {
    const [localState, setLocalState] = useState(state);

    useEffect(() => {
        const listener = () => setLocalState(backendHealthStore.getState());
        listeners.add(listener);
        return () => {
            listeners.delete(listener);
        };
    }, []);

    return {
        ...localState,
        setStatus: (status: BackendStatus, error: string | null = null) => backendHealthStore.setState({ status, error }),
        setLastCheckedAt: (timestamp: number) => backendHealthStore.setState({ lastCheckedAt: timestamp })
    };
}
