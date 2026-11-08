import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { HighlightText } from "./HighlightText";

const meta = {
  title: "Shared/HighlightText",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {
  render: () => (
    <p>
      <HighlightText
        text="表示内容を強調します。A+Bもそのまま検索します。"
        words={["強調", "A+B"]}
      />
    </p>
  ),
};
