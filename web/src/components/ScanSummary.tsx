"use client";
import React from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Files, SkipForward, AlertTriangle, Clock, ArrowRight, FolderSearch } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { ScanJobInfo } from "@/lib/api";

interface ScanSummaryProps {
    job: ScanJobInfo;
    onScanMore: () => void;
}

function formatElapsed(startedAt: number, completedAt: number): string {
    const elapsed = Math.max(0, (completedAt || Date.now() / 1000) - startedAt);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = Math.floor(elapsed % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

export function ScanSummary({ job, onScanMore }: ScanSummaryProps) {
    const t = useTranslations("scan");
    const router = useRouter();

    const stats = [
        {
            icon: <Files className="w-4 h-4 text-indigo-400" />,
            label: t("summaryNewFiles"),
            value: job.processed_count,
            color: "text-indigo-300",
        },
        {
            icon: <SkipForward className="w-4 h-4 text-zinc-400" />,
            label: t("summarySkipped"),
            value: job.skipped_count,
            color: "text-zinc-300",
        },
        {
            icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
            label: t("summaryErrors"),
            value: job.error_count,
            color: "text-amber-300",
        },
        {
            icon: <Clock className="w-4 h-4 text-emerald-400" />,
            label: t("summaryElapsed"),
            value: formatElapsed(job.started_at, job.completed_at),
            color: "text-emerald-300",
            isString: true,
        },
    ];

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="flex flex-col gap-5"
        >
            {/* Header */}
            <div className="flex flex-col items-center gap-3 py-2">
                <div className="relative">
                    <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center">
                        <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                    </div>
                    <motion.div
                        animate={{ scale: [1, 1.5, 1], opacity: [0.4, 0, 0.4] }}
                        transition={{ repeat: Infinity, duration: 2.5 }}
                        className="absolute inset-0 bg-emerald-500/20 rounded-full"
                    />
                </div>
                <div className="text-center">
                    <h3 className="text-lg font-bold text-zinc-100">{t("summaryTitle")}</h3>
                    <p className="text-xs text-zinc-500 mt-0.5">{job.target_path}</p>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-2">
                {stats.map((s, i) => (
                    <div
                        key={i}
                        className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3 flex flex-col gap-1"
                    >
                        <div className="flex items-center gap-1.5 text-xs text-zinc-500">
                            {s.icon}
                            <span>{s.label}</span>
                        </div>
                        <span className={`text-xl font-bold ${s.color}`}>
                            {s.isString ? s.value : (s.value as number).toLocaleString()}
                        </span>
                    </div>
                ))}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-2 pt-1">
                <button
                    id="scan-summary-go-to-gallery"
                    onClick={() => router.push("/")}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg shadow-indigo-500/20 text-sm"
                >
                    {t("goToGallery")}
                    <ArrowRight className="w-4 h-4" />
                </button>
                <button
                    id="scan-summary-scan-more"
                    onClick={onScanMore}
                    className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium py-2.5 rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95 text-sm border border-zinc-700"
                >
                    <FolderSearch className="w-4 h-4" />
                    {t("scanMore")}
                </button>
            </div>
        </motion.div>
    );
}
