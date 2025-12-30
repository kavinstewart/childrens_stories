import { test, expect, Page } from '@playwright/test';

/**
 * E2E test for story creation flow.
 */

async function login(page: Page): Promise<void> {
  const pin = process.env.APP_PIN;
  if (!pin) {
    throw new Error('APP_PIN not found in environment. Ensure .env is configured.');
  }

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  const pinInput = page.getByPlaceholder('Enter PIN');
  const isLoginPage = await pinInput.isVisible({ timeout: 5000 }).catch(() => false);

  if (isLoginPage) {
    await pinInput.fill(pin);
    await page.getByText('Enter', { exact: true }).click();
    await expect(page.getByText('My Story Library')).toBeVisible({ timeout: 10000 });
  }
}

test.describe('Story Creation', () => {
  test.setTimeout(300000); // 5 minutes

  test('should create a story about Transcendentalists and technology', async ({ page }) => {
    await login(page);

    // Navigate to new story page
    await page.getByText('+ New Story').click();
    await expect(page.getByText('What should your story be about?')).toBeVisible({ timeout: 10000 });

    // Enter the prompt
    const promptInput = page.getByPlaceholder('A story about...');
    await promptInput.fill(
      'The Transcendentalists (like Thoreau and Emerson) had ambivalent feelings about technology - ' +
      'they appreciated how inventions could connect people and reduce drudgery, ' +
      'but also worried technology might distract us from nature and inner wisdom. ' +
      'Show both sides of this tension in a story a child can understand.'
    );

    // Click Create My Story
    await page.getByText('Create My Story').click();

    // Wait for generation to complete
    await expect(page.getByText('Your story is ready!')).toBeVisible({ timeout: 240000 });

    // Click to read the story
    await page.getByText('Read Your Story!').click();
    await page.waitForTimeout(3000);

    // Verify page indicator is showing (e.g., "1 / 12") - confirms story reader loaded
    await expect(page.getByText(/\d+ \/ \d+/)).toBeVisible({ timeout: 10000 });

    // Take screenshot
    await page.screenshot({ path: 'test-results/transcendentalists-story-final.png', fullPage: true });

    console.log('Story created and displayed successfully!');
  });
});
