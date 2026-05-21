import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'coverage', 'node_modules']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      // Treat unused vars/args as warnings; allow `_` prefix to opt-out entirely.
      // The codebase predates this rule being strict; tightening to error is a
      // separate cleanup task.
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      // react-hooks v7 added several strict rules that fire on legitimate
      // pre-v7 patterns in this codebase. Treat as warnings until each is
      // migrated; `rules-of-hooks` stays an error because violations are bugs.
      'react-hooks/purity': 'warn',
      'react-hooks/static-components': 'warn',
      'react-hooks/set-state-in-effect': 'warn',
      // case statements with let/const are not unsafe; keep as a warning rather
      // than rewriting all switch blocks with braces.
      'no-case-declarations': 'warn',
      // Fast-Refresh only-export hint; informational, not a correctness issue.
      'react-refresh/only-export-components': 'warn',
      // `any` is allowed but flagged; downgrade to warning while typings are improved.
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    // Test files don't ship to production; their lint bar can be lower.
    files: ['**/*.test.{ts,tsx}', 'src/test/**'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
])
