module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
    es2022: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  overrides: [
    {
      files: ['*.vue'],
      parser: 'vue-eslint-parser',
      parserOptions: {
        parser: {
          js: 'espree',
        },
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    {
      files: ['tests/e2e/**/*.js', 'tests/**/*.test.js', 'tests/mocks/**/*.js', 'playwright.config.js'],
      env: {
        node: true,
      },
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
  ],
  ignorePatterns: [
    'dist/',
    'node_modules/',
    'coverage/',
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
  },
}
