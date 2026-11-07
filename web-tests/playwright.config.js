import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: '*.spec.js', workers: 1, timeout: 45000,
  outputDir: 'test-results', reporter: [['list'], ['json', { outputFile: 'report.json' }]],
  use: {browserName: 'chromium', viewport: {width:1440,height:1000}, screenshot:'only-on-failure', trace:'retain-on-failure'},
});
