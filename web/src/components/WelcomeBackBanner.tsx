"use client"

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Sparkles, ChevronRight, Info } from "lucide-react";
import { useTranslations } from "next-intl";
import changelog from "@/data/changelog.json";

interface Feature {
    version: string;
    date: string;
    features: string[];
}

export function WelcomeBackBanner() {
    const t = useTranslations("welcomeBack");
    const tw = useTranslations("whatsNew");
    const [isVisible, setIsVisible] = useState(false);
    const [showChangelog, setShowChangelog] = useState(false);

    useEffect(() => {
        // Check if dismissed in this session
        const isDismissed = sessionStorage.getItem("welcome_banner_dismissed");
        if (!isDismissed) {
            // Delay slightly for better entrance
            const timer = setTimeout(() => setIsVisible(true), 1000);
            return () => clearTimeout(timer);
        }
    }, []);

    const handleDismiss = () => {
        setIsVisible(false);
        sessionStorage.setItem("welcome_banner_dismissed", "true");
    };

    const latestVersion = changelog[0] as Feature;

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.4, ease: "circOut" }}
                    className="w-full bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-zinc-950 border-b border-indigo-500/20 overflow-hidden"
                >
                    <div className="max-w-[1600px] mx-auto px-4 py-6 sm:px-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                        <div className="flex items-start gap-4">
                            <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 flex items-center justify-center flex-shrink-0 border border-indigo-500/30">
                                <Sparkles className="w-6 h-6 text-indigo-400" />
                            </div>
                            <div className="space-y-1">
                                <h2 className="text-xl font-bold text-white tracking-tight">
                                    {t("title")}
                                </h2>
                                <div className="flex items-center gap-2">
                                    <p className="text-sm text-zinc-400">
                                        {t("subtitle")}:{" "}
                                        <span className="text-indigo-400 font-semibold">
                                            {tw("version", { version: latestVersion.version })}
                                        </span>
                                    </p>
                                    <button
                                        onClick={() => setShowChangelog(!showChangelog)}
                                        className="text-[10px] uppercase tracking-widest font-bold text-zinc-500 hover:text-indigo-400 transition-colors flex items-center gap-1"
                                    >
                                        <Info className="w-3 h-3" />
                                        {showChangelog ? "Hide" : "Details"}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 w-full md:w-auto">
                            <button
                                onClick={handleDismiss}
                                className="flex-1 md:flex-none px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-indigo-600/20"
                            >
                                {t("dismiss")}
                            </button>
                            <button
                                onClick={handleDismiss}
                                className="p-2.5 text-zinc-500 hover:text-white transition-colors"
                                aria-label="Close"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    <AnimatePresence>
                        {showChangelog && (
                            <motion.div
                                initial={{ height: 0 }}
                                animate={{ height: "auto" }}
                                exit={{ height: 0 }}
                                className="bg-zinc-900/50 backdrop-blur-md border-t border-zinc-800"
                            >
                                <div className="max-w-[1600px] mx-auto px-4 py-8 sm:px-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                                    {changelog.slice(0, 2).map((item) => (
                                        <div key={item.version} className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                                                    <span className="w-2 h-2 rounded-full bg-indigo-500" />
                                                    {tw("version", { version: item.version })}
                                                </h3>
                                                <span className="text-xs text-zinc-500 font-medium">
                                                    {item.date}
                                                </span>
                                            </div>
                                            <ul className="space-y-2">
                                                {item.features.map((feature, fidx) => (
                                                    <li
                                                        key={fidx}
                                                        className="text-sm text-zinc-400 flex items-start gap-2"
                                                    >
                                                        <ChevronRight className="w-4 h-4 text-indigo-500 mt-0.5" />
                                                        {feature}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
