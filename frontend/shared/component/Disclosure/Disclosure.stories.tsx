import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { Disclosure } from "./Disclosure";

const meta = {
  title: "Shared/Disclosure",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const States: Story = {
  render: () => (
    <main>
      <Disclosure title="詳細">任意の説明文</Disclosure>
      <Disclosure title="強調した詳細" variant="accent" defaultOpen>
        説明の内容
      </Disclosure>
      <Disclosure title="余白のある詳細" variant="spaced" defaultOpen>
        追加の説明
      </Disclosure>
    </main>
  ),
};
