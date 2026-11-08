import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { MarkdownContent } from "./MarkdownContent";

const meta = {
  title: "Shared/MarkdownContent",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {
  render: () => (
    <main className="markdown-content">
      <MarkdownContent
        content={
          "## 任意のコンテンツ\n\n[リンク](https://example.test)と**強調**を表示します。\n\n| 項目 | 内容 |\n| --- | --- |\n| A | B |"
        }
      />
    </main>
  ),
};
