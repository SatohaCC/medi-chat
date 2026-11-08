import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { S2ClientProvider } from "../../providers/S2ClientProvider";
import { PromptDocument, TokenPromptInput } from "./index";

const meta = {
  title: "Shared/TokenPromptInput",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
function Example() {
  const [value, setValue] = useState(() => new PromptDocument([]));
  const [submitted, setSubmitted] = useState("");
  return (
    <S2ClientProvider>
      <TokenPromptInput
        maxLength={20}
        value={value}
        onChange={setValue}
        onSubmit={(next) =>
          setSubmitted(next.segments.map((segment) => segment.text).join(""))
        }
        searchCompletions={(query) =>
          "テスト候補".includes(query)
            ? [
                {
                  id: "example",
                  label: "テスト候補",
                  token: {
                    type: "custom",
                    anchor: "@",
                    valueType: "example",
                    data: { id: "example" },
                  },
                },
              ]
            : []
        }
        serialize={(document) =>
          document.segments.map((segment) => segment.text).join("")
        }
        accessibleLabel="入力内容"
        placeholder="入力してください"
        sendLabel="送信"
        stopLabel="停止"
        stoppingLabel="停止中"
        lengthError="20文字以内で入力してください"
      />
      <output aria-label="送信内容">{submitted}</output>
      <button
        type="button"
        onClick={() =>
          setValue(new PromptDocument([{ type: "text", text: "復元した内容" }]))
        }
      >
        内容を復元
      </button>
    </S2ClientProvider>
  );
}
export const Default: Story = { render: () => <Example /> };
