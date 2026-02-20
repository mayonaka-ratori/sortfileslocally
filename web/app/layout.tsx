
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import Sidebar from '@/components/layout/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
    title: 'LocalCurator Prime',
    description: 'AI-Powered Media Management',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className={inter.className + " bg-black min-h-screen text-white overflow-x-hidden"}>
                <Providers>
                    <div className="flex min-h-screen">
                        <Sidebar />
                        <div className="flex-1 ml-64 relative">
                            {children}
                        </div>
                    </div>
                </Providers>
            </body>
        </html>
    );
}
