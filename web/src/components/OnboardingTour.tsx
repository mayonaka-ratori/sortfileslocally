"use client"

import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useTranslations } from "next-intl"
import {
    Search,
    Tags,
    Library,
    MessageSquare,
    Keyboard,
    Rocket,
    X,
    ArrowRight,
    ArrowLeft
} from "lucide-react"
import { updateAppSetting } from "@/lib/api"

export function OnboardingTour({
    onComplete
}: {
    onComplete: () => void
}) {
    const t = useTranslations("onboarding")
    const [currentStep, setCurrentStep] = useState(0)

    const handleDismiss = React.useCallback(async () => {
        try {
            await updateAppSetting("onboarding_dismissed", "true")
        } catch (e) {
            console.error(e)
        } finally {
            onComplete()
        }
    }, [onComplete])

    // Escape key to dismiss
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                handleDismiss()
            }
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [handleDismiss])

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(s => s + 1)
        } else {
            handleDismiss()
        }
    }

    const handleBack = () => {
        if (currentStep > 0) {
            setCurrentStep(s => s - 1)
        }
    }

    const steps = [
        {
            id: "search",
            icon: Search,
            title: t("step1Title"),
            desc: t("step1Desc"),
            color: "text-blue-400",
            bgUrl: "bg-blue-500/10"
        },
        {
            id: "tags",
            icon: Tags,
            title: t("step2Title"),
            desc: t("step2Desc"),
            color: "text-emerald-400",
            bgUrl: "bg-emerald-500/10"
        },
        {
            id: "albums",
            icon: Library,
            title: t("step3Title"),
            desc: t("step3Desc"),
            color: "text-amber-400",
            bgUrl: "bg-amber-500/10"
        },
        {
            id: "chat",
            icon: MessageSquare,
            title: t("step4Title"),
            desc: t("step4Desc"),
            color: "text-indigo-400",
            bgUrl: "bg-indigo-500/10"
        },
        {
            id: "shortcuts",
            icon: Keyboard,
            title: t("step5Title"),
            desc: t("step5Desc"),
            color: "text-purple-400",
            bgUrl: "bg-purple-500/10"
        },
        {
            id: "finish",
            icon: Rocket,
            title: t("step6Title"),
            desc: t("step6Desc"),
            color: "text-rose-400",
            bgUrl: "bg-rose-500/10"
        }
    ]

    const step = steps[currentStep]
    const Icon = step.icon
    const percent = Math.round(((currentStep + 1) / steps.length) * 100)

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Onboarding Tour"
            data-testid="onboarding-tour"
        >
            <div
                className="absolute inset-0"
                onClick={handleDismiss}
                aria-hidden="true"
            />

            <AnimatePresence mode="wait">
                <motion.div
                    key={step.id}
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -20, scale: 0.95 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                    className="relative w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-3xl shadow-2xl p-6 overflow-hidden focus:outline-none"
                    tabIndex={-1}
                >
                    {/* Header */}
                    <div className="flex justify-between items-start mb-6">
                        <div className={`w-14 h-14 rounded-2xl ${step.bgUrl} flex items-center justify-center border border-zinc-800`}>
                            <Icon className={`w-7 h-7 ${step.color}`} />
                        </div>
                        <button
                            onClick={handleDismiss}
                            className="text-zinc-500 hover:text-white p-2 rounded-full hover:bg-zinc-900 transition-colors"
                            aria-label={t("skip")}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="mb-8">
                        <h2 className="text-xl font-bold text-white mb-2 tracking-tight">
                            {step.title}
                        </h2>
                        <p className="text-zinc-400 text-sm leading-relaxed">
                            {step.desc}
                        </p>
                    </div>

                    {/* Progress Indicator */}
                    <div className="mb-6 space-y-2">
                        <div className="flex justify-between text-[11px] font-medium text-zinc-500 uppercase tracking-widest">
                            <span>{t("stepOf", { current: currentStep + 1, total: steps.length })}</span>
                            <span>{t("progress", { percent })}</span>
                        </div>
                        <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${percent}%` }}
                                className="h-full bg-indigo-500 rounded-full"
                                transition={{ duration: 0.3 }}
                            />
                        </div>
                    </div>

                    {/* Controls */}
                    <div className="flex items-center justify-between gap-3">
                        <button
                            onClick={handleDismiss}
                            className="text-xs font-semibold text-zinc-500 hover:text-zinc-300 transition-colors"
                        >
                            {t("skip")}
                        </button>
                        <div className="flex gap-2">
                            {currentStep > 0 && (
                                <button
                                    onClick={handleBack}
                                    className="p-2.5 rounded-xl border border-zinc-800 text-zinc-400 hover:bg-zinc-900 hover:text-white transition-colors"
                                    aria-label={t("back")}
                                >
                                    <ArrowLeft className="w-4 h-4" />
                                </button>
                            )}
                            <button
                                onClick={handleNext}
                                className="flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-zinc-200 text-zinc-950 text-sm font-bold rounded-xl transition-all active:scale-95"
                            >
                                {currentStep === steps.length - 1 ? t("finish") : (
                                    <>
                                        {t("next")}
                                        <ArrowRight className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    <div className="mt-4 text-center">
                        <p className="text-[10px] text-zinc-600">{t("restartHint")}</p>
                    </div>
                </motion.div>
            </AnimatePresence>
        </div>
    )
}
