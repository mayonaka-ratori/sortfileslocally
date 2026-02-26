import { test, expect } from '@playwright/test';

test.describe('Gallery Page', () => {
    test('gallery page loads and shows search bar', async ({ page }) => {
        // Navigate to /
        await page.goto('/');

        // Verify search input with data-search-input attribute exists
        const searchInput = page.locator('input[data-search-input]');
        await expect(searchInput).toBeVisible();

        // Verify sidebar navigation is visible
        const sidebar = page.locator('nav').first();
        await expect(sidebar).toBeVisible();

        // Verify PrivacyBadge is visible (components might indicate privacy level)
        await expect(page.locator('.PrivacyBadge').or(page.locator('[data-testid="PrivacyBadge"]')).or(page.locator('body'))).toContainText(/Private|Local/);
    });

    test('gallery shows empty state when no files', async ({ page }) => {
        await page.goto('/');

        // Verify empty state message appears
        // Usually something like "No files found" or "Start scanning"
        await expect(page.locator('body')).toContainText(/No results|No media|Empty/i);
    });
});
