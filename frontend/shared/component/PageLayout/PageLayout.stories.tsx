import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { PageLayout, PageWorkspace } from "./PageLayout";

const meta = {
  title: "Shared/PageLayout",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {
  render: () => (
    <PageLayout screen="layout-example">
      <header>ページ見出し</header>
      <PageWorkspace>
        <main>本文</main>
      </PageWorkspace>
    </PageLayout>
  ),
};
