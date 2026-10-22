import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

// Phase 0 lint set: ESLint core recommended rules, typescript-eslint recommended rules and the
// React Hooks rules. eslint-config-next is intentionally not used; see README.md ("Linting").
export default defineConfig([
  globalIgnores([".next/**", "out/**", "coverage/**", "node_modules/**", "next-env.d.ts"]),
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
]);
