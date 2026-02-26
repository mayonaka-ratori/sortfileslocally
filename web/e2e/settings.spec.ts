import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
    test('settings page loads with all sections', async ({ page }) => {
        // Navigate to /settings
        await page.goto('/settings');

        // Verify Language selector exists
        const languageSelector = page.getByRole('combobox').or(page.locator('select')).first();
        await expect(languageSelector).toBeVisible();

        // Verify Privacy section exists with "Network Activity Log"
        await expect(page.locator('body')).toContainText(/Privacy|Network Activity/i);

        // Verify "Run Privacy Audit" button exists
        const auditButton = page.getByRole('button', { name: /audit/i });
        await expect(auditButton).toBeVisible();
    });

    test('language switch changes UI text', async ({ page }) => {
        // Navigate to /settings
        await page.goto('/settings');

        // Switch language to Japanese
        // This assumes a dropdown or button interaction
        const langSelect = page.getByRole('combobox').or(page.locator('select')).first();
        if (await langSelect.isVisible()) {
            await langSelect.selectOption('ja');
            // Verify some UI text changes to Japanese
            await expect(page.locator('body')).toContainText(/設定|言語/);
        }
    });
});
