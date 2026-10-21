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
  plugins: ['unused-imports'],
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
      files: [
        'tests/**/*.js',
        'tests/**/*.vue',
        'tests/e2e/**/*.js',
        'tests/**/*.test.js',
        'tests/mocks/**/*.js',
        'playwright.config.js',
      ],
      env: {
        node: true,
      },
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
      rules: {
        'no-unused-vars': 'off',
        'unused-imports/no-unused-vars': 'off',
        'unused-imports/no-unused-imports': 'off',
        'no-undef': 'off',
      },
    },
  ],
  ignorePatterns: [
    'avatar-studio/src/',
    'public/avatar-studio/',
    'dist/',
    'node_modules/',
    'coverage/',
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/require-default-prop': 'off',
    'no-unused-vars': 'off',
    'unused-imports/no-unused-imports': 'error',
    'unused-imports/no-unused-vars': ['error', {
      vars: 'all',
      varsIgnorePattern: '^_',
      args: 'after-used',
      argsIgnorePattern: '^_',
      ignoreRestSiblings: true,
      caughtErrors: 'none',
    }],
  },
}
