export const JEV_INTENT_META: Record<string, { label: string; desc: string }> = {
  warnings: {
    label: "警告",
    desc: "1. 致死的な副作用、重大な事故防止に関する質問",
  },
  contraindications: {
    label: "禁忌",
    desc: "2. 投与してはいけない患者、使用禁止・禁忌事項に関する質問",
  },
  composition: {
    label: "組成",
    desc: "3.1 有効成分の名称・含量、添加剤に関する質問",
  },
  appearance: {
    label: "組成・性状",
    desc: "3. 剤形、識別コード、色、外観、粉砕可否に関する質問",
  },
  composition_and_appearance: {
    label: "組成・性状",
    desc: "3. 成分・含量、剤形、識別コード、色、外観に関する質問",
  },
  indications: {
    label: "効能・効果",
    desc: "4/5. どんな病気や症状に効くか、適応症、効能関連注意に関する質問",
  },
  dosage: {
    label: "用法・用量",
    desc: "6/7. 飲み方、服用量、投与回数、投与間隔、休薬、用量調節に関する質問",
  },
  important_precautions: {
    label: "重要な基本的注意",
    desc: "8. 定期検査の必要性、車の運転制限などの危険作業制限に関する質問",
  },
  specific_populations: {
    label: "特定の背景を有する患者",
    desc: "9. 合併症、臓器障害、年齢等の特定の背景に関する質問",
  },
  complications_or_history: {
    label: "合併症・既往歴等",
    desc: "9.1 持病、既往症、基礎疾患のある患者への投与注意に関する質問",
  },
  renal_impairment: {
    label: "腎機能障害",
    desc: "9.2 腎機能障害患者、透析患者、eGFR低下時の投与や用量調節に関する質問",
  },
  hepatic_impairment: {
    label: "肝機能障害",
    desc: "9.3 肝疾患・Child-Pugh分類等に応じた投与に関する質問",
  },
  reproductive_potential: {
    label: "生殖能を有する者",
    desc: "9.4 妊娠可能な女性、避妊の必要性に関する質問",
  },
  pregnancy: {
    label: "妊婦",
    desc: "9.5 妊娠中の投与可否、胎児への影響に関する質問",
  },
  nursing: {
    label: "授乳婦",
    desc: "9.6 母乳移行、授乳中の投与や授乳中止の指示に関する質問",
  },
  pediatric: {
    label: "小児等",
    desc: "9.7 小児、子ども、乳児への投与、小児での安全性に関する質問",
  },
  elderly: {
    label: "高齢者",
    desc: "9.8 高齢者への投与、生理機能低下、用量注意に関する質問",
  },
  interaction: {
    label: "相互作用・飲み合わせ",
    desc: "10. 他の薬剤や飲食物との飲み合わせ、併用禁忌、併用注意に関する質問",
  },
  adverse_events: {
    label: "副作用・有害事象",
    desc: "11. 副作用、有害事象、自覚症状、初期症状、重大な副作用に関する質問",
  },
  laboratory_influences: {
    label: "臨床検査への影響",
    desc: "12. 検査値への干渉、偽陽性・偽陰性に関する質問",
  },
  overdosage: {
    label: "過量投与",
    desc: "13. 飲み過ぎ・過量服用時の症状、処置、解毒剤・拮抗薬に関する質問",
  },
  precautions_for_application: {
    label: "適用上の注意",
    desc: "14. 服用時・調剤時の注意、PTP誤飲防止、噛み砕き禁止等に関する質問",
  },
  other_precautions: {
    label: "その他の注意",
    desc: "15. 臨床使用や動物実験・非臨床試験に基づく注意に関する質問",
  },
  pharmacokinetics: {
    label: "薬物動態",
    desc: "16. 血中濃度（Cmax、半減期T1/2）、吸収、代謝酵素（CYP）、排泄に関する質問",
  },
  clinical_studies: {
    label: "臨床成績",
    desc: "17. 臨床試験、治験成績、有効率、市販後使用成績調査データに関する質問",
  },
  pharmacology: {
    label: "薬効薬理",
    desc: "18. 作用機序、作用メカニズム、薬理活性に関する質問",
  },
  physicochemical_properties: {
    label: "理化学的知見",
    desc: "19. 有効成分の化学構造式、分子量、性状、融点に関する質問",
  },
  storage_and_handling: {
    label: "取扱い上の注意",
    desc: "20. 保管方法、貯法、遮光、使用期限、廃棄方法に関する質問",
  },
  conditions_of_approval: {
    label: "承認条件",
    desc: "21. 全例調査、RMP（医薬品リスク管理計画）などの承認条件に関する質問",
  },
  packaging: {
    label: "包装",
    desc: "22. 包装規格、PTPシート、バラ包装に関する質問",
  },
  literature: {
    label: "主要文献",
    desc: "23. 引用文献、公表論文、社内資料に関する質問",
  },
  contact_info: {
    label: "文献請求先・窓口",
    desc: "24. くすり相談窓口、学術情報部の連絡先に関する質問",
  },
  insurance_benefits: {
    label: "保険給付上の注意",
    desc: "25. 保険適用の留意点や給付制限に関する質問",
  },
  manufacturer_info: {
    label: "製造販売業者等",
    desc: "26. 製薬企業、発売元、製造販売元に関する質問",
  },
  general_or_other: {
    label: "一般・その他",
    desc: "上記いずれにも該当しない質問、雑談、一般的な質問",
  },
};
