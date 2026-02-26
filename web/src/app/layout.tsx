import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { SetupGuard } from "@/components/SetupGuard";
import { GlobalShortcuts } from "@/components/GlobalShortcuts";
import { NetworkStatus } from "@/components/NetworkStatus";
import I18nProvider from "@/components/I18nProvider";
import { NetworkLogProvider } from "@/stores/networkLogStore";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LocalCurator Prime",
  description: "AI-powered local media management and intelligent gallery",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <I18nProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <NetworkLogProvider>
              <SetupGuard>
                <NetworkStatus />
                {children}
                <GlobalShortcuts />
              </SetupGuard>
            </NetworkLogProvider>
          </ThemeProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
