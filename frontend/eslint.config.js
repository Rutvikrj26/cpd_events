import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import boundaries from 'eslint-plugin-boundaries';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import localRules from './eslint-local-rules.cjs';

export default [
    {
        ignores: ['dist', '.eslintrc.cjs'],
    },
    js.configs.recommended,
    {
        files: ['**/*.{ts,tsx}'],
        languageOptions: {
            ecmaVersion: 2020,
            globals: globals.browser,
            parser: tsParser,
        },
        plugins: {
            '@typescript-eslint': tsPlugin,
            'react-hooks': reactHooks,
            'react-refresh': reactRefresh,
            'boundaries': boundaries,
            'local': {
                rules: localRules,
            },
        },
        settings: {
            // Module boundaries (refactor/feature-architecture).
            // Tag every directory with a "type"; cross-type imports are then
            // restricted by `boundaries/element-types` below.
            'boundaries/elements': [
                { type: 'app',     pattern: 'src/app/**/*' },
                { type: 'feature', pattern: 'src/features/*/**/*', mode: 'folder', capture: ['featureName'] },
                { type: 'shared',  pattern: 'src/shared/**/*' },
                { type: 'store',   pattern: 'src/stores/**/*' },
                { type: 'page',    pattern: 'src/pages/**/*' },
                { type: 'api',     pattern: 'src/api/**/*' },
                { type: 'context', pattern: 'src/contexts/**/*' },
                { type: 'lib',     pattern: 'src/lib/**/*' },
                { type: 'hooks',   pattern: 'src/hooks/**/*' },
                // Legacy buckets that exist today; tagged so imports against them
                // don't crash the linter while the migration is in flight.
                { type: 'legacy',  pattern: 'src/components/**/*' },
                { type: 'legacy',  pattern: 'src/utils/**/*' },
            ],
            'boundaries/include': ['src/**/*.{ts,tsx,js,jsx}'],
            'boundaries/ignore': ['**/*.test.*', '**/*.spec.*', '**/__tests__/**'],
        },
        rules: {
            ...tsPlugin.configs.recommended.rules,
            ...reactHooks.configs.recommended.rules,
            'react-refresh/only-export-components': [
                'warn',
                { allowConstantExport: true },
            ],
            '@typescript-eslint/no-explicit-any': 'off',
            '@typescript-eslint/no-unused-vars': [
                'warn',
                {
                    argsIgnorePattern: '^_',
                    varsIgnorePattern: '^_',
                    caughtErrorsIgnorePattern: '^_',
                },
            ],
            // Custom rule to prevent hardcoded colors
            'local/no-hardcoded-colors': 'warn',

            // Warn-only during the refactor; promoted to 'error' in P5 once
            // every feature has been migrated. Until then, legacy code is
            // tagged so imports don't fail the build.
            // Promoted from `warn` to `error` after the refactor —
            // every cross-feature import path is now legal under these
            // rules, so a violation should fail CI rather than be ignored.
            'boundaries/element-types': [
                'error',
                {
                    default: 'disallow',
                    rules: [
                        { from: 'app',     allow: ['*'] },
                        { from: 'shared',  allow: ['shared', 'lib'] },
                        // Features can use shared primitives, stores, the api
                        // client, and import within their own feature folder.
                        // Cross-feature imports are intentionally absent.
                        { from: 'feature', allow: ['shared', 'store', 'api', 'lib', 'feature', 'context', 'hooks', 'legacy'] },
                        { from: 'store',   allow: ['shared', 'lib'] },
                        { from: 'page',    allow: ['feature', 'shared', 'store', 'lib', 'context', 'hooks', 'legacy', 'api'] },
                        { from: 'api',     allow: ['lib', 'shared'] },
                        { from: 'lib',     allow: ['lib', 'shared'] },
                        { from: 'hooks',   allow: ['lib', 'shared'] },
                        { from: 'context', allow: ['lib', 'shared', 'api'] },
                        { from: 'legacy',  allow: ['*'] },  // legacy keeps its own privileges during the transition
                    ],
                },
            ],
        },
    },
    {
        files: ['vite.config.ts', 'eslint.config.js'],
        languageOptions: {
            globals: globals.node,
        },
    },
    {
        files: ['src/setupTests.ts', '**/*.test.tsx', '**/*.test.ts'],
        languageOptions: {
            globals: {
                ...globals.node,
                ...globals.jest,
                vi: 'readonly',
                describe: 'readonly',
                it: 'readonly',
                expect: 'readonly',
                beforeEach: 'readonly',
                afterEach: 'readonly',
                test: 'readonly',
                beforeAll: 'readonly',
                afterAll: 'readonly',
                screen: 'readonly',
                render: 'readonly',
                fireEvent: 'readonly',
                userEvent: 'readonly',
                act: 'readonly',
                waitFor: 'readonly',
                ResizeObserver: 'writable',
            },
        },
    },
];
