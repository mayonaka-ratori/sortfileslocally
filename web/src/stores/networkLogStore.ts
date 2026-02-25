"use client"

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';

export interface NetworkLogEntry {
    id: number;
    timestamp: string;
    method: string;
    url: string;
    status: number | 'blocked';
    duration: number;
    isLocal: boolean;
}

interface NetworkLogContextType {
    logs: NetworkLogEntry[];
    addLog: (entry: Omit<NetworkLogEntry, 'id'>) => void;
    clearLog: () => void;
}

const NetworkLogContext = createContext<NetworkLogContextType | undefined>(undefined);

const MAX_LOGS = 50;

export function NetworkLogProvider({ children }: { children: ReactNode }) {
    const [logs, setLogs] = useState<NetworkLogEntry[]>([]);
    const [nextId, setNextId] = useState(1);

    const addLog = useCallback((entry: Omit<NetworkLogEntry, 'id'>) => {
        setLogs(prevLogs => {
            const newLog = { ...entry, id: nextId };
            const newLogs = [newLog, ...prevLogs];
            return newLogs.slice(0, MAX_LOGS);
        });
        setNextId(id => id + 1);
    }, [nextId]);

    const clearLog = useCallback(() => {
        setLogs([]);
    }, []);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            (window as Window & { __ADD_NETWORK_LOG?: (entry: Omit<NetworkLogEntry, 'id'>) => void }).__ADD_NETWORK_LOG = addLog;
        }
    }, [addLog]);

    return React.createElement(NetworkLogContext.Provider, { value: { logs, addLog, clearLog } }, children);
}

export function useNetworkLog() {
    const context = useContext(NetworkLogContext);
    if (context === undefined) {
        throw new Error('useNetworkLog must be used within a NetworkLogProvider');
    }
    return context;
}
