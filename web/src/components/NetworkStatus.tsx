"use client"

import React, { useState, useEffect } from "react"
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from "framer-motion"
import { WifiOff, ShieldCheck } from "lucide-react"

export function NetworkStatus() {
    const t = useTranslations('network');
    const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)

    useEffect(() => {
        const handleOnline = () => setIsOnline(true)
        const handleOffline = () => setIsOnline(false)

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    return (
        <AnimatePresence>
            {!isOnline && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="bg-amber-500 text-amber-950 px-4 py-2 flex items-center justify-center gap-3 overflow-hidden text-xs font-bold shadow-lg z-[110] relative"
                >
                    <WifiOff className="w-4 h-4" />
                    <div className="flex items-center gap-4">
                        <span>{t('offlineMessage')}</span>
                        <div className="h-4 w-[1px] bg-amber-950/20" />
                        <span className="flex items-center gap-1.5 opacity-80 uppercase tracking-wider">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            {t('privacyGuaranteed')}
                        </span>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
