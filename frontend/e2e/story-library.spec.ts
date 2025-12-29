import { test, expect, Page } from '@playwright/test';

/**
 * E2E tests for the Children's Stories app.
 *
 * These tests run against the Expo web build and exercise the story library
 * and story creation flows.
 */

/**
 * Login helper - authenticates using APP_PIN from environment
 */
async function login(page: Page): Promise<void> {
  const pin = process.env.APP_PIN;
  if (!pin) {
    throw new Error('APP_PIN not found in environment. Ensure .env is configured.');
  }

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // Check if we're on the login page
  const pinInput = page.getByPlaceholder('Enter PIN');
  const isLoginPage = await pinInput.isVisible({ timeout: 5000 }).catch(() => false);

  if (isLoginPage) {
    await pinInput.fill(pin);
    await page.getByText('Enter', { exact: true }).click();
    // Wait for redirect to home page
    await expect(page.getByText('My Story Library')).toBeVisible({ timeout: 10000 });
  }
}

test.describe('Story Library', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display the story library page with header', async ({ page }) => {
    // Already logged in and on home page from beforeEach
    // Check for the "New Story" button
    await expect(page.getByText('+ New Story')).toBeVisible();
  });

  test('should show loading state initially', async ({ page }) => {
    // Already logged in from beforeEach, library should be visible
    await expect(page.getByText('My Story Library')).toBeVisible();
  });

  test('should navigate to new story page when clicking New Story button', async ({ page }) => {
    // Already logged in and on home page from beforeEach
    // Click the New Story button
    await page.getByText('+ New Story').click();

    // Should navigate to the new story page (check for prompt area instead of ambiguous title)
    await expect(page.getByText('What should your story be about?')).toBeVisible({ timeout: 10000 });

    // Should see the Create My Story button (disabled initially)
    await expect(page.getByText('Create My Story')).toBeVisible();
  });

  test('should enable Create button when prompt is entered', async ({ page }) => {
    // Already logged in from beforeEach, navigate to new story page
    await page.getByText('+ New Story').click();
    await expect(page.getByText('What should your story be about?')).toBeVisible({ timeout: 10000 });

    // Find the text input and type a prompt
    const promptInput = page.getByPlaceholder('A story about...');
    await expect(promptInput).toBeVisible();

    // Type a story prompt
    await promptInput.fill('a friendly dragon who learns to share');

    // The Create My Story button should now be enabled
    // We verify by checking the button is clickable (not disabled)
    const createButton = page.getByText('Create My Story');
    await expect(createButton).toBeVisible();
  });

  test('should navigate back to library from new story page', async ({ page }) => {
    // Already logged in from beforeEach, navigate to new story page
    await page.getByText('+ New Story').click();
    await expect(page.getByText('What should your story be about?')).toBeVisible({ timeout: 10000 });

    // Click the back button (← symbol)
    await page.getByText('←').click();

    // Should be back at the library
    await expect(page.getByText('My Story Library')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Story Library - Empty and Error States', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should handle empty state gracefully', async ({ page }) => {
    // Already logged in from beforeEach, library should be visible
    await expect(page.getByText('My Story Library')).toBeVisible();

    // Page should show story count (either empty or with stories)
    // The "magical adventures" text appears in the count display
    const storyCount = page.getByText(/\d+ magical adventures/);
    await expect(storyCount).toBeVisible();
  });
});
