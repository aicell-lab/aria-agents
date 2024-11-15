import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";
import pluginReact from "eslint-plugin-react";

export default [
  {
    files: ["**/*.{js,mjs,cjs,ts,jsx,tsx}"],
    languageOptions: { globals: globals.browser },
    plugins: { react: pluginReact },  // Define the react plugin here
    rules: {
      "react/react-in-jsx-scope": "off",
      "react/jsx-filename-extension": [1, { "extensions": [".js", ".jsx"] }],
    },
  },
  pluginJs.configs.recommended,          // equivalent to "eslint:recommended"
  ...tseslint.configs.recommended,
  pluginReact.configs.recommended,       // equivalent to "plugin:react/recommended"
];
