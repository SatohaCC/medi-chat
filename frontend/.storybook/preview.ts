import type { Preview } from "@storybook/nextjs-vite";
import "../styles/tokens.css";
import "../styles/base.css";
import "../shared/component/MarkdownContent/MarkdownContent.css";
import "../shared/component/HighlightText/HighlightText.css";
import "../features/chat/styles/markdown-content.css";
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
