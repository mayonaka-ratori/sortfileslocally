import { test, expect } from '@playwright/test';
import { setLocale } from './helpers/test-utils';

test.describe('Setup Wizard', () => {
    test('completes setup wizard in English', async ({ page }) => {
        // Navigate to /setup (using full URL as we match the requested route)
        await page.goto('/setup');

        // Step 1: Welcome
        await expect(page.getByText(/Welcome to LocalCurator Prime/i)).toBeVisible();
        await page.getByRole('button', { name: /next/i }).click();

        // Step 2: Media
        await expect(page.getByText(/Tell us where your media is/i)).toBeVisible();
        await page.getByRole('button', { name: /next/i }).click();

        // Step 3: Performance
        await expect(page.getByText(/Hardware Profile/i)).toBeVisible();
        await page.getByRole('button', { name: /next/i }).click();

        // Step 4: Appearance
        await expect(page.getByText(/Appearance/i)).toBeVisible();
        await page.getByRole('button', { name: /next/i }).click();

        // Step 5: Finalize
        await expect(page.getByText(/You're all set/i)).toBeVisible();
        await expect(page.locator('#setup-skip-scan')).toBeVisible();
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
