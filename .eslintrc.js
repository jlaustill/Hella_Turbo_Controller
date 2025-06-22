module.exports = {
  root: true,
  ignorePatterns: [
    "node_modules/**",
    "dist/**",
    "dist-electron/**",
    "build/**",
    "*.js",
    "vite.config.ts",
    "electron/**",
  ],
  extends: [
    "airbnb-base",
    "airbnb-typescript/base",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "prettier",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    project: ["./tsconfig.json", "./tsconfig.node.json"],
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ["@typescript-eslint", "react", "react-hooks"],
  rules: {
    // Hardware safety rules
    "no-bitwise": "off", // Allow bitwise for CAN operations
    "no-console": "off", // Essential for CAN debugging
    "prefer-const": "error", // Prevent accidental mutations

    // React specific
    "react/react-in-jsx-scope": "off", // Not needed in React 17+

    // Import rules
    "import/no-extraneous-dependencies": ["error", { devDependencies: true }],
    "import/extensions": "off", // Allow missing extensions with bundlers
    "import/no-import-module-exports": "off", // Node.js ES modules

    // Code quality rules
    "no-nested-ternary": "error", // Force fixing nested ternaries
    "no-restricted-syntax": "off", // Allow for-of loops
    "no-await-in-loop": "error", // Force fixing await in loops
    "consistent-return": "error", // Force fixing return consistency
    "no-plusplus": "off", // Allow ++ operator
    "global-require": "error", // Force fixing dynamic requires

    // TypeScript specific
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-shadow": "error",
    "@typescript-eslint/lines-between-class-members": "off",
    "class-methods-use-this": "off",
    "max-classes-per-file": "off",
    "@typescript-eslint/no-use-before-define": "off",
    "object-shorthand": "error",
    radix: "error",
    "no-case-declarations": "error",
  },
  env: {
    node: true,
    browser: true,
  },
  settings: {
    react: {
      version: "detect",
    },
  },
};
