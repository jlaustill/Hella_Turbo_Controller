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
    "no-console": "warn", // Allow console for debugging
    "prefer-const": "error", // Prevent accidental mutations

    // React specific
    "react/react-in-jsx-scope": "off", // Not needed in React 17+

    // Import rules
    "import/no-extraneous-dependencies": ["error", { devDependencies: true }],
    "import/extensions": "off", // Allow missing extensions with bundlers

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
