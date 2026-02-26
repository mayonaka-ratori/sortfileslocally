"use client"

import React, { useState, useEffect } from "react";
import { Download, RefreshCw, CheckCircle2, History } from "lucide-react";
import { useTranslations } from "next-intl";
import { APP_VERSION } from "@/lib/version";
import { getAppSettings, updateAppSetting } from "@/lib/api";

// Type for the Tauri Update object
interface TauriUpdate {
    version: string;
    body?: string;
    downloadAndInstall: () => Promise<void>;
}

export function UpdateUI() {
    const t = useTranslations("update");
    const [update, setUpdate] = useState<TauriUpdate | null>(null);
    const [status, setStatus] = useState<"idle" | "checking" | "available" | "upToDate" | "downloading">("idle");
    const [lastChecked, setLastChecked] = useState<string | null>(null);
    const [autoCheck, setAutoCheck] = useState(true);

    useEffect(() => {
        const saved = localStorage.getItem("last_update_check");
        if (saved) setLastChecked(saved);

        // Fetch settings for auto-check toggle
        getAppSettings().then(settings => {
            // @ts-expect-error settings may contain auto_check_updates which is newly added
            setAutoCheck(settings.auto_check_updates !== "false");
        }).catch(console.error);
    }, []);

    const checkForUpdates = async () => {
        if (typeof window === "undefined" || !('__TAURI__' in window)) return;

        setStatus("checking");
        try {
            // @ts-expect-error Tauri plugin may not have types
            const { check } = await import("@tauri-apps/plugin-updater");
            const updateRes = await check();

            if (updateRes?.available) {
                setUpdate(updateRes as TauriUpdate);
                setStatus("available");
            } else {
                setStatus("upToDate");
            }

            const now = new Date().toLocaleString();
            setLastChecked(now);
            localStorage.setItem("last_update_check", now);
        } catch (err) {
            console.error("Failed to check for updates:", err);
            setStatus("idle");
        }
    };

    const handleInstall = async () => {
        if (!update) return;

        try {
            setStatus("downloading");
            await update.downloadAndInstall();

            // @ts-expect-error Tauri plugin may not have types
            const { relaunch } = await import("@tauri-apps/plugin-process");
            await relaunch();
        } catch (err) {
            console.error("Failed to install update:", err);
            setStatus("available");
        }
    };

    const toggleAutoCheck = async () => {
        const newValue = !autoCheck;
        setAutoCheck(newValue);
        try {
            await updateAppSetting("auto_check_updates", newValue.toString());
        } catch (err) {
            console.error("Failed to update auto-check setting:", err);
            setAutoCheck(!newValue); // Rollback
        }
    };

    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-6">
            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-zinc-800 flex items-center justify-center text-zinc-400">
                        <History className="w-6 h-6" />
                    </div>
                    <div>
                        <p className="text-sm font-bold text-white">
                            {t("currentVersion", { version: APP_VERSION })}
                        </p>
                        {lastChecked && (
                            <p className="text-xs text-zinc-500">
                                {t("lastChecked", { date: lastChecked })}
                            </p>
                        )}
                    </div>
                </div>

                <button
                    onClick={checkForUpdates}
                    disabled={status === "checking" || status === "downloading"}
                    className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-2"
                >
                    {status === "checking" ? (
                        <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : (
                        <RefreshCw className="w-3 h-3" />
                    )}
                    {t("checkButton")}
                </button>
            </div>

            {/* Auto-check Toggle */}
            <div className="flex items-center justify-between p-3 bg-zinc-950/40 rounded-lg border border-zinc-800/50">
                <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-bold text-white tracking-wide uppercase opacity-70">
                        Automation
                    </span>
                    <span className="text-sm font-medium text-zinc-300">
                        {t("autoCheck")}
                    </span>
                </div>
                <button
                    onClick={toggleAutoCheck}
                    className={`w-11 h-6 rounded-full transition-colors relative ${autoCheck ? 'bg-indigo-600' : 'bg-zinc-700'}`}
                >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${autoCheck ? 'left-6' : 'left-1'}`} />
                </button>
            </div>

            {status === "upToDate" && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    <p className="text-sm text-emerald-200 font-medium">
                        {t("upToDate")}
                    </p>
                </div>
            )}

            {update && status === "available" && (
                <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-6 space-y-4">
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-indigo-500 anim-pulse" />
                                {t("available", { version: update.version })}
                            </h3>
                            {update.body && (
                                <div className="mt-3 p-3 bg-zinc-950/50 rounded-lg border border-zinc-800">
                                    <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">
                                        {t("releaseNotes")}
                                    </p>
                                    <p className="text-sm text-zinc-400 whitespace-pre-wrap leading-relaxed">
                                        {update.body}
                                    </p>
                                </div>
                            )}
                        </div>
                        <button
                            onClick={handleInstall}
                            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-indigo-600/20 flex items-center gap-2 whitespace-nowrap"
                        >
                            <Download className="w-4 h-4" />
                            {t("updateNow")}
                        </button>
                    </div>
                </div>
            )}

            {status === "downloading" && (
                <div className="bg-indigo-600 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        <p className="text-sm font-bold">{t("downloading")}</p>
                    </div>
                </div>
            )}
        </div>
    );
}
