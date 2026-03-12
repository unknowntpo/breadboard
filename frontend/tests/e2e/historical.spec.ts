import { test, expect } from '@playwright/test'

const AAPL_RECORDS = [
  { date: '2024-01-02', symbol: 'AAPL', open: 185.0, high: 188.0, low: 184.0, close: 187.0, volume: 1000000 },
  { date: '2024-01-03', symbol: 'AAPL', open: 187.0, high: 190.5, low: 186.0, close: 189.0, volume: 1200000 },
]

const TSLA_RECORDS = [
  { date: '2024-01-02', symbol: 'TSLA', open: 250.0, high: 255.0, low: 248.0, close: 252.0, volume: 500000 },
]

function mockApi(page: import('@playwright/test').Page, records: typeof AAPL_RECORDS, symbol = 'AAPL') {
  return page.route('**/api/v1/history**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        symbol,
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        records,
        count: records.length,
      }),
    })
  )
}

test.beforeEach(async ({ page }) => {
  await mockApi(page, AAPL_RECORDS)
})

test('page loads with nav and AAPL selected by default', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('nav')).toContainText('breadboard')
  await expect(page.getByRole('button', { name: 'AAPL' })).toHaveClass(/bg-\[#FF6900\]/)
})

test('stat cards show latest record values', async ({ page }) => {
  await page.goto('/')
  // latest record is 2024-01-03: open=187, high=190.5, low=186, close=189
  await expect(page.locator('.text-2xl').nth(0)).toContainText('187.00')
  await expect(page.locator('.text-2xl').nth(1)).toContainText('190.50')
  await expect(page.locator('.text-2xl').nth(2)).toContainText('186.00')
  await expect(page.locator('.text-2xl').nth(3)).toContainText('189.00')
})

test('table renders rows sorted descending by date', async ({ page }) => {
  await page.goto('/')
  const rows = page.locator('tbody tr')
  await expect(rows.first()).toContainText('2024-01-03')
  await expect(rows.nth(1)).toContainText('2024-01-02')
})

test('switching to TSLA reloads data with correct symbol', async ({ page }) => {
  const requests: string[] = []
  page.on('request', req => {
    if (req.url().includes('/api/v1/history')) requests.push(req.url())
  })

  // Override mock for TSLA
  await page.route('**/api/v1/history**', route => {
    const url = new URL(route.request().url())
    const sym = url.searchParams.get('symbol') || 'AAPL'
    const records = sym === 'TSLA' ? TSLA_RECORDS : AAPL_RECORDS
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ symbol: sym, start_date: '2024-01-01', end_date: '2024-12-31', records, count: records.length }),
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'TSLA' }).click()
  await expect(page.getByRole('button', { name: 'TSLA' })).toHaveClass(/bg-\[#FF6900\]/)

  // Table should show TSLA data
  await expect(page.locator('tbody tr').first()).toContainText('252.00')
})

test('switching range triggers new API call', async ({ page }) => {
  const urls: string[] = []
  await page.route('**/api/v1/history**', route => {
    urls.push(route.request().url())
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ symbol: 'AAPL', start_date: '2024-01-01', end_date: '2024-12-31', records: AAPL_RECORDS, count: 2 }),
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '3M' }).click()
  await expect(page.getByRole('button', { name: '3M' })).toHaveClass(/bg-\[#FF6900\]/)

  // Should have made at least 2 requests (initial + after range switch)
  expect(urls.length).toBeGreaterThanOrEqual(2)
  const lastUrl = new URL(urls[urls.length - 1])
  expect(lastUrl.searchParams.get('symbol')).toBe('AAPL')
})

test('error state shows message when API returns 500', async ({ page }) => {
  await page.route('**/api/v1/history**', route =>
    route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Internal server error' }) })
  )
  await page.goto('/')
  await expect(page.locator('text=Internal server error')).toBeVisible()
  await expect(page.locator('tbody td').filter({ hasText: 'No data' })).toBeVisible()
})
