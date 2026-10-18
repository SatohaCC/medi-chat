import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { SourceEvidencePanel } from "../components/SourceEvidencePanel";
import {
  packageInsertMockData,
  realCalonalEvidence,
  realMetglucoEvidence,
  realXareltoEvidence,
} from "./packageInsertData";

const meta: Meta<typeof SourceEvidencePanel> = {
  title: "Chat/SourceEvidencePanel",
  component: SourceEvidencePanel,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "チャット画面の右側に展開される添付文書根拠引用パネルです。複数の項目（警告、禁忌、用法用量、相互作用、副作用など）を項目別フィルター付きで一覧表示・確認できます。",
      },
    },
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof SourceEvidencePanel>;

export const MultipleSectionsRetrieved: Story = {
  name: "複数項目取得時（統合根拠表示）",
  args: {
    sources: [
      packageInsertMockData.section1_warning,
      packageInsertMockData.section2_contraindication,
      packageInsertMockData.section6_dosage,
      packageInsertMockData.section10_interactions,
      packageInsertMockData.section11_adverse_reactions,
      packageInsertMockData.section16_pharmacokinetics,
    ],
    retrievalStatus: "complete",
    onClose: () => alert("Close panel clicked"),
  },
};

export const All26SectionsOverview: Story = {
  name: "26全項目一覧プレビュー",
  args: {
    sources: Object.values(packageInsertMockData),
    retrievalStatus: "complete",
    onClose: () => alert("Close panel clicked"),
  },
};

export const JevSearchingState: Story = {
  name: "Jev判定取得中状態 (jev_searching)",
  args: {
    sources: [
      packageInsertMockData.section1_warning,
      packageInsertMockData.section2_contraindication,
    ],
    retrievalStatus: "jev_searching",
    onClose: () => alert("Close panel clicked"),
  },
};

export const RealMetglucoAllSections: Story = {
  name: "【実データ】メトグルコ錠（全登録セクション一覧）",
  args: {
    sources: realMetglucoEvidence,
    retrievalStatus: "complete",
    onClose: () => alert("Close panel clicked"),
  },
};

export const RealXareltoAllSections: Story = {
  name: "【実データ】イグザレルト錠（全登録セクション一覧）",
  args: {
    sources: realXareltoEvidence,
    retrievalStatus: "complete",
    onClose: () => alert("Close panel clicked"),
  },
};

export const RealCalonalAllSections: Story = {
  name: "【実データ】カロナール錠（全登録セクション一覧）",
  args: {
    sources: realCalonalEvidence,
    retrievalStatus: "complete",
    onClose: () => alert("Close panel clicked"),
  },
};
