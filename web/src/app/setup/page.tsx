"use client"
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronRight,
    ChevronLeft,
    FolderPlus,
    Cpu,
    Sun,
    Moon,
    Settings2,
    CheckCircle2,
    Zap,
    ShieldCheck,
    Monitor,
    Loader2,
    Sparkles,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { useTranslations } from 'next-intl';
import { browseFolder, updateAppSetting, completeSetup, startScan } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { LanguageSelector } from '@/components/LanguageSelector';

export default function SetupWizard() {
    const t = useTranslations('setup');
    const common = useTranslations('common');
    const [step, setStep] = useState(1);
    const [mediaPath, setMediaPath] = useState('');
    const [profile, setProfile] = useState('balanced');
    const [isSaving, setIsSaving] = useState(false);
    const { theme, setTheme } = useTheme();
    const router = useRouter();

    const nextStep = () => setStep(prev => Math.min(prev + 1, 5));
    const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

    const handleBrowseFolders = async () => {
        try {
            const res = await browseFolder();
            if (!res.cancelled && res.path) {
                setMediaPath(res.path);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleComplete = async () => {
        setIsSaving(true);
        try {
            await updateAppSetting('execution_profile', profile);
            await updateAppSetting('theme', theme || 'system');

            if (mediaPath) {
                await startScan(mediaPath);
            }

            await completeSetup();
            router.push('/');
            router.refresh();
        } catch (err) {
            console.error(err);
            alert(t('errors.completeFailed'));
        } finally {
            setIsSaving(false);
        }
    };

    const profilesList = [
        {
            id: 'performance',
            name: t('performance.profiles.performance'),
            vram: t('hardware.vram8gb'),
            desc: t('performance.profiles.performanceDesc'),
            icon: <Zap className="w-5 h-5 text-yellow-500" />
        },
        {
            id: 'balanced',
            name: t('performance.profiles.balanced'),
            vram: t('hardware.vram4gb'),
            desc: t('performance.profiles.balancedDesc'),
            icon: <Settings2 className="w-5 h-5 text-indigo-500" />
        },
        {
            id: 'lightweight',
            name: t('performance.profiles.lightweight'),
            vram: t('hardware.vramMinimal'),
            desc: t('performance.profiles.lightweightDesc'),
            icon: <ShieldCheck className="w-5 h-5 text-emerald-500" />
        }
    ];

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center p-6 font-sans">
            {/* Background decorative elements */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 blur-[120px] rounded-full" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 blur-[120px] rounded-full" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-2xl bg-zinc-900/50 border border-zinc-800 rounded-3xl overflow-hidden backdrop-blur-xl shadow-2xl relative z-10"
            >
                {/* Progress Bar */}
                <div className="h-1 bg-zinc-800 w-full relative">
                    <motion.div
                        initial={{ width: '20%' }}
                        animate={{ width: `${(step / 5) * 100}%` }}
                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-indigo-500 to-purple-500"
                    />
                </div>

                <div className="p-8 sm:p-12">
                    <AnimatePresence mode="wait">
                        {step === 1 && (
                            <motion.div
                                key="step1"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-6"
                            >
                                <div className="space-y-2">
                                    <div className="w-12 h-12 bg-indigo-500/20 rounded-2xl flex items-center justify-center mb-4">
                                        <Sparkles className="w-6 h-6 text-indigo-500" />
                                    </div>
                                    <h1 className="text-3xl font-bold tracking-tight">{t('welcome.title')}</h1>
                                    <p className="text-zinc-400 leading-relaxed">
                                        {t('welcome.desc')}
                                    </p>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4">
                                    <div className="p-4 bg-zinc-950/40 rounded-2xl border border-zinc-800/50">
                                        <h3 className="text-sm font-semibold mb-1 flex items-center gap-2">
                                            <Zap className="w-4 h-4 text-indigo-400" /> {t('welcome.feature1')}
                                        </h3>
                                        <p className="text-xs text-zinc-500">{t('welcome.feature1Desc')}</p>
                                    </div>
                                    <div className="p-4 bg-zinc-950/40 rounded-2xl border border-zinc-800/50">
                                        <h3 className="text-sm font-semibold mb-1 flex items-center gap-2">
                                            <Cpu className="w-4 h-4 text-purple-400" /> {t('welcome.feature2')}
                                        </h3>
                                        <p className="text-xs text-zinc-500">{t('welcome.feature2Desc')}</p>
                                    </div>
                                </div>

                                <div className="pt-8 border-t border-zinc-800/50">
                                    <LanguageSelector />
                                </div>
                            </motion.div>
                        )}

                        {step === 2 && (
                            <motion.div
                                key="step2"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-6"
                            >
                                <div className="space-y-2">
                                    <h2 className="text-2xl font-bold tracking-tight">{t('media.title')}</h2>
                                    <p className="text-zinc-400">{t('media.desc')}</p>
                                </div>
                                <div className="space-y-4 pt-4">
                                    <div className="flex gap-2">
                                        <div className="relative flex-1">
                                            <input
                                                type="text"
                                                readOnly
                                                value={mediaPath}
                                                placeholder={t('media.placeholder')}
                                                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500/50 transition-colors pl-12"
                                            />
                                            <FolderPlus className="w-5 h-5 absolute left-4 top-3 text-zinc-600" />
                                        </div>
                                        <button
                                            onClick={handleBrowseFolders}
                                            className="bg-indigo-600 hover:bg-indigo-500 text-sm font-medium px-6 py-3 rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
                                        >
                                            {common('browse')}
                                        </button>
                                    </div>
                                    <p className="text-[11px] text-zinc-500 bg-indigo-500/5 border border-indigo-500/10 p-3 rounded-lg leading-relaxed">
                                        {t('media.privacyNote')}
                                    </p>
                                </div>
                            </motion.div>
                        )}

                        {step === 3 && (
                            <motion.div
                                key="step3"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-6"
                            >
                                <div className="space-y-2">
                                    <h2 className="text-2xl font-bold tracking-tight">{t('performance.title')}</h2>
                                    <p className="text-zinc-400">{t('performance.desc')}</p>
                                </div>
                                <div className="grid grid-cols-1 gap-3 pt-4">
                                    {profilesList.map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => setProfile(p.id)}
                                            className={`p-4 rounded-2xl border transition-all text-left flex gap-4 items-start ${profile === p.id
                                                ? 'bg-indigo-500/5 border-indigo-500 shadow-[0_0_20px_rgba(99,102,241,0.1)]'
                                                : 'bg-zinc-950/40 border-zinc-800 hover:border-zinc-700'
                                                }`}
                                        >
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${profile === p.id ? 'bg-indigo-500/20' : 'bg-zinc-900'
                                                }`}>
                                                {p.icon}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex justify-between items-center mb-1">
                                                    <h3 className="font-semibold text-zinc-100">{p.name}</h3>
                                                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${profile === p.id ? 'bg-indigo-500/10 text-indigo-400' : 'bg-zinc-900 text-zinc-500'
                                                        }`}>
                                                        {p.vram}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-zinc-500 leading-relaxed">{p.desc}</p>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        {step === 4 && (
                            <motion.div
                                key="step4"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-6"
                            >
                                <div className="space-y-2">
                                    <h2 className="text-2xl font-bold tracking-tight">{t('appearance.title')}</h2>
                                    <p className="text-zinc-400">{t('appearance.desc')}</p>
                                </div>
                                <div className="grid grid-cols-3 gap-4 pt-4">
                                    {[
                                        { id: 'light', name: t('appearance.themes.light'), icon: <Sun className="w-6 h-6" /> },
                                        { id: 'dark', name: t('appearance.themes.dark'), icon: <Moon className="w-6 h-6" /> },
                                        { id: 'system', name: t('appearance.themes.system'), icon: <Monitor className="w-6 h-6" /> }
                                    ].map((t) => (
                                        <button
                                            key={t.id}
                                            onClick={() => setTheme(t.id)}
                                            className={`flex flex-col items-center gap-3 p-6 rounded-2xl border transition-all ${theme === t.id
                                                ? 'bg-indigo-500/5 border-indigo-500'
                                                : 'bg-zinc-950/40 border-zinc-800 hover:border-zinc-700'
                                                }`}
                                        >
                                            <div className={`${theme === t.id ? 'text-indigo-500' : 'text-zinc-500'}`}>
                                                {t.icon}
                                            </div>
                                            <span className="text-xs font-medium">{t.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        {step === 5 && (
                            <motion.div
                                key="step5"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-6 text-center"
                            >
                                <div className="py-4 flex justify-center">
                                    <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center relative">
                                        <CheckCircle2 className="w-10 h-10 text-emerald-500" />
                                        <motion.div
                                            animate={{ scale: [1, 1.2, 1], opacity: [0, 0.5, 0] }}
                                            transition={{ repeat: Infinity, duration: 2 }}
                                            className="absolute inset-0 bg-emerald-500 rounded-full"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <h2 className="text-2xl font-bold tracking-tight">{t('ready.title')}</h2>
                                    <p className="text-zinc-400">{t('ready.desc')}</p>
                                </div>
                                <div className="bg-zinc-950/40 border border-zinc-800 rounded-2xl p-6 text-left space-y-3">
                                    <div className="flex justify-between text-xs">
                                        <span className="text-zinc-500 uppercase tracking-widest font-bold">{t('ready.mediaPath')}</span>
                                        <span className="text-zinc-300 truncate pl-4 max-w-[240px]">{mediaPath || t('ready.notSelected')}</span>
                                    </div>
                                    <div className="flex justify-between text-xs">
                                        <span className="text-zinc-500 uppercase tracking-widest font-bold">{t('ready.profile')}</span>
                                        <span className="text-zinc-300 capitalize">{profile}</span>
                                    </div>
                                    <div className="flex justify-between text-xs">
                                        <span className="text-zinc-500 uppercase tracking-widest font-bold">{t('ready.theme')}</span>
                                        <span className="text-zinc-300 capitalize">{theme}</span>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Navigation */}
                    <div className="flex justify-between items-center mt-12 pt-8 border-t border-zinc-800/50">
                        <button
                            disabled={step === 1 || isSaving}
                            onClick={prevStep}
                            className="flex items-center gap-2 text-sm font-medium text-zinc-400 hover:text-zinc-100 disabled:opacity-0 transition-opacity px-2"
                        >
                            <ChevronLeft className="w-4 h-4" />
                            {t('footer.back')}
                        </button>

                        {step < 5 ? (
                            <button
                                onClick={nextStep}
                                className="bg-zinc-100 hover:bg-white text-zinc-950 text-sm font-bold px-8 py-3 rounded-xl flex items-center gap-2 transition-all active:scale-95 shadow-xl shadow-white/5"
                            >
                                {t('footer.next')}
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                onClick={handleComplete}
                                disabled={isSaving}
                                className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold px-10 py-3 rounded-xl flex items-center gap-2 transition-all active:scale-95 shadow-xl shadow-indigo-500/20 disabled:opacity-50"
                            >
                                {isSaving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        {t('footer.finalizing')}
                                    </>
                                ) : (
                                    <>
                                        {t('footer.start')}
                                        <CheckCircle2 className="w-4 h-4 text-white/80" />
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
