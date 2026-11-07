import { defineConfig } from '@playwright/test';
const remote = process.env.UI_BASE_URL;
export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.js',
  workers: 1,
  timeout: 45000,
  outputDir: 'test-results',
  reporter: [['list'], ['json', { outputFile: 'report.json' }]],
  webServer: remote
    ? undefined
    : {
        command:
          'python3 -m http.server 8765 --directory ../dist --bind 127.0.0.1',
        url: 'http://127.0.0.1:8765',
        reuseExistingServer: false,
      },
  use: {
    baseURL: remote || 'http://127.0.0.1:8765',
    browserName: process.env.UI_BROWSER || 'chromium',
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
