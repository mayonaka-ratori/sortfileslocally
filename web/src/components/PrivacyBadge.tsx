"use client"

import React from "react"
import { Shield, ShieldAlert } from "lucide-react"
import { useTranslations } from "next-intl"
import { useNetworkLog } from "@/stores/networkLogStore"

export function PrivacyBadge() {
    const t = useTranslations('privacy');
    const { logs } = useNetworkLog();

    // Check if any log is not local and not blocked
    const hasExternal = logs.some(log => !log.isLocal && log.status !== 'blocked');

    return (
        <div className="group relative" data-testid="privacy-badge">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${hasExternal
                ? "bg-amber-500/10 border-amber-500/20 text-amber-500"
                : "bg-green-500/10 border-green-500/20 text-green-500 shadow-[0_0_10px_rgba(34,197,94,0.1)]"
                }`}>
                {hasExternal ? (
                    <>
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>{t('externalDetected')}</span>
                    </>
                ) : (
                    <>
                        <Shield className="w-3.5 h-3.5" />
                        <span>{t('localOnly')}</span>
                    </>
                )}
            </div>

            {/* Tooltip */}
            <div className="absolute left-full ml-3 px-2 py-1 bg-zinc-800 text-zinc-100 text-[10px] rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50 border border-zinc-700 shadow-xl">
                {t('badgeTooltip')}
                {/* Arrow */}
                <div className="absolute top-1/2 -left-1 -translate-y-1/2 w-2 h-2 bg-zinc-800 border-l border-b border-zinc-700 rotate-45" />
            </div>
        </div>
    )
}
