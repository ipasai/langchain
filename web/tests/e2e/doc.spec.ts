import { test, expect } from '@playwright/test'

test('homepage has DocAnalyzer and can load', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/LangChain/i)
  // check DocAnalyzer text
  await expect(page.locator('text=上傳文件後可先檢視摘要')).toBeVisible()
})
