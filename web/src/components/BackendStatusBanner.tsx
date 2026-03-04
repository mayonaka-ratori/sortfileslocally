"use client"

import React from "react"
import { useBackendHealth } from "@/hooks/useBackendHealth"
import { motion, AnimatePresence } from "framer-motion"
import { Loader2, ServerCrash } from "lucide-react"
import { useTranslations } from "next-intl"

export function BackendStatusBanner() {
    const { status, retryNow } = useBackendHealth()
    const t = useTranslations('common') // Fallback to common if network not found

    return (
        <AnimatePresence>
            {status !== 'healthy' && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className={`px-4 py-2 flex items-center justify-center gap-3 overflow-hidden text-xs font-bold shadow-lg z-[110] relative ${status === 'unhealthy' ? 'bg-red-500 text-red-950' : 'bg-amber-500 text-amber-950'
                        }`}
                >
                    {status === 'unhealthy' ? (
                        <ServerCrash className="w-4 h-4 shrink-0" />
                    ) : (
                        <Loader2 className="w-4 h-4 shrink-0 animate-spin" />
                    )}

                    <div className="flex items-center gap-4">
                        <span>
                            {status === 'connecting' && "バックエンド起動中 / Connecting to backend..."}
                            {status === 'recovering' && "再接続中 / Reconnecting..."}
                            {status === 'unhealthy' && "バックエンドと通信できません。 / Cannot communicate with backend."}
                        </span>

                        {status === 'unhealthy' && (
                            <>
                                <div className="h-4 w-[1px] bg-red-950/20" />
                                <button
                                    onClick={retryNow}
                                    className="px-2 py-0.5 bg-red-950/10 hover:bg-red-950/20 rounded transition-colors"
                                >
                                    再試行 / Retry
                                </button>
                            </>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
