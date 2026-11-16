// ESLint config. Protected by an ECC hook after creation: ask Kenny or Vlad before changing it.
// Besides the usual TypeScript rules it enforces three design rules from CLAUDE.md:
// colours come from theme.ts, keys are bound in input/, view models stay free of three.js/React.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import { defineConfig } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

const COLOUR_LITERAL = "/^(#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|(rgba?|hsla?)\\()/";

export default defineConfig(
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      ".venv/**",
      "vendor/**",
      "backend/**",
      "docs/**",
      "data/**",
      "models/**",
      "test-results/**",
      "playwright-report/**",
      "client/src/contract.gen.ts",
    ],
  },
  js.configs.recommended,
  tseslint.configs.recommended,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_" },
      ],
    },
  },
  {
    files: ["client/src/**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  {
    files: ["scripts/**/*.{js,mjs}", "e2e/**/*.ts", "*.config.{js,mjs,ts}", "client/*.config.{js,mjs,ts}"],
    languageOptions: { globals: globals.node },
  },
  {
    // CLAUDE.md: sizes and colours come from theme.ts; every user action is an intent.
    files: ["client/src/scene/**/*.{ts,tsx}", "client/src/hud/**/*.{ts,tsx}"],
    ignores: ["**/*.test.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: `Literal[value=${COLOUR_LITERAL}]`,
          message: "No literal colours in components or view models: use tokens from client/src/theme.ts.",
        },
        {
          selector: "CallExpression[callee.property.name='addEventListener'][arguments.0.value=/^key/]",
          message: "Do not bind keys here: add a binding in client/src/input/ that emits an intent.",
        },
      ],
    },
  },
  {
    // View models are pure functions, unit tested without a GPU.
    files: ["client/src/hud/**/*.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["three", "three/*", "@react-three/*", "react", "react-dom", "react/*"],
              message: "View models (client/src/hud/) must not import three.js or React.",
            },
          ],
        },
      ],
    },
  },
);
