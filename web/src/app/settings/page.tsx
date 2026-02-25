import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Settings as SettingsIcon } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { ModelManagerUI } from '@/components/Settings/ModelManagerUI';
import { DataManagementUI } from '@/components/Settings/DataManagementUI';
import { CleanerUI } from '@/components/Settings/CleanerUI';
import { SceneSettings } from '@/components/SceneSettings';
import { NetworkPrivacyUI } from '@/components/Settings/NetworkPrivacyUI';
import { LanguageSelector } from '@/components/LanguageSelector';

export default function SettingsPage() {
    const t = useTranslations('settings');
    const common = useTranslations('common');

    return (
        <main className="flex h-screen w-full bg-zinc-950 text-zinc-100 overflow-y-auto font-sans">
            <div className="max-w-4xl w-full mx-auto p-6 md:p-10 flex flex-col gap-8">
                {/* Header */}
                <div className="flex items-center gap-4 border-b border-zinc-800 pb-6">
                    <Link
                        href="/"
                        className="p-2 hover:bg-zinc-800 rounded-full transition-colors text-zinc-400 hover:text-white"
                        title={common('back')}
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight flex items-center gap-3">
                            <SettingsIcon className="w-6 h-6 text-indigo-500" />
                            {t('title')}
                        </h1>
                        <p className="text-zinc-500 text-sm mt-1">{t('subtitle')}</p>
                    </div>
                </div>

                {/* Appearance & Language Section */}
                <section className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold">{t('language.section')}</h2>
                    </div>
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
                        <LanguageSelector />
                    </div>
                </section>

                {/* Model Manager Section */}
                <section className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold">{t('models.title')}</h2>
                        <p className="text-xs text-zinc-400">{t('models.subtitle')}</p>
                    </div>

                    <ModelManagerUI />
                </section>

                {/* Data Management Section */}
                <section className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold">{t('data.title')}</h2>
                        <p className="text-xs text-zinc-400">{t('data.subtitle')}</p>
                    </div>

                    <DataManagementUI />
                </section>

                {/* Scene Settings Section */}
                <section className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold">{t('video.title')}</h2>
                        <p className="text-xs text-zinc-400">{t('video.subtitle')}</p>
                    </div>

                    <SceneSettings />
                </section>

                {/* Network & Privacy Section */}
                <section className="flex flex-col gap-4">
                    <NetworkPrivacyUI />
                </section>

                {/* Deduplication Section */}
                <section className="flex flex-col gap-4 mb-20">
                    <CleanerUI />
                </section>
            </div>
        </main>
    );
}
