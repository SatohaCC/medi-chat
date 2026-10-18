import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { SourceEvidenceCard } from "../components/SourceEvidenceCard";
import { packageInsertMockData, realInteractionRows } from "./packageInsertData";

const meta: Meta<typeof SourceEvidenceCard> = {
  title: "Chat/SourceEvidenceCard",
  component: SourceEvidenceCard,
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "医療用医薬品添付文書の項目（1〜26項目）の根拠（エビデンス）カード表示コンポーネントです。各セクションの特性（警告・禁忌の強調、構造化された相互作用表、副作用・臨床成績・薬物動態の表やリストなど）に応じたスタイルでレンダリングされます。",
      },
    },
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "radio",
      options: ["default", "compact"],
      description: "カードの表示バリアント",
    },
    highlightWords: {
      control: "object",
      description: "ハイライト対象のキーワード配列",
    },
  },
};

export default meta;
type Story = StoryObj<typeof SourceEvidenceCard>;

// 1. 警告
export const Section1_Warnings: Story = {
  name: "1. 警告 (Warnings)",
  args: {
    source: packageInsertMockData.section1_warning,
    variant: "default",
  },
};

// 2. 禁忌
export const Section2_Contraindications: Story = {
  name: "2. 禁忌 (Contraindications)",
  args: {
    source: packageInsertMockData.section2_contraindication,
    variant: "default",
  },
};

// 3. 組成・性状
export const Section3_CompositionAndProperty: Story = {
  name: "3. 組成・性状 (Composition & Property)",
  args: {
    source: packageInsertMockData.section3_composition_property,
    variant: "default",
  },
};

// 4. 効能又は効果
export const Section4_IndicationsOrEfficacy: Story = {
  name: "4. 効能又は効果 (Indications)",
  args: {
    source: packageInsertMockData.section4_indications,
    variant: "default",
  },
};

// 5. 効能又は効果に関連する注意
export const Section5_EfficacyRelatedPrecautions: Story = {
  name: "5. 効能又は効果に関連する注意 (Precautions on Indications)",
  args: {
    source: packageInsertMockData.section5_indications_precautions,
    variant: "default",
  },
};

// 6. 用法及び用量
export const Section6_DosageAndAdministration: Story = {
  name: "6. 用法及び用量 (Dosage & Administration)",
  args: {
    source: packageInsertMockData.section6_dosage,
    variant: "default",
  },
};

// 7. 用法及び用量に関連する注意
export const Section7_DosageRelatedPrecautions: Story = {
  name: "7. 用法及び用量に関連する注意 (Precautions on Dosage)",
  args: {
    source: packageInsertMockData.section7_dosage_precautions,
    variant: "default",
  },
};

// 8. 重要な基本的注意
export const Section8_ImportantPrecautions: Story = {
  name: "8. 重要な基本的注意 (Important Precautions)",
  args: {
    source: packageInsertMockData.section8_important_precautions,
    variant: "default",
  },
};

// 9. 特定の背景を有する患者に関する注意
export const Section9_SpecificPopulations: Story = {
  name: "9. 特定の背景を有する患者に関する注意 (Specific Populations)",
  args: {
    source: packageInsertMockData.section9_specific_populations,
    variant: "default",
  },
};

// 10. 相互作用
export const Section10_Interactions: Story = {
  name: "10. 相互作用 (Interactions - Table)",
  args: {
    source: packageInsertMockData.section10_interactions,
    variant: "default",
  },
};

// 11. 副作用
export const Section11_AdverseReactions: Story = {
  name: "11. 副作用 (Adverse Reactions)",
  args: {
    source: packageInsertMockData.section11_adverse_reactions,
    variant: "default",
  },
};

// 12. 臨床検査結果に及ぼす影響
export const Section12_EffectsOnLaboratoryTests: Story = {
  name: "12. 臨床検査結果に及ぼす影響 (Lab Tests)",
  args: {
    source: packageInsertMockData.section12_lab_tests,
    variant: "default",
  },
};

// 13. 過量投与
export const Section13_Overdosage: Story = {
  name: "13. 過量投与 (Overdosage)",
  args: {
    source: packageInsertMockData.section13_overdosage,
    variant: "default",
  },
};

// 14. 適用上の注意
export const Section14_PrecautionsConcerningUse: Story = {
  name: "14. 適用上の注意 (Precautions Concerning Use)",
  args: {
    source: packageInsertMockData.section14_precautions_concerning_use,
    variant: "default",
  },
};

// 15. その他の注意
export const Section15_OtherPrecautions: Story = {
  name: "15. その他の注意 (Other Precautions)",
  args: {
    source: packageInsertMockData.section15_other_precautions,
    variant: "default",
  },
};

