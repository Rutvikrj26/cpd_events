import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';

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
