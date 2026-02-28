import { test, expect } from '@playwright/test';

test.describe('Gallery Page', () => {
    test('gallery page loads and shows search bar', async ({ page }) => {
        // Navigate to /
        await page.goto('/');

        // Verify search bar wrapper
        const searchBar = page.locator('[data-testid="search-bar"]');
        await expect(searchBar).toBeVisible();

        // Verify search input with data-search-input attribute exists
        const searchInput = page.locator('input[data-search-input]');
        await expect(searchInput).toBeVisible();

        // Verify gallery grid exists
        const galleryGrid = page.locator('[data-testid="gallery-grid"]');
        await expect(galleryGrid).toBeVisible();

        // Verify sidebar navigation is visible
        const sidebar = page.locator('[data-testid="sidebar"]');
        await expect(sidebar).toBeVisible();

        // Verify PrivacyBadge is visible
        const privacyBadge = page.locator('[data-testid="privacy-badge"]');
        await expect(privacyBadge).toBeVisible();
        await expect(privacyBadge).toContainText(/Private|Local/);
    });

    test('gallery shows empty state when no files', async ({ page }) => {
        await page.goto('/');

        // Verify empty state message appears
        // Usually something like "No files found" or "Start scanning"
        await expect(page.locator('body')).toContainText(/No results|No media|Empty/i);
    });
});
