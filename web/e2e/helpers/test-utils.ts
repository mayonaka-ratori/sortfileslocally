import { Page } from '@playwright/test';

export const API_BASE = 'http://localhost:8000';

/**
 * Polling function to wait until the application is ready.
 */
export async function waitForApp(page: Page, timeout = 30000) {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
        try {
            const response = await page.goto('/');
            if (response && response.status() === 200) {
                return;
            }
        } catch {
            // Ignore errors and retry
        }
        await page.waitForTimeout(1000);
    }
    throw new Error(`Application failed to become ready within ${timeout}ms`);
}

/**
 * Sets the NEXT_LOCALE cookie to change the language.
 */
export async function setLocale(page: Page, locale: 'en' | 'ja') {
    await page.context().addCookies([
        {
            name: 'NEXT_LOCALE',
            value: locale,
            domain: 'localhost',
            path: '/',
        },
    ]);
    await page.reload();
}
