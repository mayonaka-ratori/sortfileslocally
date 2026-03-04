import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';

type Profile = 'lightweight' | 'balanced' | 'full';

export default function FirstRunWizard() {
    const t = useTranslations('firstRun');
    const [step, setStep] = useState(1);
    const [profile, setProfile] = useState<Profile>('lightweight');
    const [progress, setProgress] = useState<Record<string, number>>({});
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        if (step === 3) {
            const startDownload = async () => {
                await fetch('http://localhost:8000/setup/download-model', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile }),
                });

                const eventSource = new EventSource('http://localhost:8000/setup/download-progress/stream');
                eventSource.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    setProgress(data);

                    // Check if all are 100%
                    const values = Object.values(data) as number[];
                    if (values.length > 0 && values.every((v: number) => v === 100)) {
                        setIsReady(true);
                        setStep(4);
                        eventSource.close();
                        localStorage.setItem('first_run_completed', 'true');
                    }
                };

                return () => {
                    eventSource.close();
                };
            };
            startDownload();
        }
    }, [step, profile]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-neutral-900 text-white p-8">
            <div className="max-w-xl w-full bg-neutral-800 p-8 rounded-xl shadow-2xl">
                {step === 1 && (
                    <div className="space-y-4">
                        <h1 className="text-3xl font-bold">{t('welcome.title')}</h1>
                        <p className="text-neutral-300">
                            {t('welcome.description')}
                        </p>
                        <button
                            className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-500 rounded font-semibold transition"
                            onClick={() => setStep(2)}
                        >
                            {t('welcome.next')}
                        </button>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-4">
                        <h1 className="text-2xl font-bold">{t('modelSelect.title')}</h1>
                        <div className="space-y-2">
                            <label className="flex items-center space-x-3 p-3 bg-neutral-700 rounded cursor-pointer">
                                <input type="radio" name="profile" checked={profile === 'lightweight'} onChange={() => setProfile('lightweight')} />
                                <div>
                                    <div className="font-bold">{t('modelSelect.lightweight')}</div>
                                    <div className="text-sm text-neutral-400">{t('modelSelect.lightweightDesc')}</div>
                                </div>
                            </label>

                            <label className="flex items-center space-x-3 p-3 bg-neutral-700 rounded cursor-pointer">
                                <input type="radio" name="profile" checked={profile === 'balanced'} onChange={() => setProfile('balanced')} />
                                <div>
                                    <div className="font-bold">{t('modelSelect.balanced')}</div>
                                    <div className="text-sm text-neutral-400">{t('modelSelect.balancedDesc')}</div>
                                </div>
                            </label>

                            <label className="flex items-center space-x-3 p-3 bg-neutral-700 rounded cursor-pointer">
                                <input type="radio" name="profile" checked={profile === 'full'} onChange={() => setProfile('full')} />
                                <div>
                                    <div className="font-bold">{t('modelSelect.full')}</div>
                                    <div className="text-sm text-neutral-400">{t('modelSelect.fullDesc')}</div>
                                </div>
                            </label>
                        </div>

                        <button
                            className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-500 rounded font-semibold transition"
                            onClick={() => setStep(3)}
                        >
                            {t('modelSelect.download')}
                        </button>
                    </div>
                )}

                {step === 3 && (
                    <div className="space-y-4">
                        <h1 className="text-2xl font-bold">{t('download.title')}</h1>
                        <div className="space-y-4">
                            {Object.entries(progress).map(([name, pct]) => (
                                <div key={name}>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>{name}</span>
                                        <span>{Math.round(pct)}%</span>
                                    </div>
                                    <div className="w-full bg-neutral-700 rounded-full h-2">
                                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${pct}%` }}></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {step === 4 && (
                    <div className="space-y-4">
                        <h1 className="text-3xl font-bold text-green-400">{t('ready.title')}</h1>
                        <p className="text-neutral-300">
                            {t('ready.description')}
                        </p>
                        <button
                            className="mt-4 px-6 py-2 bg-green-600 hover:bg-green-500 rounded font-semibold transition"
                            onClick={() => window.location.reload()}
                        >
                            {t('ready.startScan')}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
