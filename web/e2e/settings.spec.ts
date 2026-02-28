import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
    test('settings page loads with all sections', async ({ page }) => {
        // Navigate to /settings
        await page.goto('/settings');

        // Verify Language selector exists
        const languageSelector = page.locator('[data-testid="language-selector"]');
        await expect(languageSelector).toBeVisible();

        // Verify Privacy section exists with "Network Activity Log"
        await expect(page.locator('body')).toContainText(/Privacy|Network Activity/i);

        // Verify "Run Privacy Audit" button exists
        const auditButton = page.getByRole('button', { name: /audit/i });
        await expect(auditButton).toBeVisible();
    });

    test('language switch updates UI', async ({ page }) => {
        // Navigate to /settings
        await page.goto('/settings');

        // Switch language to Japanese using the button in language selector
        const langSelector = page.locator('[data-testid="language-selector"]');
        const jaButton = langSelector.getByRole('button', { name: /日本語/i });

        await jaButton.click();

        // Verify some UI text changes to Japanese
        await expect(page.locator('body')).toContainText(/設定|言語/);
    });
});
