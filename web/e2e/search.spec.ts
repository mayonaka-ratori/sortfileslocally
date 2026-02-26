import { test, expect } from '@playwright/test';

test.describe('Search Functionality', () => {
    test('search bar accepts input and submits', async ({ page }) => {
        // Navigate to /
        await page.goto('/');

        // Click search input
        const searchInput = page.locator('input[data-search-input]');
        await searchInput.click();

        // Type a query
        const query = 'Nature';
        await searchInput.fill(query);
        await searchInput.press('Enter');

        // Verify search is triggered (URL change or results area appears)
        await expect(page).toHaveURL(/search|query=/);
    });

    test('keyboard shortcut / focuses search', async ({ page }) => {
        // Navigate to /
        await page.goto('/');

        // Press /
        await page.keyboard.press('/');

        // Verify search input is focused
        const searchInput = page.locator('input[data-search-input]');
        await expect(searchInput).toBeFocused();
    });
});
