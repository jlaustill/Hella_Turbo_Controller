module.exports = {
  extends: [
    'airbnb-base',
    'airbnb-typescript/base',
    'plugin:vue/vue3-recommended',
    '@vue/typescript/recommended',
    'prettier',
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    project: './tsconfig.json',
    extraFileExtensions: ['.vue'],
  },
  rules: {
    // Hardware safety rules
    'no-bitwise': 'off', // Allow bitwise for CAN operations
    'no-console': 'warn', // Allow console for debugging
    'prefer-const': 'error', // Prevent accidental mutations
    
    // Vue specific
    'vue/multi-word-component-names': 'off',
    
    // Import rules
    'import/no-extraneous-dependencies': ['error', { devDependencies: true }],
  },
  env: {
    node: true,
    browser: true,
  },
};