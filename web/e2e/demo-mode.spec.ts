import { test, expect } from '@playwright/test';

test.describe('Demo Mode', () => {
    test('start demo mode from setup wizard', async ({ page }) => {
        await page.goto('/setup');

        // Go to Step 2 (Media)
        await page.getByRole('button', { name: /next/i }).click();

        // Click "Try with demo images" button
        // Looking at SetupWizard code, it has t('demoButton')
        const demoButton = page.getByRole('button', { name: /Try with demo images/i });
        await expect(demoButton).toBeVisible();
        await demoButton.click();

        // It should skip to step 5 and show "All set" or "Scanning"
        await expect(page.getByText(/You're all set/i).or(page.getByText(/Scanning/i))).toBeVisible();

        // Click "Start Explorer" or similar (id="setup-skip-scan" in Step 5 is Skip Scan, handleComplete starts scan)
        // If startDemo was called, it goes to step 5.
        const skipScan = page.locator('#setup-skip-scan');
        await skipScan.click();

        // Should land on gallery
        await expect(page).toHaveURL('/');
        await expect(page.locator('[data-testid="gallery-grid"]')).toBeVisible();
    });
});