// 16. 薬物動態
export const Section16_Pharmacokinetics: Story = {
  name: "16. 薬物動態 (Pharmacokinetics)",
  args: {
    source: packageInsertMockData.section16_pharmacokinetics,
    variant: "default",
  },
};

// 17. 臨床成績
export const Section17_ClinicalStudies: Story = {
  name: "17. 臨床成績 (Clinical Studies)",
  args: {
    source: packageInsertMockData.section17_clinical_studies,
    variant: "default",
  },
};

// 18. 薬効薬理
export const Section18_Pharmacology: Story = {
  name: "18. 薬効薬理 (Pharmacology)",
  args: {
    source: packageInsertMockData.section18_pharmacology,
    variant: "default",
  },
};

// 19. 有効成分に関する理化学的知見
export const Section19_PhysicochemicalProperties: Story = {
  name: "19. 有効成分に関する理化学的知見 (Physicochemical)",
  args: {
    source: packageInsertMockData.section19_physicochemical,
    variant: "default",
  },
};

// 20. 取扱い上の注意
export const Section20_PrecautionsForHandling: Story = {
  name: "20. 取扱い上の注意 (Handling)",
  args: {
    source: packageInsertMockData.section20_handling,
    variant: "default",
  },
};

// 21. 承認条件
export const Section21_ApprovalConditions: Story = {
  name: "21. 承認条件 (Approval Conditions)",
  args: {
    source: packageInsertMockData.section21_approval_conditions,
    variant: "default",
  },
};

// 22. 包装
export const Section22_Packaging: Story = {
  name: "22. 包装 (Packaging)",
  args: {
    source: packageInsertMockData.section22_packaging,
    variant: "default",
  },
};

// 23. 主要文献
export const Section23_References: Story = {
  name: "23. 主要文献 (References)",
  args: {
    source: packageInsertMockData.section23_references,
    variant: "default",
  },
};

// 24. 文献請求先及び問い合わせ先
export const Section24_Inquiries: Story = {
  name: "24. 文献請求先及び問い合わせ先 (Inquiries)",
  args: {
    source: packageInsertMockData.section24_inquiries,
    variant: "default",
  },
};

// 25. 保険給付上の注意
export const Section25_InsuranceReimbursement: Story = {
  name: "25. 保険給付上の注意 (Insurance)",
  args: {
    source: packageInsertMockData.section25_insurance,
    variant: "default",
  },
};

// 26. 製造販売業者等
export const Section26_ManufacturerAndDistributor: Story = {
  name: "26. 製造販売業者等 (Manufacturer)",
  args: {
    source: packageInsertMockData.section26_manufacturer,
    variant: "default",
  },
};

// キーワードハイライト表示
export const WithKeywordHighlights: Story = {
  name: "検索キーワードハイライト表示",
  args: {
    source: packageInsertMockData.section1_warning,
    highlightWords: ["乳酸アシドーシス", "腎機能障害", "定期的に"],
    variant: "default",
  },
};

// コンパクトバリアント
export const CompactVariant: Story = {
  name: "コンパクト表示 (Compact Variant)",
  args: {
    source: packageInsertMockData.section2_contraindication,
    variant: "compact",
  },
};

// 【実データ】メトグルコ × ヨード造影剤（併用注意）
export const RealMetglucoInteractionContrastAgent: Story = {
  name: "【実データ】メトグルコ × ヨード造影剤（併用注意）",
  args: {
    source: realInteractionRows.metgluco_contrast_agent,
    variant: "default",
    highlightWords: ["乳酸アシドーシス", "一時的に中止"],
  },
};

// 【実データ】メトグルコ × アルコール（併用禁忌）
export const RealMetglucoInteractionAlcohol: Story = {
  name: "【実データ】メトグルコ × アルコール（併用禁忌）",
  args: {
    source: realInteractionRows.metgluco_alcohol,
    variant: "default",
    highlightWords: ["アルコール", "乳酸アシドーシス"],
  },
};

// 【実データ】イグザレルト × イトラコナゾール等（併用禁忌）
export const RealXareltoInteractionItraconazole: Story = {
  name: "【実データ】イグザレルト × イトラコナゾール等（併用禁忌）",
  args: {
    source: realInteractionRows.xarelto_itraconazole,
    variant: "default",
    highlightWords: ["イトラコナゾール", "出血"],
  },
};

// 【実データ】カロナール × リチウム製剤（併用注意）
export const RealCalonalInteractionWarfarin: Story = {
  name: "【実データ】カロナール × リチウム製剤（併用注意）",
  args: {
    source: realInteractionRows.calonal_warfarin,
    variant: "default",
    highlightWords: ["リチウム", "中毒"],
  },
};
