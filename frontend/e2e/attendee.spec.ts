import { test, expect } from '@playwright/test';

test.describe('Attendee Flow', () => {
    const uniqueId = Date.now().toString();
    const organizerEmail = `org_setup_${uniqueId}@example.com`;
    const attendeeEmail = `attendee_${uniqueId}@example.com`;
    const password = 'TestPassword123!';
    const eventTitle = `Attendee Test Event ${uniqueId}`;
    let eventUrl = '';

    test.beforeAll(async ({ browser }) => {
        // Setup: Create a Published Event as an Organizer
        // using a separate browser context to emulate a distinct session
        const context = await browser.newContext();
        const page = await context.newPage();

        // 1. Sign Up as Organizer
        await page.goto('/signup');
        await page.getByLabel(/email/i).fill(organizerEmail);
        await page.getByLabel(/password/i).fill(password);
        await page.getByRole('button', { name: /create account/i }).click();

        // Handle login redirect if needed
        if (page.url().includes('/login')) {
            await page.getByLabel(/email/i).fill(organizerEmail);
            await page.getByLabel(/password/i).fill(password);
            await page.getByRole('button', { name: /sign in/i }).click();
        }
        await expect(page).toHaveURL(/.*\/dashboard/);

        // 2. Create Event
        await page.goto('/events/create');
        await page.getByLabel(/event title/i).fill(eventTitle);
        // Defaults are usually okay, but let's select required fields
        await page.locator('button[role="combobox"]').first().click();
        await page.getByRole('option', { name: /webinar/i }).click();
        await page.locator('button[role="combobox"]').nth(1).click();
        await page.getByRole('option', { name: /online/i }).click();

        await page.getByRole('button', { name: /next/i }).click(); // Schedule
        await page.locator('input[type="number"]').first().fill('1');
        await page.locator('input[type="number"]').nth(1).fill('0');
        await page.getByRole('button', { name: /next/i }).click(); // Details
        await page.locator('.ql-editor').fill('Description for attendee test.');
        await page.getByRole('button', { name: /next/i }).click(); // Settings
        await page.getByRole('button', { name: /next/i }).click(); // Review
        await page.getByRole('button', { name: /create event/i }).click();

        await expect(page.getByText(/event created successfully/i)).toBeVisible();
        await page.waitForURL(/.*\/events\/.*/);

        // 3. Publish Event
        // We need to find the publish button. 
        // Assuming it's on the page or we need to click "Publish"
        // Let's try to find it.
        const publishButton = page.getByRole('button', { name: /publish/i });
        if (await publishButton.isVisible()) {
            await publishButton.click();
            // Handle confirmation modal if it exists
            const confirmBtn = page.getByRole('button', { name: /confirm|yes|proceed/i });
            if (await confirmBtn.isVisible()) {
                await confirmBtn.click();
            }
        }

        // Wait for status update
        await page.reload();
        await expect(page.getByText(/published/i)).toBeVisible();

        await context.close();
    });

    test('should allow an attendee to discover and register for an event', async ({ page }) => {
        // 1. Sign Up as Attendee
        await page.goto('/signup');
        await page.getByLabel(/email/i).fill(attendeeEmail);
        await page.getByLabel(/password/i).fill(password);
        await page.getByRole('button', { name: /create account/i }).click();

        if (page.url().includes('/login')) {
            await page.getByLabel(/email/i).fill(attendeeEmail);
            await page.getByLabel(/password/i).fill(password);
            await page.getByRole('button', { name: /sign in/i }).click();
        }
        await expect(page).toHaveURL(/.*\/dashboard/);

        // 2. Discover Event
        await page.goto('/events/browse');
        // Search or find the event
        await page.getByPlaceholder(/search/i).fill(eventTitle);
        await page.keyboard.press('Enter');

        // Click on the event card/link
        // Assuming the title is a link or part of a card
        await page.getByText(eventTitle).first().click();

        // 3. Register
        // Should be on Event Detail Page
        // Click Register button
        await page.getByRole('button', { name: /register/i }).first().click();

        // 4. Registration Flow (might be a modal or page)
        // If it's a simple free event, maybe just "Confirm"
        // If there's a form, fill it.
        // Assuming minimal form or auto-filled for logged-in user.
        // Look for "Confirm Registration" or similar
        const completeButton = page.getByRole('button', { name: /complete|confirm|register/i });
        if (await completeButton.isVisible()) {
            await completeButton.click();
        }

        // 5. Verify Success
        await expect(page.getByText(/registration confirmed/i)).toBeVisible();

        // 6. Verify in My Registrations
        await page.goto('/registrations');
        await expect(page.getByText(eventTitle)).toBeVisible();
    });
});
