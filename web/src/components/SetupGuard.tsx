"use client"

import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { getAppSettings } from '@/lib/api';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';

export function SetupGuard({ children }: { children: React.ReactNode }) {
    const t = useTranslations("common");
    const [loading, setLoading] = useState(true);
    const pathname = usePathname();
    const router = useRouter();

    useEffect(() => {
        async function checkSetup() {
            try {
                const settings = await getAppSettings();

                if (!settings.setup_completed && pathname !== '/setup') {
                    router.push('/setup');
                } else if (settings.setup_completed && pathname === '/setup') {
                    router.push('/');
                }
            } catch (error) {
                console.error("Failed to check setup status:", error);
            } finally {
                setLoading(false);
            }
        }

        checkSetup();
    }, [pathname, router]);

    if (loading && pathname !== '/setup') {
        return (
            <div className="fixed inset-0 bg-zinc-950 flex flex-col items-center justify-center z-50">
                <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mb-4" />
                <p className="text-zinc-400 font-medium">{t("checkingStatus")}</p>
            </div>
        );
    }

    return <>{children}</>;
}
