import eslint from "@eslint/js";
import globals from "globals";
import svelte from "eslint-plugin-svelte";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: ["dist/**", "../custom_components/benni_light_policy/frontend/app/**"],
  },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  ...svelte.configs["flat/recommended"],
  {
    files: ["**/*.ts", "**/*.svelte"],
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        extraFileExtensions: [".svelte"],
        parser: tseslint.parser,
        projectService: true,
      },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "svelte/no-at-html-tags": "error",
    },
  },
);
