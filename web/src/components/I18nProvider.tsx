"use client";
import { NextIntlClientProvider, AbstractIntlMessages } from 'next-intl';
import { useState, useEffect } from 'react';
import { initApiBase } from '@/lib/api';

export default function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<string | null>(null);
  const [messages, setMessages] = useState<AbstractIntlMessages | null>(null);

  useEffect(() => {
    const init = async () => {
      // Initialize API base URL (Tauri discovery)
      await initApiBase();

      const saved = localStorage.getItem('locale') || 'en';
      setLocale(saved);
      try {
        const m = await import(`../../messages/${saved}.json`);
        setMessages(m.default);
      } catch (err) {
        console.error(`Failed to load messages for ${saved}`, err);
        const fallback = await import(`../../messages/en.json`);
        setMessages(fallback.default);
      }
    };
    init();
  }, []);

  if (!messages || !locale) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
