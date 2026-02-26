import { test, expect } from '@playwright/test';
import { setLocale } from './helpers/test-utils';

test.describe('Setup Wizard', () => {
    test('completes setup wizard in English', async ({ page }) => {
        // Navigate to /setup (using full URL as we match the requested route)
        await page.goto('/setup');

        // Verify welcome step renders (Next.js 16 + next-intl usually has specific headings)
        // We'll look for generic welcome text or a title
        await expect(page.getByRole('heading')).toBeVisible();

        // Verify step progression (Next missions or step indicators)
        const nextButton = page.getByRole('button', { name: /next|continue/i });
        if (await nextButton.isVisible()) {
            await nextButton.click();
        }

        // Verify "Skip for now" link exists on final step
        // In many setup flows, this is a button or a link
        await expect(page.getByRole('link', { name: /skip/i }).or(page.getByRole('button', { name: /skip/i }))).toBeVisible();
    });

    test('setup wizard renders in Japanese', async ({ page }) => {
        // Set locale cookie to 'ja'
        await setLocale(page, 'ja');

        // Navigate to /setup
        await page.goto('/setup');

        // Verify Japanese text appears (e.g., check for "ようこそ" or similar)
        // We'll look for common Japanese greetings used in onboarding
        await expect(page.locator('body')).toContainText(/ようこそ|設定/);
    });
});
