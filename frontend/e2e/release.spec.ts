import { test, expect } from '@playwright/test'

test('dashboard and image-to-caption workflow', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  await expect(page.getByText('Grounded captions start with evidence')).toBeVisible()

  await page.goto('/create')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'release-image.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
      'base64',
    ),
  })
  await page.getByRole('button', { name: 'Upload and build evidence' }).click()
  await expect(page.getByText('Evidence Review')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Unified evidence')).toBeVisible()
  await expect(page.getByText('test object', { exact: false }).first()).toBeVisible()

  await page.getByRole('link', { name: 'Open Caption Studio' }).click()
  await expect(page.getByText('Caption settings')).toBeVisible()
  await page.getByRole('button', { name: 'Generate grounded captions' }).click()
  await expect(page.getByText('direct', { exact: false }).first()).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Verified by evidence', { exact: false }).first()).toBeVisible()

  const copyButton = page.getByRole('button', { name: 'Copy caption' }).first()
  await copyButton.click()
  await expect(page.getByText('Copied').first()).toBeVisible()

  await page.getByRole('button', { name: 'Regenerate' }).click()
  await expect(page.getByText('direct', { exact: false }).first()).toBeVisible()

  await page.goto('/history')
  await expect(page.getByText('Generation History')).toBeVisible()
  await expect(page.getByText('caption variants', { exact: false }).first()).toBeVisible()
})

test('invalid file upload shows an understandable error', async ({ page }) => {
  await page.goto('/create')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'document.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4'),
  })
  await expect(page.getByText(/not a supported media type/i)).toBeVisible()
})
