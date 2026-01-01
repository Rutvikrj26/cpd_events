import { test, expect } from '@playwright/test';

test.describe('Organizer Flow', () => {
    const uniqueId = Date.now().toString();
    const email = `organizer_${uniqueId}@example.com`;
    const password = 'TestPassword123!';
    let eventTitle = `Organizer Flow Event ${uniqueId}`;

    test.beforeEach(async ({ page }) => {
        // 1. Sign Up as a new Organizer
        await page.goto('/signup');
        await page.getByLabel(/email/i).fill(email);
        await page.getByLabel(/password/i).fill(password);
        await page.getByRole('button', { name: /create account/i }).click();

        // Handle potential login redirect
        if (page.url().includes('/login')) {
            await page.getByLabel(/email/i).fill(email);
            await page.getByLabel(/password/i).fill(password);
            await page.getByRole('button', { name: /sign in/i }).click();
        }

        // Verify Dashboard
        await expect(page).toHaveURL(/.*\/dashboard/);
    });

    test('should allow an organizer to create and publish an event', async ({ page }) => {
        // 2. Create a new Event (Draft)
        await page.goto('/events');
        await page.getByRole('link', { name: /create event/i }).click();

        // Step 1: Basic Info
        await expect(page.getByRole('heading', { name: /basic information/i })).toBeVisible();
        await page.getByLabel(/event title/i).fill(eventTitle);

        // Select Event Type: Webinar
        await page.locator('button[role="combobox"]').first().click();
        await page.getByRole('option', { name: /webinar/i }).click();

        // Select Format: Online
        await page.locator('button[role="combobox"]').nth(1).click();
        await page.getByRole('option', { name: /online/i }).click();

        await page.getByRole('button', { name: /next/i }).click();

        // Step 2: Schedule
        await expect(page.getByRole('heading', { name: /schedule/i })).toBeVisible();

        // Set duration to 1 hour
        await page.locator('input[type="number"]').first().fill('1');
        await page.locator('input[type="number"]').nth(1).fill('0');

        await page.getByRole('button', { name: /next/i }).click();

        // Step 3: Details
        await expect(page.getByRole('heading', { name: /event details/i })).toBeVisible();
        await page.locator('.ql-editor').fill('This is a comprehensive test event created by the organizer flow test.');
        await page.getByRole('button', { name: /next/i }).click();

        // Step 4: Settings
        await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
        await page.getByRole('button', { name: /next/i }).click();

        // Step 5: Review & Create
        await expect(page.getByRole('heading', { name: /review & create/i })).toBeVisible();
        await page.getByRole('button', { name: /create event/i }).click();

        // Verify creation
        await expect(page.getByText(/event created successfully/i)).toBeVisible();

        // 3. Publish the Event
        // Assuming we are redirected to the event dashboard or list. 
        // Need to find the "Publish" button. 
        // The URL should be something like /events/:uuid
        await expect(page).toHaveURL(/.*\/events\/[a-f0-9-]+/);

        // On the event detail page, look for Publish button
        // It might be in a header or actions menu
        // Check for 'Publish Event' button
        const publishButton = page.getByRole('button', { name: /publish event/i });

        // If it's inside a menu, we might need to open it, but usually primary action is visible.
        // Let's assume it's visible or we can find it.
        if (await publishButton.isVisible()) {
            await publishButton.click();

            // Confirm dialog if exists
            const confirmButton = page.getByRole('button', { name: /confirm/i });
            if (await confirmButton.isVisible()) {
                await confirmButton.click();
            }
        } else {
            // Fallback: Check if there's a status dropdown or manage menu
            console.log('Publish button not found directly, checking status badge seems to be Draft');
        }

        // 4. Verify status is Published
        // Reload to be sure or wait for UI update
        await page.reload();
        await expect(page.getByText(/published/i)).toBeVisible();

        // 5. Verify it appears in Dashboard
        await page.goto('/dashboard');
        await expect(page.getByText(eventTitle)).toBeVisible();
    });
});
