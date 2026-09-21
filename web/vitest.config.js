import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    exclude: ['tests/e2e/**', 'tests/e2e.spec.js', 'node_modules/**'],
  },
})