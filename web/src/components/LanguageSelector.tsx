"use client"

import React, { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Languages, Check, Loader2 } from "lucide-react"
import { getAppSettings, updateAppSetting } from "@/lib/api"

export function LanguageSelector() {
    const [locale, setLocale] = useState<string>("en")
    const [loading, setLoading] = useState(true)
    const [isUpdating, setIsUpdating] = useState(false)
    const router = useRouter()

    useEffect(() => {
        getAppSettings()
            .then(settings => {
                setLocale(settings.locale || "en")
            })
            .finally(() => setLoading(false))
    }, [])

    const handleLocaleChange = async (newLocale: string) => {
        if (newLocale === locale || isUpdating) return

        setIsUpdating(true)
        try {
            await updateAppSetting("locale", newLocale)

            // Set cookie for next-intl (as per standard next-intl setup with cookies)
            document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000; SameSite=Lax`

            setLocale(newLocale)
            router.refresh()
        } catch (err) {
            console.error("Failed to update locale:", err)
        } finally {
            setIsUpdating(false)
        }
    }

    if (loading) return (
        <div className="w-full h-10 bg-zinc-900/50 rounded-xl animate-pulse" />
    )

    const languages = [
        { code: "en", name: "English", flag: "🇺🇸" },
        { code: "ja", name: "日本語", flag: "🇯🇵" }
    ]

    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-zinc-400 mb-1">
                <Languages className="w-4 h-4" />
                <span className="text-[10px] font-bold uppercase tracking-widest">Language / 言語</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
                {languages.map((lang) => (
                    <button
                        key={lang.code}
                        onClick={() => handleLocaleChange(lang.code)}
                        disabled={isUpdating}
                        className={`
                            flex items-center justify-between px-4 py-3 rounded-xl border transition-all
                            ${locale === lang.code
                                ? "bg-indigo-600/10 border-indigo-600 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.1)]"
                                : "bg-zinc-950/40 border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
                            }
                        `}
                    >
                        <div className="flex items-center gap-3">
                            <span className="text-lg">{lang.flag}</span>
                            <span className="text-sm font-semibold">{lang.name}</span>
                        </div>
                        {isUpdating && locale !== lang.code && (
                            <Loader2 className="w-4 h-4 animate-spin opacity-50" />
                        )}
                        {locale === lang.code && !isUpdating && (
                            <Check className="w-4 h-4" />
                        )}
                    </button>
                ))}
            </div>
        </div>
    )
}
