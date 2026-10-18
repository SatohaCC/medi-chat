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

export const JevInspectorActive: Story = {
  name: "Jev判定インスペクター表示時（右列タブ展開）",
  args: {
    sources: [packageInsertMockData.section10_interactions],
    retrievalStatus: "complete",
    activeTab: "jev",
    jevResponse: {
      answers: {
        intent: {
          choice: "interaction",
          confidence: 0.98,
          probabilities: {
            interaction: 0.98,
            dosage: 0.01,
            adverse_events: 0.005,
          },
        },
      },
      model: "jev-classifier-v1",
    },
    onClose: () => alert("Close panel clicked"),
  },
};

export const AvailableSectionsOverview: Story = {
  name: "原本に存在する24大項目の一覧（複数文書）",
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

export const WithSearchHighlightWords: Story = {
  name: "キーワードハイライト＆続きを読む表示（メトグルコ実データ）",
  args: {
    sources: realMetglucoEvidence,
    retrievalStatus: "complete",
    highlightWords: ["乳酸アシドーシス", "腎機能障害", "定期的に"],
    onClose: () => alert("Close panel clicked"),
  },
};
