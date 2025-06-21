module.exports = {
  extends: [
    'airbnb-base',
    'airbnb-typescript/base',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'prettier',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: './tsconfig.json',
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['@typescript-eslint', 'react', 'react-hooks'],
  rules: {
    // Hardware safety rules
    'no-bitwise': 'off', // Allow bitwise for CAN operations
    'no-console': 'warn', // Allow console for debugging
    'prefer-const': 'error', // Prevent accidental mutations
    
    // React specific
    'react/react-in-jsx-scope': 'off', // Not needed in React 17+
    
    // Import rules
    'import/no-extraneous-dependencies': ['error', { devDependencies: true }],
  },
  env: {
    node: true,
    browser: true,
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
};