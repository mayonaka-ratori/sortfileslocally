import { test, expect } from '@playwright/test';

test.describe('Onboarding Tour', () => {
    test('onboarding tour flow', async ({ page }) => {
        // Force onboarding to show by clearing storage or just navigating if first run
        await page.goto('/');

        // Verify tour appears
        const tour = page.locator('[data-testid="onboarding-tour"]');
        await expect(tour).toBeVisible();
        await expect(tour).toContainText(/Welcome|Search/i);

        // Navigate through steps
        const nextButton = tour.getByRole('button', { name: /next/i });
        const stepCount = 6; // Based on OnboardingTour.tsx

        for (let i = 0; i < stepCount - 1; i++) {
            await nextButton.click();
        }

        // Final step should have "Finish"
        const finishButton = tour.getByRole('button', { name: /finish/i });
        await expect(finishButton).toBeVisible();
        await finishButton.click();

        // Tour should be gone
        await expect(tour).not.toBeVisible();
    });

    test('onboarding tour can be skipped', async ({ page }) => {
        await page.goto('/');

        const tour = page.locator('[data-testid="onboarding-tour"]');
        await expect(tour).toBeVisible();

        // Click skip button
        const skipButton = tour.getByRole('button', { name: /skip/i });
        await skipButton.click();

        // Tour should be gone
        await expect(tour).not.toBeVisible();
    });
});
