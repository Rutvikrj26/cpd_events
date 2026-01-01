import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
    const uniqueId = Date.now().toString();
    const email = `testuser_${uniqueId}@example.com`;
    const password = 'TestPassword123!';

    test('should allow a user to sign up and then log in', async ({ page }) => {
        // 1. Sign Up
        await page.goto('/signup');
        await expect(page.getByRole('heading', { name: /create an account/i })).toBeVisible();

        await page.getByLabel(/email/i).fill(email);
        await page.getByLabel(/password/i).fill(password);
        await page.getByRole('button', { name: /create account/i }).click();

        // Expect redirect to dashboard or login
        // Depending on logic, it might auto-login or ask to login.
        // Assuming auto-login or redirect to login.
        // Let's check for either Dashboard or Login page.
        // If it goes to login:
        if (page.url().includes('/login')) {
            await page.getByLabel(/email/i).fill(email);
            await page.getByLabel(/password/i).fill(password);
            await page.getByRole('button', { name: /sign in/i }).click();
        }

        // Verify Dashboard access
        await expect(page).toHaveURL(/.*\/dashboard/);
        await expect(page.getByText('CPD Events')).toBeVisible();

        // 2. Log Out (optional, but good for cleanup test)
        // await page.getByRole('button', { name: /user menu/i }).click();
        // await page.getByText(/sign out/i).click();
        // await expect(page).toHaveURL(/.*\/login/);
    });
});
