import { test, expect } from '@playwright/test';

test.describe('Event Creation Flow', () => {
    const uniqueId = Date.now().toString();
    const email = `organizer_${uniqueId}@example.com`;
    const password = 'TestPassword123!';

    test.beforeEach(async ({ page }) => {
        // Register a new user for each test to ensure clean state
        await page.goto('/signup');
        await page.getByLabel(/email/i).fill(email);
        await page.getByLabel(/password/i).fill(password);
        await page.getByRole('button', { name: /create account/i }).click();
        // Handle redirect to login if necessary
        if (page.url().includes('/login')) {
            await page.getByLabel(/email/i).fill(email);
            await page.getByLabel(/password/i).fill(password);
            await page.getByRole('button', { name: /sign in/i }).click();
        }
        await expect(page).toHaveURL(/.*\/dashboard/);
    });

    test('should create a new webinar event', async ({ page }) => {
        // Navigate to Create Event
        await page.goto('/events');
        await page.getByRole('link', { name: /create event/i }).click();

        // Step 1: Basic Info
        await expect(page.getByRole('heading', { name: /basic information/i })).toBeVisible();
        await page.getByLabel(/event title/i).fill(`Live Test Event ${uniqueId}`);

        // Selects in Radix UI are trickier in E2E sometimes, but clean playwright locators usually work.
        // Trigger click -> Option click
        // "Event Type"
        await page.locator('button[role="combobox"]').first().click();
        await page.getByRole('option', { name: /webinar/i }).click();

        // "Format"
        await page.locator('button[role="combobox"]').nth(1).click();
        await page.getByRole('option', { name: /online/i }).click();

        await page.getByRole('button', { name: /next/i }).click();

        // Step 2: Schedule
        await expect(page.getByRole('heading', { name: /schedule/i })).toBeVisible();
        // Fill Date (input type="datetime-local" or similar?)
        // Our mock used text input, REAL app uses DateTimePicker component.
        // Assuming standard input behavior or flatpickr?
        // Let's try filling the input.
        // If it's a native date picker or complex component, might need specific locator.
        // Based on previous file views, it's `DateTimePicker`.
        // Let's assume we can type in it or it exposes an input.
        // We'll try generic fill first.
        // Finding the input might need care.
        // Inspecting `StepSchedule.tsx` earlier showed: `DateTimePicker label="Start Date & Time"`.
        // We can try `getByLabel`.
        // Note: If it's a readonly input that opens a calendar, simple fill might fail.
        // But for now, let's try.

        // Duration
        // There are hours/minutes inputs.
        // They are number inputs.
        await page.locator('input[type="number"]').first().fill('1'); // Hours
        await page.locator('input[type="number"]').nth(1).fill('0'); // Minutes

        await page.getByRole('button', { name: /next/i }).click();

        // Step 3: Details
        await expect(page.getByRole('heading', { name: /event details/i })).toBeVisible();
        // Quill editor. 
        // Playwright needs to target the editor content editable area.
        await page.locator('.ql-editor').fill('This is a test description for the live event.');

        await page.getByRole('button', { name: /next/i }).click();

        // Step 4: Settings
        await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
        await page.getByRole('button', { name: /next/i }).click();

        // Step 5: Review
        await expect(page.getByRole('heading', { name: /review & create/i })).toBeVisible();
        await page.getByRole('button', { name: /create event/i }).click();

        // Success
        await expect(page.getByText(/event created successfully/i)).toBeVisible();
        await expect(page).toHaveURL(/.*\/events/);
    });
});
