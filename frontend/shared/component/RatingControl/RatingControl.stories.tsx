import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { RatingControl, type RatingValue } from "./RatingControl";

const meta = { title: "Shared/RatingControl" } satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
function Example() {
  const [value, setValue] = useState<RatingValue>(null);
  return (
    <RatingControl
      value={value}
      onChange={setValue}
      confirmed={Boolean(value)}
      disabled={false}
      label="テスト評価"
      pendingLabel="送信中"
      successLabel="送信済み"
      retryLabel="再試行"
    />
  );
}
export const Default: Story = { render: () => <Example /> };
