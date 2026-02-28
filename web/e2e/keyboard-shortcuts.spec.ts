import { test, expect } from '@playwright/test';

test.describe('Keyboard Shortcuts', () => {
    test('? key opens shortcut help modal', async ({ page }) => {
        // Navigate to /
        await page.goto('/');

        // Press ?
        await page.keyboard.press('Shift+?');

        // Verify modal appears with shortcut list
        const modal = page.locator('[data-testid="shortcut-modal"]');
        await expect(modal).toBeVisible();
        await expect(modal).toContainText(/Shortcut|Keyboard/i);

        // Press Escape
        await page.keyboard.press('Escape');

        // Verify modal closes
        await expect(modal).not.toBeVisible();
    });

    test('Escape key closes modals', async ({ page }) => {
        await page.goto('/');

        // Open shortcut modal
        await page.keyboard.press('Shift+?');
        const modal = page.locator('[data-testid="shortcut-modal"]');
        await expect(modal).toBeVisible();

        // Press Escape
        await page.keyboard.press('Escape');

        // Verify it's gone
        await expect(modal).not.toBeVisible();
    });
});
