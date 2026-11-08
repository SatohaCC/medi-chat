import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { S2ClientProvider } from "../../providers/S2ClientProvider";
import { AriaButton, Button, SpectrumButton } from "./index";

const meta = {
  title: "Shared/Button",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
function Examples() {
  const [count, setCount] = useState(0);
  return (
    <main>
      <Button onActivate={() => setCount((value) => value + 1)}>実行</Button>
      <Button disabled>無効な操作</Button>
      <Button variant="compact">コンパクト</Button>
      <Button variant="compact" tone="positive">
        完了
      </Button>
      <Button variant="text">テキスト</Button>
      <output aria-label="実行回数">{count}</output>
      <S2ClientProvider>
        <SpectrumButton onPress={() => setCount((value) => value + 1)}>
          Spectrumの操作
        </SpectrumButton>
      </S2ClientProvider>
      <AriaButton onPress={() => setCount((value) => value + 1)}>Ariaの操作</AriaButton>
    </main>
  );
}
export const States: Story = { render: () => <Examples /> };
