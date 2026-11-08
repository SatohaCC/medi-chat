import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { ToggleButton } from "./ToggleButton";

const meta = {
  title: "Shared/ToggleButton",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
function Examples() {
  const [selected, setSelected] = useState(false);
  return (
    <main>
      <ToggleButton selected={selected} onSelectedChange={setSelected}>
        オプション
      </ToggleButton>
      <ToggleButton selected onSelectedChange={() => {}} variant="chip">
        選択済み
      </ToggleButton>
      <ToggleButton selected onSelectedChange={() => {}} tone="positive">
        成功
      </ToggleButton>
      <ToggleButton selected onSelectedChange={() => {}} tone="warning">
        警告
      </ToggleButton>
      <ToggleButton selected={false} onSelectedChange={() => {}} disabled>
        無効な選択
      </ToggleButton>
    </main>
  );
}
export const States: Story = { render: () => <Examples /> };
