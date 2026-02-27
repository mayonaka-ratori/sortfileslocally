"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { getAppSettings, updateAppSetting } from "@/lib/api";
import { Loader2, Settings2, Save } from "lucide-react";
import { toast } from "sonner";

interface SettingsState {
    auto_scene_detection: boolean;
    scene_threshold: number;
    max_video_duration: number;
}

export function SceneSettings() {
    const scenes = useTranslations("scenes");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState<SettingsState>({
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
            } catch (err) {
                console.error("Failed to load settings:", err);
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
        } catch (err) {
            console.error("Failed to save settings:", err);
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
        <div className="space-y-6">
            <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-indigo-500/10 rounded-lg">
                    <Settings2 className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-white">{scenes('settingsTitle')}</h2>
                    <p className="text-xs text-zinc-500">{scenes('settingsDesc')}</p>
                </div>
            </div>

            <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-sm font-semibold text-zinc-200">{scenes('autoDetect')}</h3>
                        <p className="text-xs text-zinc-500">{scenes('autoDetectDesc')}</p>
                    </div>
                    <button
                        onClick={() => setSettings(prev => ({ ...prev, auto_scene_detection: !prev.auto_scene_detection }))}
                        className={`w-12 h-6 rounded-full transition-colors relative ${settings.auto_scene_detection ? 'bg-indigo-600' : 'bg-zinc-700'}`}
                    >
                        <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${settings.auto_scene_detection ? 'left-7' : 'left-1'}`} />
                    </button>
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-zinc-200">{scenes('threshold')}</h3>
                        <span className="text-xs font-mono text-indigo-400">{settings.scene_threshold}</span>
                    </div>
                    <input
                        type="range"
                        min="10"
                        max="50"
                        step="0.5"
                        value={settings.scene_threshold}
                        onChange={(e) => setSettings(prev => ({ ...prev, scene_threshold: parseFloat(e.target.value) }))}
                        className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                    <p className="text-[10px] text-zinc-600">{scenes('thresholdHelp')}</p>
                </div>

                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-zinc-200">{scenes('maxDuration')}</h3>
                        <span className="text-xs font-mono text-indigo-400">{Math.floor(settings.max_video_duration / 60)} {scenes('minutes')}</span>
                    </div>
                    <select
                        value={settings.max_video_duration}
                        onChange={(e) => setSettings(prev => ({ ...prev, max_video_duration: parseInt(e.target.value) }))}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
                    >
                        <option value={1800}>30 {scenes('minutes')}</option>
                        <option value={3600}>1 {scenes('hour')}</option>
                        <option value={7200}>2 {scenes('hours')}</option>
                        <option value={14400}>4 {scenes('hours')}</option>
                    </select>
                    <p className="text-[10px] text-zinc-600">{scenes('maxDurationHelp')}</p>
                </div>

                <div className="pt-2">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-all shadow-lg shadow-indigo-900/20"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        {scenes('saveSettings')}
                    </button>
                </div>
            </div>
        </div>
    );
}
