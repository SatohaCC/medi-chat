import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { Tabs } from "./Tabs";

const meta = {
  title: "Shared/Tabs",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
function Example() {
  const [tab, setTab] = useState("first");
  return (
    <Tabs
      value={tab}
      onValueChange={setTab}
      label="表示切り替え"
      items={[
        { id: "first", title: "概要", content: "概要の内容" },
        { id: "second", title: "補足", content: "補足の内容" },
      ]}
    />
  );
}
export const Default: Story = { render: () => <Example /> };
