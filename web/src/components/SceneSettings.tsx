"use client"

import React, { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { getAppSettings, updateAppSetting } from "@/lib/api";
import { toast } from "sonner";
import { Clapperboard, Sliders, Clock, Save, Loader2 } from "lucide-react";

export function SceneSettings() {
    const t = useTranslations('settings.video');
    const scenes = useTranslations('settings.scenes');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState({
        auto_scene_detection: false,
        scene_threshold: 27,
        max_video_duration: 7200,
    });

    useEffect(() => {
        async function loadSettings() {
            try {
                const data = await getAppSettings();
                // Since getAppSettings returns AppSettings which doesn't have these keys yet in the type,
                // we'll cast it or handle the potential missing keys.
                const s = data as unknown as Record<string, unknown>;
                setSettings({
                    auto_scene_detection: (s.auto_scene_detection as boolean) ?? false,
                    scene_threshold: (s.scene_threshold as number) ?? 27,
                    max_video_duration: (s.max_video_duration as number) ?? 7200,
                });
            } catch {
                console.error("Failed to load settings:");
            } finally {
                setLoading(false);
            }
        }
        loadSettings();
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            await Promise.all([
                updateAppSetting("auto_scene_detection", settings.auto_scene_detection.toString()),
                updateAppSetting("scene_threshold", settings.scene_threshold.toString()),
                updateAppSetting("max_video_duration", settings.max_video_duration.toString()),
            ]);
            toast.success(scenes('saveSuccess'));
        } catch {
            toast.error(scenes('saveFailed'));
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8 bg-zinc-900/50 rounded-xl border border-zinc-800">
                <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 space-y-6">
            <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
                <Clapperboard className="w-5 h-5 text-indigo-400" />
                <h3 className="text-sm font-bold uppercase tracking-wider">{t('sectionTitle')}</h3>
            </div>

            <div className="space-y-6">
                <div className="flex items-center justify-between group">
                    <div className="space-y-1">
                        <label className="text-sm font-bold text-zinc-200">{t('autoDetect')}</label>
                        <p className="text-[11px] text-zinc-500">{t('autoDetectDesc')}</p>
                    </div>
                    <button
                        onClick={() => setSettings(s => ({ ...s, auto_scene_detection: !s.auto_scene_detection }))}
                        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${settings.auto_scene_detection ? 'bg-indigo-600' : 'bg-zinc-700'}`}
                    >
                        <span
                            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${settings.auto_scene_detection ? 'translate-x-5' : 'translate-x-0'}`}
                        />
                    </button>
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Sliders className="w-4 h-4 text-zinc-500" />
                            <label className="text-sm font-bold text-zinc-200">{t('sensitivity')}</label>
                        </div>
                        <span className="text-xs font-mono text-indigo-400 font-bold bg-indigo-500/10 px-2 py-0.5 rounded">
                            {settings.scene_threshold}
                        </span>
                    </div>
                    <input
                        type="range"
                        min="15"
                        max="50"
                        value={settings.scene_threshold}
                        onChange={(e) => setSettings(s => ({ ...s, scene_threshold: parseInt(e.target.value) }))}
                        className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                    <div className="flex justify-between text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
                        <span>{t('fine')}</span>
                        <span>{t('coarse')}</span>
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-zinc-500" />
                            <label className="text-sm font-bold text-zinc-200">{t('maxDuration')}</label>
                        </div>
                        <input
                            type="number"
                            value={settings.max_video_duration}
                            onChange={(e) => setSettings(s => ({ ...s, max_video_duration: parseInt(e.target.value) || 0 }))}
                            className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs font-mono text-white w-24 focus:outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>
                    <p className="text-[11px] text-zinc-500">{t('maxDurationDesc')}</p>
                </div>
            </div>

            <div className="pt-4 flex justify-end">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-all shadow-lg shadow-indigo-900/40 active:scale-95"
                >
                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                    {t('saveButton')}
                </button>
            </div>
        </div>
    );
}

