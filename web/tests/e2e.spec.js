const { test, expect } = require('@playwright/test')

test('homepage has title', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toContainText('LangChain Web')
})
