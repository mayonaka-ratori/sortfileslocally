import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Settings as SettingsIcon } from 'lucide-react';
import { ModelManagerUI } from '@/components/Settings/ModelManagerUI';
import { DataManagementUI } from '@/components/Settings/DataManagementUI';
import { CleanerUI } from '@/components/Settings/CleanerUI';

export default function SettingsPage() {
    return (
        <main className="flex h-screen w-full bg-zinc-950 text-zinc-100 overflow-y-auto font-sans">
            <div className="max-w-4xl w-full mx-auto p-6 md:p-10 flex flex-col gap-8">
                {/* Header */}
                <div className="flex items-center gap-4 border-b border-zinc-800 pb-6">
                    <Link
                        href="/"
                        className="p-2 hover:bg-zinc-800 rounded-full transition-colors text-zinc-400 hover:text-white"
                        title="Back to Gallery"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight flex items-center gap-3">
                            <SettingsIcon className="w-6 h-6 text-indigo-500" />
                            Settings
                        </h1>
                        <p className="text-zinc-500 text-sm mt-1">Configure application preferences and manage AI models.</p>
                    </div>
                </div>

                {/* Model Manager Section */}
                <section className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold">AI Models</h2>
                        <p className="text-xs text-zinc-400">Download and manage the machine learning models required for analysis.</p>
                    </div>

                    <ModelManagerUI />
                </section>

                {/* Data Management Section */}
                <section className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-lg font-bold">Data Management</h2>
                        <p className="text-xs text-zinc-400">Manage and export data associated with your library.</p>
                    </div>

                    <DataManagementUI />
                </section>

                {/* Deduplication Section */}
                <section className="flex flex-col gap-4 mb-20">
                    <CleanerUI />
                </section>
            </div>
        </main>
    );
}
