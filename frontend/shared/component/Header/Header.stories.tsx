import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { Button } from "../../ui/Button";
import { Link } from "../../ui/Link";
import { HighlightText } from "../HighlightText";
import { MarkdownContent } from "../MarkdownContent";
import { PageLayout } from "../PageLayout";
import { Header } from "./Header";

const meta = {
  title: "Shared/Header",
  parameters: { layout: "fullscreen" },
} satisfies Meta;
export default meta;
type Story = StoryObj<typeof meta>;
export const Workspace: Story = {
  render: () => (
    <PageLayout screen="shared-example">
      <Header
        brand={<h1>Example workspace</h1>}
        renderNavigation={(_mobile, close) => (
          <nav aria-label="ページ一覧">
            <Link href="#overview" onPress={close}>
              概要
            </Link>
            <Link href="#details" onPress={close}>
              詳細
            </Link>
          </nav>
        )}
        actions={<Button>任意の操作</Button>}
        controlsLabel="表示設定"
      >
        表示オプション
      </Header>
      <main id="overview">
        <MarkdownContent
          content={
            "## 任意のコンテンツ\n\n[リンク](https://example.test)と**強調**を表示します。"
          }
        />
        <HighlightText text="表示内容を強調します" words={["強調"]} />
      </main>
    </PageLayout>
  ),
};

function ConnectionStatusExample({ withControls }: { withControls: boolean }) {
  return (
    <Header
      brand={<h1>接続状態のヘッダー</h1>}
      renderNavigation={() => <nav aria-label="ページ一覧">概要</nav>}
      connectionStatus={<span role="status">接続済み</span>}
      controlsLabel={withControls ? "表示設定" : undefined}
    >
      {withControls ? <span>表示オプション</span> : undefined}
    </Header>
  );
}

export const ConnectionStatusOnly: Story = {
  render: () => <ConnectionStatusExample withControls={false} />,
};

export const ConnectionStatusWithControls: Story = {
  render: () => <ConnectionStatusExample withControls />,
};
