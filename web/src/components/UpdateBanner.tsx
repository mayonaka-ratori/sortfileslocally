"use client"

import React, { useState, useEffect } from "react";
import { Download, RefreshCw, X, ChevronRight, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslations } from "next-intl";
import { APP_VERSION } from "@/lib/version";

// Type for the Tauri Update object
interface TauriUpdate {
    version: string;
    body?: string;
    downloadAndInstall: () => Promise<void>;
}

export function UpdateBanner() {
    const t = useTranslations("update");
    const [update, setUpdate] = useState<TauriUpdate | null>(null);
    const [isVisible, setIsVisible] = useState(false);
    const [status, setStatus] = useState<"available" | "downloading" | "installed">("available");

    useEffect(() => {
        const checkUpdates = async () => {
            // Check if running in Tauri
            if (typeof window === "undefined" || !('__TAURI__' in window)) return;

            // Check if already dismissed this session
            if (sessionStorage.getItem("update_banner_dismissed") === "true") return;

            try {
                // @ts-expect-error Tauri plugin may not have types in some environments
                const { check } = await import("@tauri-apps/plugin-updater");
                const updateRes = await check();

                if (updateRes?.available) {
                    setUpdate(updateRes as TauriUpdate);
                    setIsVisible(true);
                }
            } catch (err) {
                console.error("Failed to check for updates:", err);
            }
        };

        const timer = setTimeout(checkUpdates, 2000); // Check 2s after mount
        return () => clearTimeout(timer);
    }, []);

    const handleInstall = async () => {
        if (!update) return;

        try {
            setStatus("downloading");
            await update.downloadAndInstall();
            setStatus("installed");
        } catch (err) {
            console.error("Failed to install update:", err);
            setStatus("available");
        }
    };

    const handleDismiss = () => {
        setIsVisible(false);
        sessionStorage.setItem("update_banner_dismissed", "true");
    };

    const handleRestart = async () => {
        try {
            // @ts-expect-error Tauri plugin may not have types in some environments
            const { relaunch } = await import("@tauri-apps/plugin-process");
            await relaunch();
        } catch (err) {
            console.error("Failed to relaunch:", err);
        }
    };

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden mb-6"
                >
                    <div className="bg-gradient-to-r from-indigo-600 to-violet-600 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xl shadow-indigo-500/20 group relative overflow-hidden">
                        {/* Animated background particles */}
                        <div className="absolute inset-0 overflow-hidden pointer-events-none">
                            <div className="absolute -top-1/2 -left-1/4 w-1/2 h-full bg-white/5 blur-3xl transform -rotate-12 translate-x-0 group-hover:translate-x-full transition-transform duration-1000" />
                        </div>

                        <div className="flex items-center gap-4 relative z-10">
                            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                                {status === "downloading" ? (
                                    <RefreshCw className="w-5 h-5 text-white animate-spin" />
                                ) : status === "installed" ? (
                                    <CheckCircle2 className="w-5 h-5 text-emerald-300" />
                                ) : (
                                    <Download className="w-5 h-5 text-white" />
                                )}
                            </div>
                            <div>
                                <h3 className="text-sm font-black text-white flex items-center gap-2">
                                    {status === "installed"
                                        ? t("restartRequired")
                                        : t("available", { version: update?.version ?? "" })}
                                    <span className="text-[10px] bg-white/20 px-1.5 py-0.5 rounded text-indigo-100 font-mono">
                                        v{APP_VERSION} → v{update?.version}
                                    </span>
                                </h3>
                                <p className="text-xs text-indigo-100 font-medium">
                                    {status === "downloading"
                                        ? t("downloading")
                                        : status === "installed"
                                            ? t("restartRequired")
                                            : "A new version of LocalCurator Prime is ready to download."}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 relative z-10">
                            {status === "available" && (
                                <>
                                    <button
                                        onClick={handleDismiss}
                                        className="px-4 py-2 hover:bg-white/10 text-white text-xs font-bold rounded-lg transition-colors"
                                    >
                                        {t("later")}
                                    </button>
                                    <button
                                        onClick={handleInstall}
                                        className="px-5 py-2 bg-white text-indigo-600 hover:bg-indigo-50 text-xs font-black rounded-lg transition-all active:scale-95 flex items-center gap-2 shadow-lg"
                                    >
                                        {t("updateNow")}
                                        <ChevronRight className="w-4 h-4" />
                                    </button>
                                </>
                            )}

                            {status === "installed" && (
                                <button
                                    onClick={handleRestart}
                                    className="px-5 py-2 bg-emerald-500 text-white hover:bg-emerald-400 text-xs font-black rounded-lg transition-all active:scale-95 flex items-center gap-2 shadow-lg"
                                >
                                    {t("restartRequired")}
                                    <RefreshCw className="w-4 h-4" />
                                </button>
                            )}

                            <button
                                onClick={handleDismiss}
                                className="p-2 hover:bg-white/10 text-indigo-100 rounded-lg transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
