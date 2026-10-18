import type { Preview } from "@storybook/nextjs-vite";
import "../styles/tokens.css";
import "../styles/base.css";
import "../features/chat/components/markdown-content.css";
import "../app/globals.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    layout: "padded",
  },
};

export default preview;
