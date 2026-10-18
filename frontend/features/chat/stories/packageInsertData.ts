/* eslint-disable */
// このファイルは実データベース（data/pmda/structured/.chat-search.sqlite3）から生成された実際のPMDA添付文書データです。
// 生成スクリプト: node scripts/export-storybook-evidence.mjs

import type { SourceItem } from "../model/chat";

export const packageInsertMockData: Record<string, SourceItem> = {
  section1_warning: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "1",
      title: "警告",
    },
    kind: "section",
    excerpt:
      "<p>重篤な乳酸アシドーシスを起こすことがあり、死亡に至った例も報告されている。乳酸アシドーシスを起こしやすい患者には投与しないこと。</p><p>腎機能障害又は肝機能障害のある患者、高齢者に投与する場合には、定期的に腎機能や肝機能を確認するなど慎重に投与すること。特に75歳以上の高齢者では、本剤投与の適否を慎重に判断すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section2_contraindication: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "2",
      title: "禁忌",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>乳酸アシドーシスの既往のある患者</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>重度の腎機能障害（eGFR 30mL/min/1.73m²未満）のある患者又は透析患者（腹膜透析を含む）</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>重度の肝機能障害のある患者</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>心血管系、肺機能に高度の障害（ショック、心不全、心筋梗塞、肺塞栓等）のある患者及びその他の低酸素血症を伴いやすい状態にある患者［嫌気的解糖の亢進により乳酸産生が増加する。］</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>脱水症の患者又は脱水状態が懸念される患者（下痢、嘔吐等の胃腸障害のある患者、経口摂取が困難な患者等）</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>過度のアルコール摂取者</p><p>重症ケトーシス、糖尿病性昏睡又は前昏睡、1型糖尿病の患者［輸液、インスリンによる速やかな高血糖の是正が必須である。］</p><p>重症感染症、手術前後、重篤な外傷のある患者［インスリン注射による血糖管理が望まれるので本剤の投与は適さない。また、乳酸アシドーシスを起こしやすい。］</p><p>栄養不良状態、飢餓状態、衰弱状態、脳下垂体機能不全又は副腎機能不全の患者［低血糖を起こすおそれがある。］</p><p>妊婦又は妊娠している可能性のある女性</p><p>本剤の成分又はビグアナイド系薬剤に対し過敏症の既往歴のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_PatientsWithRenalImpairment_20220920113045_20",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_PatientsWithHepaticImpairment_20220920113045_23",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_MalesAndFemalesOfReproductivePotential",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section3_composition_property: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:3.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "3.2",
      title: "製剤の性状",
    },
    kind: "section",
    excerpt:
      "<p>割線入りのフィルムコート錠</p><p>白色～帯黄白色</p><p>［図:400093_3962002F2027_fig01.gif］</p><p>約9.1mm</p><p>約4.1mm</p><p>約271mg</p><p>DS271</p><p>割線入りのフィルムコート錠</p><p>白色～帯黄白色</p><p>［図:400093_3962002F2027_fig02.gif］</p><p>約15.8mm</p><p>約7.3mm</p><p>約5.7mm</p><p>約538mg</p><p>DS272</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section4_indications: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:4",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "4",
      title: "効能又は効果",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈2型糖尿病〉</strong></p><p>ただし、下記のいずれかの治療で十分な効果が得られない場合に限る。<br>（1）食事療法・運動療法のみ<br>（2）食事療法・運動療法に加えてスルホニルウレア剤を使用</p><p><strong>〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉</strong></p><p>ただし、肥満、耐糖能異常、又はインスリン抵抗性のいずれかを呈する患者に限る。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section5_indications_precautions: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:5",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "5",
      title: "効能又は効果に関連する注意",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>糖尿病を合併する多嚢胞性卵巣症候群の患者では糖尿病の治療を優先すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発〉〉</strong></p><p>ゴナドトロピン製剤を除く排卵誘発薬で十分な効果が得られない場合に本剤の併用を考慮すること。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section6_dosage: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:6",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "6",
      title: "用法及び用量",
    },
    kind: "section",
    excerpt:
      "<p>〈2型糖尿病〉<br>通常、成人にはメトホルミン塩酸塩として1日500mgより開始し、1日2～3回に分割して食直前又は食後に経口投与する。維持量は効果を観察しながら決めるが、通常1日750～1,500mgとする。なお、患者の状態により適宜増減するが、1日最高投与量は2,250mgまでとする。<br>通常、10歳以上の小児にはメトホルミン塩酸塩として1日500mgより開始し、1日2～3回に分割して食直前又は食後に経口投与する。維持量は効果を観察しながら決めるが、通常1日500～1,500mgとする。なお、患者の状態により適宜増減するが、1日最高投与量は2,000mgまでとする。</p><p>〈多嚢胞性卵巣症候群における排卵誘発〉<br>他の排卵誘発薬との併用で、通常、メトホルミン塩酸塩として500mgの1日1回経口投与より開始する。患者の忍容性を確認しながら増量し、1日投与量として1,500mgを超えない範囲で、1日2～3回に分割して経口投与する。なお、本剤は排卵までに中止する。</p><p>〈多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉</p><p>他の卵巣刺激薬との併用で、通常、メトホルミン塩酸塩として500mgの1日1回経口投与より開始する。患者の忍容性を確認しながら増量し、1日投与量として1,500mgを超えない範囲で、1日2～3回に分割して経口投与する。なお、本剤は採卵までに中止する。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section7_dosage_precautions: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:7",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "7",
      title: "用法及び用量に関連する注意",
    },
    kind: "section",
    excerpt:
      '<p>中等度の腎機能障害のある患者（eGFR 30mL/min/1.73m²以上60mL/min/1.73m²未満）では、メトホルミンの血中濃度が上昇し、乳酸アシドーシスの発現リスクが高くなる可能性があるため、以下の点に注意すること。特に、eGFRが30mL/min/1.73m²以上45mL/min/1.73m²未満の患者には、治療上の有益性が危険性を上回ると判断される場合にのみ投与すること。</p><p>投与は、少量より開始すること。</p><p>投与中は、より頻回に腎機能（eGFR等）を確認するなど慎重に経過を観察し、投与の適否及び投与量の調節を検討すること。</p><p>効果不十分な場合は、メトホルミン塩酸塩として1日最高投与量を下表の目安まで増量することができるが、効果を観察しながら徐々に増量すること。また、投与にあたっては、1日量を1日2～3回分割投与すること。</p><p>中等度の腎機能障害のある患者における1日最高投与量の目安</p><table><thead><tr><th>推算糸球体濾過量（eGFR）\n（mL/min/1.73m²）</th><th>1日最高投与量の目安</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">推算糸球体濾過量（eGFR）<br>（mL/min/1.73m²）</td><td rowspan="1" colspan="1">1日最高投与量の目安</td></tr><tr><td rowspan="1" colspan="1">45 ≦ eGFR ＜ 60</td><td rowspan="1" colspan="1">1,500mg</td></tr><tr><td rowspan="1" colspan="1">30 ≦ eGFR ＜ 45</td><td rowspan="1" colspan="1">750mg</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_PatientsWithRenalImpairment_20220920113045_21",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SpecificPopulation_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section8_important_precautions: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:8",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "8",
      title: "重要な基本的注意",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈効能共通〉〉</strong></p><p>まれに重篤な乳酸アシドーシスを起こすことがある。リスク因子としては、腎機能障害、肝機能障害、低酸素血症を伴いやすい状態、脱水（利尿作用を有する薬剤の併用を含む）、過度のアルコール摂取、感染症、高齢者等が知られている。特に、脱水、過度のアルコール摂取等により患者の状態が急変することもあるので、以下の点に注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>(1)本剤の投与開始前及びその後も投与中は定期的に、腎機能（eGFR等）及び肝機能を確認するとともに、患者の状態に十分注意して投与の適否及び投与量の調節を検討すること。なお、高齢者等、特に慎重な経過観察が必要な場合には、より頻回に確認すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>(2)脱水症状があらわれた場合には投与を中止し、適切な処置を行うこと。利尿作用を有する薬剤（利尿剤、SGLT2阻害剤等）との併用時には、特に脱水に注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈(3)本剤の投与開始時及びその後も投与中は適切に、以下の内容を患者及びその家族に十分指導すること。〉</strong></p><p>過度のアルコール摂取を避けること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈(3)本剤の投与開始時及びその後も投与中は適切に、以下の内容を患者及びその家族に十分指導すること。〉</strong></p><p>発熱、下痢、嘔吐、食事摂取不良等の体調不良（シックデイ）の時は、脱水状態が懸念されるため、いったん服用を中止し、医師に相談すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈(3)本剤の投与開始時及びその後も投与中は適切に、以下の内容を患者及びその家族に十分指導すること。〉</strong></p><p>乳酸アシドーシスの症状（胃腸障害、倦怠感、筋肉痛、過呼吸等）があらわれた場合には、直ちに受診すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>(4)ヨード造影剤を用いて検査を行う患者においては、本剤の併用により乳酸アシドーシスを起こすことがあるので、検査前は本剤の投与を一時的に中止すること（ただし、緊急に検査を行う必要がある場合を除く）。ヨード造影剤投与後48時間は本剤の投与を再開しないこと。なお、投与再開時には、患者の状態に注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>低血糖症状を起こすことがあるので、高所作業、自動車の運転等に従事している患者に投与するときには注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>本剤の使用にあたっては、患者及びその家族に対し低血糖症状及びその対処方法について十分説明すること。</p><p><strong>〈〈2型糖尿病〉〉</strong></p><p>投与する場合には、少量より開始し、血糖値、尿糖等を定期的に検査し、薬剤の効果を確かめ、本剤を3～4ヵ月投与しても効果が不十分な場合には、速やかに他の治療法への切り替えを行うこと。</p><p><strong>〈〈2型糖尿病〉〉</strong></p><p>本剤とイメグリミン塩酸塩は作用機序の一部が共通している可能性があること、また、イメグリミン塩酸塩の国内臨床試験において、ビグアナイド系薬剤と併用した場合、他の糖尿病用薬との併用療法と比較して消化器症状が多く認められたとの報告があることから、併用薬剤の選択の際には留意すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>本剤は、不妊治療に十分な知識と経験のある医師のもとで使用すること。本剤投与により予想されるリスク及び妊娠初期の本剤の服用を避けるための服用中止時期について、あらかじめ患者に説明を行うこと。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p><strong>〈患者に対しては、あらかじめ以下の点を説明すること。〉</strong></p><p>本剤との関連は明確ではないが、本剤を用いた不妊治療において、卵巣過剰刺激症候群があらわれることがあるので、自覚症状（下腹部痛、下腹部緊迫感、悪心、腰痛等）や急激な体重増加が認められた場合には直ちに医師等に相談すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p><strong>〈患者に対しては、あらかじめ以下の点を説明すること。〉</strong></p><p>多嚢胞性卵巣症候群における排卵誘発に本剤を用いた場合、卵巣過剰刺激の結果として多胎妊娠となる可能性があること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_MalesAndFemalesOfReproductivePotential",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section9_specific_populations: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.2",
      title: "腎機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>腎臓における排泄が減少しメトホルミンの血中濃度が上昇するため、乳酸アシドーシス等の発現リスクが高くなる可能性がある。</p><p>重度の腎機能障害のある患者（eGFR 30mL/min/1.73m²未満）又は透析患者（腹膜透析を含む）<br>投与しないこと。</p><p>中等度の腎機能障害のある患者（eGFR 30mL/min/1.73m²以上60mL/min/1.73m²未満）<br>慎重に経過を観察し、投与の適否及び投与量の調節を検討すること。特に、eGFRが30mL/min/1.73m²以上45mL/min/1.73m²未満の患者には、治療上の有益性が危険性を上回ると判断される場合にのみ投与すること。</p><p>軽度の腎機能障害のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SpecificPopulation_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section10_interactions: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.2:row-0",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "interaction_row",
    excerpt:
      "ヨード造影剤\n併用により乳酸アシドーシスを起こすことがある。\nヨード造影剤を用いて検査を行う場合には、本剤の投与を一時的に中止すること。\n腎機能が低下し、本剤の排泄が低下することが考えられている。",
    columns: {
      drug_name: "ヨード造影剤",
      clinical_symptoms_and_measures:
        "併用により乳酸アシドーシスを起こすことがある。\nヨード造影剤を用いて検査を行う場合には、本剤の投与を一時的に中止すること。",
      mechanism_and_risk_factors:
        "腎機能が低下し、本剤の排泄が低下することが考えられている。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section11_adverse_reactions: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:11.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "11.1",
      title: "重大な副作用",
    },
    kind: "section",
    excerpt:
      "<p>乳酸アシドーシス（頻度不明）<br>乳酸アシドーシス（血中乳酸値の上昇、乳酸/ピルビン酸比の上昇、血液pHの低下等を示す）は予後不良のことが多い。一般的に発現する臨床症状は様々であるが、胃腸症状、倦怠感、筋肉痛、過呼吸等の症状がみられることが多く、これらの症状があらわれた場合には直ちに投与を中止し、必要な検査を行うこと。なお、乳酸アシドーシスの疑いが大きい場合には、乳酸の測定結果等を待つことなく適切な処置を行うこと。</p><p>低血糖（5%以上）<br>低血糖症状（初期症状:脱力感、高度の空腹感、発汗等）が認められた場合には糖質を含む食品を摂取するなど適切な処置を行うこと。ただし、α-グルコシダーゼ阻害剤との併用により低血糖症状が認められた場合にはブドウ糖を投与すること。</p><p>肝機能障害、黄疸（頻度不明）<br>AST、ALT、ALP、γ-GTP、ビリルビンの著しい上昇等を伴う肝機能障害、黄疸があらわれることがある。</p><p>横紋筋融解症（頻度不明）<br>筋肉痛、脱力感、CK上昇、血中及び尿中ミオグロビン上昇を特徴とする横紋筋融解症があらわれることがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "13.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_OverDosage_20220920113045_29",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "17.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_EfficacyAndSafety_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  section12_lab_tests: {
    unit_id: "sec-12-lab-tests-pmda-standard",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "12",
      title: "臨床検査結果に及ぼす影響",
    },
    kind: "section",
    excerpt: "<p>本剤投与により、尿中ケトン体検査において偽陽性を示すことがある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["keyword"],
  },
  section13_overdosage: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:13",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "13",
      title: "過量投与",
    },
    kind: "section",
    excerpt:
      "<p>症状<br>乳酸アシドーシスが起こることがある。</p><p>処置<br>アシドーシスの補正（炭酸水素ナトリウム静注等）、輸液（強制利尿）、血液透析等の適切な処置を行う。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section14_precautions_concerning_use: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:14",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "14",
      title: "適用上の注意",
    },
    kind: "section",
    excerpt:
      "<p>薬剤調製時の注意 本剤とオルメサルタン メドキソミル製剤等との一包化は避けること。一包化して高温高湿度条件下にて保存した場合、本剤が変色することがある。</p><p>薬剤交付時の注意 PTP包装の薬剤はPTPシートから取り出して服用するよう指導すること。PTPシートの誤飲により、硬い鋭角部が食道粘膜へ刺入し、更には穿孔をおこして縦隔洞炎等の重篤な合併症を併発することがある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section15_other_precautions: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:15.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "15.1",
      title: "臨床使用に基づく情報",
    },
    kind: "section",
    excerpt:
      "<p>インスリン又は経口血糖降下剤の投与中にアンジオテンシン変換酵素阻害剤を投与することにより、低血糖が起こりやすいとの報告がある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section16_pharmacokinetics: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.1",
      title: "血中濃度",
    },
    kind: "section",
    excerpt:
      '<p>単回投与<br>健康成人男性にメトホルミン塩酸塩を空腹時に単回経口投与したときの血漿中メトホルミン濃度推移及び薬物動態パラメータは以下のとおりであった。</p><p><strong>〈単回投与〉</strong></p><p></p><p><strong>〈単回投与〉</strong></p><table><thead><tr><th>投与量</th><th>T_{max}\n（h）</th><th>C_{max}\n（ng/mL）</th><th>AUC_{0-48}\n（ng・h/mL）</th><th>T_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">投与量</td><td rowspan="1" colspan="1">T_{max}<br>（h）</td><td rowspan="1" colspan="1">C_{max}<br>（ng/mL）</td><td rowspan="1" colspan="1">AUC_{0-48}<br>（ng・h/mL）</td><td rowspan="1" colspan="1">T_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">250mg（6例）</td><td rowspan="1" colspan="1">1.9 ± 1.1</td><td rowspan="1" colspan="1">898 ± 168</td><td rowspan="1" colspan="1">4,861 ± 577</td><td rowspan="1" colspan="1">2.9 ± 0.6</td></tr><tr><td rowspan="1" colspan="1">500mg（6例）</td><td rowspan="1" colspan="1">2.3 ± 0.9</td><td rowspan="1" colspan="1">1,341 ± 329</td><td rowspan="1" colspan="1">8,019 ± 2,347</td><td rowspan="1" colspan="1">4.0 ± 1.4</td></tr><tr><td rowspan="1" colspan="1">750mg（12例）</td><td rowspan="1" colspan="1">2.1 ± 0.7</td><td rowspan="1" colspan="1">2,163 ± 517</td><td rowspan="1" colspan="1">11,802 ± 2,221</td><td rowspan="1" colspan="1">4.7 ±1.7</td></tr></tbody></table><p><strong>〈単回投与〉</strong></p><p>平均値±標準偏差</p><p>反復投与<br>健康成人男性に1日3回メトホルミン塩酸塩500mgあるいは750mg（各9例）を6日間反復経口投与したとき、血漿中メトホルミン濃度は投与2～4日後には定常状態に達し、反復投与による蓄積性はみられなかった。</p>',
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section17_clinical_studies: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:17.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "17.1",
      title: "有効性及び安全性に関する試験",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈成人〉</strong></p><p>成人2型糖尿病患者を対象とした二重盲検比較試験を含む各種臨床試験注）において、HbA1c（NGSP）値、空腹時血糖値及びグリコアルブミン値の改善が認められた。<br>注）試験対象から以下の患者を除外した。</p><p><strong>〈成人〉</strong></p><p>投与前の血清クレアチニン値が男性1.3mg/dL以上、女性1.2mg/dL以上（酵素法）の腎機能障害を有する患者</p><p><strong>〈成人〉</strong></p><p>投与前のAST又はALTが基準値上限の2.5倍以上の患者、肝硬変患者</p><p><strong>〈成人〉</strong></p><p>20歳未満又は75歳以上の患者（長期投与試験は20歳未満のみを除外した。）</p><p><strong>〈成人〉</strong></p><p>(1)国内第Ⅱ相用量反応検討試験（単独療法）<br>食事療法・運動療法で効果不十分な2型糖尿病患者に、1回250mg又は500mgを1日3回毎食後に14週間（投与開始1週間は1回250mgを1日2回）投与した結果、HbA1c（NGSP）値（平均値±標準偏差、以下同様）はそれぞれ0.67±0.64%（106例）、1.07±0.68%（106例）低下した。<br>副作用発現頻度は、750mg/日群で47.7%（51/107例）、1,500mg/日群で69.8%（74/106例）であった。主な副作用（発現頻度10%以上）は、750mg/日群で下痢30.8%（33例）、悪心15.9%（17例）、腹痛15.0%（16例）、食欲不振11.2%（12例）、1,500mg/日群で下痢48.1%（51例）、悪心22.6%（24例）、腹痛16.0%（17例）、食欲不振15.1%（16例）であった。低血糖症の副作用は認められなかった。</p><p><strong>〈成人〉</strong></p><p>(2)国内第Ⅱ相用量反応検討試験（スルホニルウレア剤併用療法）<br>食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な2型糖尿病患者に、1回250mg又は500mgを1日3回毎食後に14週間（投与開始1週間は1回250mgを1日2回）投与した結果、HbA1c（NGSP）値はそれぞれ0.74±0.68%（102例）、1.22±0.75%（103例）低下した。<br>副作用発現頻度は、750mg/日群で58.8%（60/102例）、1,500mg/日群で75.0%(78/104例)であった。主な副作用（発現頻度10%以上）は、750mg/日群で下痢26.5%（27例）、1,500mg/日群で下痢40.4%（42例）、食欲不振14.4%（15例）、悪心13.5%（14例）であった。低血糖症の副作用は、それぞれ9.8%（10例）、21.2%（22例）に発現した。</p><p><strong>〈成人〉</strong></p><p>(3)国内第Ⅱ相長期投与試験<br>食事療法・運動療法のみ又は食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な2型糖尿病患者に、1日500mgより開始し、1日750～2,250mgを2～3回に分割して54週間投与した結果、HbA1c（NGSP）値、空腹時血糖値及びグリコアルブミン値は改善し、良好な血糖コントロールが維持された。HbA1c（NGSP）値は1.30±0.78%（165例）低下した。HbA1c（NGSP）値6.9%未満の割合は、投与開始前7.3%（12/165例）に対して14週後で65.4%（100/153例）、26週後で73.5%（108/147例）、54週後で80.7%（113/140例）であった。<br>副作用発現頻度は67.5%（114/169例）であった。主な副作用（発現頻度10%以上）は、下痢54.4%（92例）、悪心15.4%（26例）、食欲不振14.8%（25例）、腹痛10.1%（17例）であった。低血糖症の副作用は食事療法・運動療法のみの患者では発現せず、食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な患者では11.6%（10/86例）に発現した。</p><p><strong>〈小児〉</strong></p><p>(1)国内第Ⅲ相長期投与試験<br>小児2型糖尿病患者を対象とした長期投与試験注）において、HbA1c（NGSP）値、グリコアルブミン値、空腹時血糖値の改善が認められた。<br>注）試験対象から以下の患者を除外した。</p><p><strong>〈小児〉</strong></p><p><strong>〈(1)国内第Ⅲ相長期投与試験〉</strong></p><p>投与前の血清クレアチニン値が1.0mg/dL（酵素法）を超える腎機能障害を有する患者</p><p><strong>〈小児〉</strong></p><p><strong>〈(1)国内第Ⅲ相長期投与試験〉</strong></p><p>投与前のAST又はALTが基準値上限の3倍以上の患者。ただし、脂肪肝を合併している場合は基準値上限の5倍未満の患者は投与可</p><p><strong>〈小児〉</strong></p><p><strong>〈(1)国内第Ⅲ相長期投与試験〉</strong></p><p>5歳以下及び18歳以上の患者</p><p><strong>〈小児〉</strong></p><p>1日500～2,000mgを2～3回に分割して24週間（可能な場合は52週間）投与した結果は以下のとおりであった（なお、組み入れられた患者の体重は44.4～112.0kgであった）。</p><p><strong>〈小児〉</strong></p><p>（1）食事療法・運動療法で効果不十分な2型糖尿病<br>HbA1c（NGSP）値（平均値±標準偏差、以下同様）は24週間投与で0.76±0.58%（14例）低下した。52週継続例では0.71±0.69%（10例）低下した。</p><p><strong>〈小児〉</strong></p><p>（2）食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な2型糖尿病<br>HbA1c（NGSP）値は24週間投与で0.40±1.87%（4例）低下した。52週継続例では0.45±0.78%（2例）低下した。</p><p><strong>〈小児〉</strong></p><p>（3）食事療法・運動療法に加えて1日750mg以下のメトホルミンで効果不十分な2型糖尿病<br>HbA1c（NGSP）値は24週間投与で0.98±1.62%（17例）低下した。52週継続例では0.65±1.17%（13例）低下した。<br>副作用発現頻度は51.4 %（19/37例）であった。主な副作用（発現頻度10%以上）は、下痢29.7%（11例）、悪心18.9%（7例）、腹痛10.8%（4例）であった。低血糖症の副作用は認められなかった。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_08",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_09",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_10",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_11",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section18_pharmacology: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:18.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "18.1",
      title: "作用機序",
    },
    kind: "section",
    excerpt:
      "<p>主に肝臓における糖新生を抑制し、膵β細胞のインスリン分泌を介することなく血糖降下作用を示す。また、末梢組織における糖取り込みの促進、小腸における糖吸収の抑制等も知られている。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_12",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section19_physicochemical: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:19",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "19",
      title: "有効成分に関する理化学的知見",
    },
    kind: "section",
    excerpt:
      "<p>メトホルミン塩酸塩（Metformin Hydrochloride）</p><p>1,1-Dimethylbiguanide monohydrochloride</p><p>C_{4}H_{11}N_{5}・HCl</p><p>165.62</p><p>白色の結晶又は結晶性の粉末である。水に溶けやすく、酢酸（100）にやや溶けにくく、エタノール（99.5）に溶けにくい。</p><p></p><p>約221℃（分解）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section20_handling: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:20",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "20",
      title: "取扱い上の注意",
    },
    kind: "section",
    excerpt:
      "<p>錠剤を取り出すときに特異なにおいがすることがある。（本剤の原料に由来する成分による。）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section21_approval_conditions: {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:21",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "21",
      title: "承認条件",
    },
    kind: "section",
    excerpt: "<p>医薬品リスク管理計画を策定の上、適切に実施すること。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  section22_packaging: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:22",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "22",
      title: "包装",
    },
    kind: "section",
    excerpt:
      "<p>〈メトグルコ錠250mg〉<br>100錠［10錠（PTP）×10］<br>1,000錠［10錠（PTP）×100］<br>500錠［瓶、バラ、乾燥剤入り］</p><p>〈メトグルコ錠500mg〉<br>100錠［10錠（PTP）×10］<br>1,000錠［10錠（PTP）×100］<br>500錠［瓶、バラ、乾燥剤入り］</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section23_references: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:23",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "23",
      title: "主要文献",
    },
    kind: "section",
    excerpt:
      "<p>Dubourg J., et al.: Diabetes Obes Metab.2022; 24(4): 609-619</p><p>Tuchmann-Duplessis H., et al.: Compt. Rend. 1961; 253: 321-323</p><p>Pentikainen P.J., et al.: Eur. J. Clin. Pharmacol. 1979; 16: 195-202</p><p>Sambol N.C., et al.: J.Clin.Pharmacol. 1995; 35: 1094-1102</p><p>社内資料: 小児患者を対象とした長期投与試験における母集団薬物動態解析</p><p>Song I.H., et al.: J Acquir Immune Defic Syndr. 2016; 72(4): 400-407</p><p>Johansson, S., et al.: Clin Pharmacokinet. 2014; 53: 837-847</p><p>社内資料: 用量反応検討試験（単独療法）（2010年1月20日承認、CTD2.7.6.15）</p><p>社内資料: 用量反応検討試験（SU剤併用療法）（2010年1月20日承認、CTD2.7.6.16）</p><p>社内資料: 長期投与試験（2010年1月20日承認、CTD2.7.6.18）</p><p>社内資料: 小児患者を対象とした長期投与試験</p><p>Lee, A.J.: Pharmacotherapy.1996; 16: 327-351</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section24_inquiries: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:24",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "24",
      title: "文献請求先及び問い合わせ先",
    },
    kind: "section",
    excerpt:
      "<p>住友ファーマ株式会社</p><p>〒541-0045 大阪市中央区道修町2-6-8</p><p>くすり情報センター<br>TEL 0120-034-389</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  section25_insurance: {
    unit_id: "sec-25-insurance-pmda-standard",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "25",
      title: "保険給付上の注意",
    },
    kind: "section",
    excerpt: "<p>本剤は保険給付上の制限対象とならない。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["keyword"],
  },
  section26_manufacturer: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:26",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "26",
      title: "製造販売業者等",
    },
    kind: "section",
    excerpt:
      "<p>製造販売元</p><p>住友ファーマ株式会社</p><p>大阪市中央区道修町2-6-8</p><p>提携</p><p>Merck Santé（フランス）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
};

export const realMetglucoEvidence: SourceItem[] = [
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "1",
      title: "警告",
    },
    kind: "section",
    excerpt:
      "<p>重篤な乳酸アシドーシスを起こすことがあり、死亡に至った例も報告されている。乳酸アシドーシスを起こしやすい患者には投与しないこと。</p><p>腎機能障害又は肝機能障害のある患者、高齢者に投与する場合には、定期的に腎機能や肝機能を確認するなど慎重に投与すること。特に75歳以上の高齢者では、本剤投与の適否を慎重に判断すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "2",
      title: "禁忌",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>乳酸アシドーシスの既往のある患者</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>重度の腎機能障害（eGFR 30mL/min/1.73m²未満）のある患者又は透析患者（腹膜透析を含む）</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>重度の肝機能障害のある患者</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>心血管系、肺機能に高度の障害（ショック、心不全、心筋梗塞、肺塞栓等）のある患者及びその他の低酸素血症を伴いやすい状態にある患者［嫌気的解糖の亢進により乳酸産生が増加する。］</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>脱水症の患者又は脱水状態が懸念される患者（下痢、嘔吐等の胃腸障害のある患者、経口摂取が困難な患者等）</p><p><strong>〈次に示す患者［乳酸アシドーシスを起こしやすい。］〉</strong></p><p>過度のアルコール摂取者</p><p>重症ケトーシス、糖尿病性昏睡又は前昏睡、1型糖尿病の患者［輸液、インスリンによる速やかな高血糖の是正が必須である。］</p><p>重症感染症、手術前後、重篤な外傷のある患者［インスリン注射による血糖管理が望まれるので本剤の投与は適さない。また、乳酸アシドーシスを起こしやすい。］</p><p>栄養不良状態、飢餓状態、衰弱状態、脳下垂体機能不全又は副腎機能不全の患者［低血糖を起こすおそれがある。］</p><p>妊婦又は妊娠している可能性のある女性</p><p>本剤の成分又はビグアナイド系薬剤に対し過敏症の既往歴のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_PatientsWithRenalImpairment_20220920113045_20",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_PatientsWithHepaticImpairment_20220920113045_23",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_MalesAndFemalesOfReproductivePotential",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:3.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "3.1",
      title: "組成",
    },
    kind: "section",
    excerpt:
      "<p>1錠中日局メトホルミン塩酸塩</p><p>250mg</p><p>ポビドン、ステアリン酸マグネシウム、ヒプロメロース、マクロゴール400、マクロゴール6000、タルク</p><p>1錠中日局メトホルミン塩酸塩</p><p>500mg</p><p>ポビドン、ステアリン酸マグネシウム、ヒプロメロース、マクロゴール400、マクロゴール6000、タルク</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:3.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "3.2",
      title: "製剤の性状",
    },
    kind: "section",
    excerpt:
      "<p>割線入りのフィルムコート錠</p><p>白色～帯黄白色</p><p>［図:400093_3962002F2027_fig01.gif］</p><p>約9.1mm</p><p>約4.1mm</p><p>約271mg</p><p>DS271</p><p>割線入りのフィルムコート錠</p><p>白色～帯黄白色</p><p>［図:400093_3962002F2027_fig02.gif］</p><p>約15.8mm</p><p>約7.3mm</p><p>約5.7mm</p><p>約538mg</p><p>DS272</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:4",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "4",
      title: "効能又は効果",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈2型糖尿病〉</strong></p><p>ただし、下記のいずれかの治療で十分な効果が得られない場合に限る。<br>（1）食事療法・運動療法のみ<br>（2）食事療法・運動療法に加えてスルホニルウレア剤を使用</p><p><strong>〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉</strong></p><p>ただし、肥満、耐糖能異常、又はインスリン抵抗性のいずれかを呈する患者に限る。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:5",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "5",
      title: "効能又は効果に関連する注意",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>糖尿病を合併する多嚢胞性卵巣症候群の患者では糖尿病の治療を優先すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発〉〉</strong></p><p>ゴナドトロピン製剤を除く排卵誘発薬で十分な効果が得られない場合に本剤の併用を考慮すること。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:6",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "6",
      title: "用法及び用量",
    },
    kind: "section",
    excerpt:
      "<p>〈2型糖尿病〉<br>通常、成人にはメトホルミン塩酸塩として1日500mgより開始し、1日2～3回に分割して食直前又は食後に経口投与する。維持量は効果を観察しながら決めるが、通常1日750～1,500mgとする。なお、患者の状態により適宜増減するが、1日最高投与量は2,250mgまでとする。<br>通常、10歳以上の小児にはメトホルミン塩酸塩として1日500mgより開始し、1日2～3回に分割して食直前又は食後に経口投与する。維持量は効果を観察しながら決めるが、通常1日500～1,500mgとする。なお、患者の状態により適宜増減するが、1日最高投与量は2,000mgまでとする。</p><p>〈多嚢胞性卵巣症候群における排卵誘発〉<br>他の排卵誘発薬との併用で、通常、メトホルミン塩酸塩として500mgの1日1回経口投与より開始する。患者の忍容性を確認しながら増量し、1日投与量として1,500mgを超えない範囲で、1日2～3回に分割して経口投与する。なお、本剤は排卵までに中止する。</p><p>〈多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉</p><p>他の卵巣刺激薬との併用で、通常、メトホルミン塩酸塩として500mgの1日1回経口投与より開始する。患者の忍容性を確認しながら増量し、1日投与量として1,500mgを超えない範囲で、1日2～3回に分割して経口投与する。なお、本剤は採卵までに中止する。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:7",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "7",
      title: "用法及び用量に関連する注意",
    },
    kind: "section",
    excerpt:
      '<p>中等度の腎機能障害のある患者（eGFR 30mL/min/1.73m²以上60mL/min/1.73m²未満）では、メトホルミンの血中濃度が上昇し、乳酸アシドーシスの発現リスクが高くなる可能性があるため、以下の点に注意すること。特に、eGFRが30mL/min/1.73m²以上45mL/min/1.73m²未満の患者には、治療上の有益性が危険性を上回ると判断される場合にのみ投与すること。</p><p>投与は、少量より開始すること。</p><p>投与中は、より頻回に腎機能（eGFR等）を確認するなど慎重に経過を観察し、投与の適否及び投与量の調節を検討すること。</p><p>効果不十分な場合は、メトホルミン塩酸塩として1日最高投与量を下表の目安まで増量することができるが、効果を観察しながら徐々に増量すること。また、投与にあたっては、1日量を1日2～3回分割投与すること。</p><p>中等度の腎機能障害のある患者における1日最高投与量の目安</p><table><thead><tr><th>推算糸球体濾過量（eGFR）\n（mL/min/1.73m²）</th><th>1日最高投与量の目安</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">推算糸球体濾過量（eGFR）<br>（mL/min/1.73m²）</td><td rowspan="1" colspan="1">1日最高投与量の目安</td></tr><tr><td rowspan="1" colspan="1">45 ≦ eGFR ＜ 60</td><td rowspan="1" colspan="1">1,500mg</td></tr><tr><td rowspan="1" colspan="1">30 ≦ eGFR ＜ 45</td><td rowspan="1" colspan="1">750mg</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_PatientsWithRenalImpairment_20220920113045_21",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SpecificPopulation_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:8",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "8",
      title: "重要な基本的注意",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈効能共通〉〉</strong></p><p>まれに重篤な乳酸アシドーシスを起こすことがある。リスク因子としては、腎機能障害、肝機能障害、低酸素血症を伴いやすい状態、脱水（利尿作用を有する薬剤の併用を含む）、過度のアルコール摂取、感染症、高齢者等が知られている。特に、脱水、過度のアルコール摂取等により患者の状態が急変することもあるので、以下の点に注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>(1)本剤の投与開始前及びその後も投与中は定期的に、腎機能（eGFR等）及び肝機能を確認するとともに、患者の状態に十分注意して投与の適否及び投与量の調節を検討すること。なお、高齢者等、特に慎重な経過観察が必要な場合には、より頻回に確認すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>(2)脱水症状があらわれた場合には投与を中止し、適切な処置を行うこと。利尿作用を有する薬剤（利尿剤、SGLT2阻害剤等）との併用時には、特に脱水に注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈(3)本剤の投与開始時及びその後も投与中は適切に、以下の内容を患者及びその家族に十分指導すること。〉</strong></p><p>過度のアルコール摂取を避けること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈(3)本剤の投与開始時及びその後も投与中は適切に、以下の内容を患者及びその家族に十分指導すること。〉</strong></p><p>発熱、下痢、嘔吐、食事摂取不良等の体調不良（シックデイ）の時は、脱水状態が懸念されるため、いったん服用を中止し、医師に相談すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈(3)本剤の投与開始時及びその後も投与中は適切に、以下の内容を患者及びその家族に十分指導すること。〉</strong></p><p>乳酸アシドーシスの症状（胃腸障害、倦怠感、筋肉痛、過呼吸等）があらわれた場合には、直ちに受診すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>(4)ヨード造影剤を用いて検査を行う患者においては、本剤の併用により乳酸アシドーシスを起こすことがあるので、検査前は本剤の投与を一時的に中止すること（ただし、緊急に検査を行う必要がある場合を除く）。ヨード造影剤投与後48時間は本剤の投与を再開しないこと。なお、投与再開時には、患者の状態に注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>低血糖症状を起こすことがあるので、高所作業、自動車の運転等に従事している患者に投与するときには注意すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>本剤の使用にあたっては、患者及びその家族に対し低血糖症状及びその対処方法について十分説明すること。</p><p><strong>〈〈2型糖尿病〉〉</strong></p><p>投与する場合には、少量より開始し、血糖値、尿糖等を定期的に検査し、薬剤の効果を確かめ、本剤を3～4ヵ月投与しても効果が不十分な場合には、速やかに他の治療法への切り替えを行うこと。</p><p><strong>〈〈2型糖尿病〉〉</strong></p><p>本剤とイメグリミン塩酸塩は作用機序の一部が共通している可能性があること、また、イメグリミン塩酸塩の国内臨床試験において、ビグアナイド系薬剤と併用した場合、他の糖尿病用薬との併用療法と比較して消化器症状が多く認められたとの報告があることから、併用薬剤の選択の際には留意すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>本剤は、不妊治療に十分な知識と経験のある医師のもとで使用すること。本剤投与により予想されるリスク及び妊娠初期の本剤の服用を避けるための服用中止時期について、あらかじめ患者に説明を行うこと。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p><strong>〈患者に対しては、あらかじめ以下の点を説明すること。〉</strong></p><p>本剤との関連は明確ではないが、本剤を用いた不妊治療において、卵巣過剰刺激症候群があらわれることがあるので、自覚症状（下腹部痛、下腹部緊迫感、悪心、腰痛等）や急激な体重増加が認められた場合には直ちに医師等に相談すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p><strong>〈患者に対しては、あらかじめ以下の点を説明すること。〉</strong></p><p>多嚢胞性卵巣症候群における排卵誘発に本剤を用いた場合、卵巣過剰刺激の結果として多胎妊娠となる可能性があること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_MalesAndFemalesOfReproductivePotential",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.1",
      title: "合併症・既往歴等のある患者",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈低血糖を起こすおそれのある以下の患者又は状態〉</strong></p><p>不規則な食事摂取、食事摂取量の不足</p><p><strong>〈低血糖を起こすおそれのある以下の患者又は状態〉</strong></p><p>激しい筋肉運動</p><p>感染症<br>乳酸アシドーシスを起こすおそれがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.2",
      title: "腎機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>腎臓における排泄が減少しメトホルミンの血中濃度が上昇するため、乳酸アシドーシス等の発現リスクが高くなる可能性がある。</p><p>重度の腎機能障害のある患者（eGFR 30mL/min/1.73m²未満）又は透析患者（腹膜透析を含む）<br>投与しないこと。</p><p>中等度の腎機能障害のある患者（eGFR 30mL/min/1.73m²以上60mL/min/1.73m²未満）<br>慎重に経過を観察し、投与の適否及び投与量の調節を検討すること。特に、eGFRが30mL/min/1.73m²以上45mL/min/1.73m²未満の患者には、治療上の有益性が危険性を上回ると判断される場合にのみ投与すること。</p><p>軽度の腎機能障害のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SpecificPopulation_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.3",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.3",
      title: "肝機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>肝臓における乳酸の代謝能が低下し、乳酸アシドーシスの発現リスクが高くなる可能性がある。</p><p>重度の肝機能障害のある患者<br>投与しないこと。</p><p>軽度～中等度の肝機能障害のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "17.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_EfficacyAndSafety_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "17.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_EfficacyAndSafety_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.4",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.4",
      title: "生殖能を有する者",
    },
    kind: "section",
    excerpt:
      "<p>〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉<br>妊娠初期の投与を避けるため、以下の対応を行うこと。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>各治療周期における本剤投与開始前に妊娠していないことを確認すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>多嚢胞性卵巣症候群における排卵誘発においては、患者に、本剤投与前少なくとも1ヵ月間及び治療期間中は基礎体温を必ず記録させ、排卵の有無を確認すること。</p><p><strong>〈〈多嚢胞性卵巣症候群における排卵誘発、多嚢胞性卵巣症候群の生殖補助医療における調節卵巣刺激〉〉</strong></p><p>排卵後又は採卵後に服用を継続することがないよう、服用中止時期を患者に指示すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.5",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.5",
      title: "妊婦",
    },
    kind: "section",
    excerpt:
      "<p>妊婦又は妊娠している可能性のある女性には投与しないこと。動物実験（ラット、ウサギ）で胎児への移行が認められており、一部の動物実験（ラット）で催奇形作用が報告されている。また、妊婦は乳酸アシドーシスを起こしやすい。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_02",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_MalesAndFemalesOfReproductivePotential",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.6",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.6",
      title: "授乳婦",
    },
    kind: "section",
    excerpt:
      "<p>治療上の有益性及び母乳栄養の有益性を考慮し、授乳の継続又は中止を検討すること。動物実験（ラット）で乳汁中への移行が認められている。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.7",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.7",
      title: "小児等",
    },
    kind: "section",
    excerpt:
      "<p>低出生体重児、新生児、乳児、幼児を対象とした臨床試験は実施していない。10歳未満の小児への使用経験は限られている。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:9.8",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "9.8",
      title: "高齢者",
    },
    kind: "section",
    excerpt:
      "<p>高齢者では、腎機能、肝機能等が低下していることが多く、また脱水症状を起こしやすい。これらの状態では乳酸アシドーシスを起こしやすいので、以下の点に注意すること。</p><p>本剤の投与開始前、投与中は定期的に、特に慎重な経過観察が必要な場合にはより頻回に腎機能や肝機能を確認するなど十分に観察しながら慎重に投与すること。本剤はほとんど代謝されず、未変化体のまま尿中に排泄される。また、肝機能の低下により乳酸の代謝能が低下する。</p><p>腎機能や脱水症状等患者の状態に十分注意して投与の中止や減量を検討すること。特に75歳以上の高齢者では、本剤投与の適否をより慎重に判断すること。乳酸アシドーシスが多く報告されており、予後も不良であることが多い。国内における本剤の承認時までの臨床試験において、75歳以上の高齢者への1日1,500mgを超える用量の使用経験は限られている。</p><p>血清クレアチニン値が正常範囲内であっても、eGFR等も考慮して、慎重に患者の状態を観察すること。年齢によっては実際の腎機能が低下していることがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SpecificPopulation_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Metabolism",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Excretion",
      },
      {
        kind: "HeaderRef",
        target_section_code: "17.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_EfficacyAndSafety_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10",
      title: "相互作用",
    },
    kind: "section",
    excerpt:
      "<p>本剤はほとんど代謝されず、未変化体のまま、主にOCT2を介して尿中に排泄される。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "16.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Metabolism",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Excretion",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.1",
      title: "併用禁忌",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">アルコール（過度の摂取）</td><td rowspan="1" colspan="1">乳酸アシドーシスを起こすことがある。本剤の投与中は過度のアルコール摂取（飲酒）を避けること。</td><td rowspan="1" colspan="1">肝臓における乳酸の代謝能が低下する。また、脱水状態を来すことがある。</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "section",
    excerpt:
      '<p>10.2.1 乳酸アシドーシスを起こすことがある薬剤</p><table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">ヨード造影剤</td><td rowspan="1" colspan="1">併用により乳酸アシドーシスを起こすことがある。<br>ヨード造影剤を用いて検査を行う場合には、本剤の投与を一時的に中止すること。</td><td rowspan="1" colspan="1">腎機能が低下し、本剤の排泄が低下することが考えられている。</td></tr><tr><td rowspan="1" colspan="1">腎毒性の強い抗生物質<br>ゲンタマイシン等</td><td rowspan="1" colspan="1">併用により乳酸アシドーシスを起こすことがある。併用する場合は本剤の投与を一時的に減量・中止するなど適切な処置を行うこと。</td><td rowspan="1" colspan="1">腎機能が低下し、本剤の排泄が低下することが考えられている。</td></tr><tr><td rowspan="1" colspan="1">利尿作用を有する薬剤<br>利尿剤<br>SGLT2阻害剤 等</td><td rowspan="1" colspan="1">脱水により乳酸アシドーシスを起こすことがある。脱水症状があらわれた場合には、本剤の投与を中止し、適切な処置を行うこと。</td><td rowspan="1" colspan="1">利尿作用を有する薬剤により、体液量が減少し脱水状態になることがある。</td></tr></tbody></table><p>10.2.2 血糖降下作用を増強する薬剤</p><table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">糖尿病用薬<br>インスリン製剤<br>スルホニルウレア剤<br>速効型インスリン分泌促進薬<br>α-グルコシダーゼ阻害剤<br>チアゾリジン系薬剤<br>DPP-4阻害剤<br>GLP-1受容体作動薬<br>SGLT2阻害剤<br>イメグリミン塩酸塩 等</td><td rowspan="1" colspan="1">併用により低血糖が起こることがある。<br>スルホニルウレア剤併用時に低血糖のリスクが増加するおそれがある。<br>患者の状態を十分観察しながら投与する。</td><td rowspan="1" colspan="1">併用による血糖降下作用の増強。</td></tr><tr><td rowspan="1" colspan="1">たん白同化ホルモン剤</td><td rowspan="1" colspan="1">併用により低血糖が起こることがある。<br>スルホニルウレア剤併用時に低血糖のリスクが増加するおそれがある。<br>患者の状態を十分観察しながら投与する。</td><td rowspan="1" colspan="1">機序不明。</td></tr><tr><td rowspan="1" colspan="1">サリチル酸剤<br>アスピリン等</td><td rowspan="1" colspan="1">併用により低血糖が起こることがある。<br>スルホニルウレア剤併用時に低血糖のリスクが増加するおそれがある。<br>患者の状態を十分観察しながら投与する。</td><td rowspan="1" colspan="1">サリチル酸剤の血糖降下作用が考えられている。</td></tr><tr><td rowspan="1" colspan="1">β遮断剤<br>プロプラノロール等</td><td rowspan="1" colspan="1">併用により低血糖が起こることがある。<br>スルホニルウレア剤併用時に低血糖のリスクが増加するおそれがある。<br>患者の状態を十分観察しながら投与する。</td><td rowspan="1" colspan="1">β遮断作用によりアドレナリンを介した低血糖からの回復を遅らせることが考えられている。</td></tr><tr><td rowspan="1" colspan="1">モノアミン酸化酵素阻害剤</td><td rowspan="1" colspan="1">併用により低血糖が起こることがある。<br>スルホニルウレア剤併用時に低血糖のリスクが増加するおそれがある。<br>患者の状態を十分観察しながら投与する。</td><td rowspan="1" colspan="1">モノアミン酸化酵素阻害剤によるインスリン分泌促進、糖新生抑制が考えられている。</td></tr></tbody></table><p>10.2.3 血糖降下作用を減弱する薬剤</p><table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">アドレナリン</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">アドレナリンによる末梢での糖利用抑制、肝での糖新生促進、インスリン分泌抑制が考えられている。</td></tr><tr><td rowspan="1" colspan="1">副腎皮質ホルモン</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">副腎皮質ホルモンによる肝での糖新生促進等が考えられている。</td></tr><tr><td rowspan="1" colspan="1">甲状腺ホルモン</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">甲状腺ホルモンは糖代謝全般に作用し血糖値を変動させると考えられている。</td></tr><tr><td rowspan="1" colspan="1">卵胞ホルモン</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">卵胞ホルモンには耐糖能を変化させ、血糖を上昇させる作用が認められている。</td></tr><tr><td rowspan="1" colspan="1">利尿剤</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">利尿剤によるカリウム喪失によりインスリン分泌の低下が考えられている。</td></tr><tr><td rowspan="1" colspan="1">ピラジナミド</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">機序不明。</td></tr><tr><td rowspan="1" colspan="1">イソニアジド</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">イソニアジドによる炭水化物代謝阻害が考えられている。</td></tr><tr><td rowspan="1" colspan="1">ニコチン酸</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">ニコチン酸による血糖上昇作用が考えられている。</td></tr><tr><td rowspan="1" colspan="1">フェノチアジン系薬剤</td><td rowspan="1" colspan="1">併用により血糖降下作用が減弱することがある。<br>患者の状態を十分観察しながら投与すること。</td><td rowspan="1" colspan="1">フェノチアジン系薬剤によるインスリン分泌抑制、副腎からのアドレナリン遊離が考えられている。</td></tr></tbody></table><p>10.2.4 その他</p><table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">OCT2、MATE1、又はMATE2-Kを阻害する薬剤<br>シメチジン<br>ドルテグラビル<br>ビクテグラビル<br>バンデタニブ<br>イサブコナゾニウム硫酸塩<br>ピミテスピブ 等</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇し、作用が増強するおそれがある。観察を十分に行い、必要に応じて本剤を減量するなど慎重に投与すること。</td><td rowspan="1" colspan="1">OCT2、MATE1、又はMATE2-Kを介した本剤の腎排泄が阻害されると考えられている。</td></tr><tr><td rowspan="1" colspan="1">イメグリミン塩酸塩</td><td rowspan="1" colspan="1">消化器症状の発現に注意すること。</td><td rowspan="1" colspan="1">特に併用初期に多く発現する傾向が認められている。</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_DrugAndDrugInteractions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_DrugAndDrugInteractions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_DrugAndDrugInteractions_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_ImportantPrecautions_20220920113045_15",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:11",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "11",
      title: "副作用",
    },
    kind: "section",
    excerpt:
      "<p>次の副作用があらわれることがあるので、観察を十分に行い、異常が認められた場合には投与を中止するなど適切な処置を行うこと。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:11.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "11.1",
      title: "重大な副作用",
    },
    kind: "section",
    excerpt:
      "<p>乳酸アシドーシス（頻度不明）<br>乳酸アシドーシス（血中乳酸値の上昇、乳酸/ピルビン酸比の上昇、血液pHの低下等を示す）は予後不良のことが多い。一般的に発現する臨床症状は様々であるが、胃腸症状、倦怠感、筋肉痛、過呼吸等の症状がみられることが多く、これらの症状があらわれた場合には直ちに投与を中止し、必要な検査を行うこと。なお、乳酸アシドーシスの疑いが大きい場合には、乳酸の測定結果等を待つことなく適切な処置を行うこと。</p><p>低血糖（5%以上）<br>低血糖症状（初期症状:脱力感、高度の空腹感、発汗等）が認められた場合には糖質を含む食品を摂取するなど適切な処置を行うこと。ただし、α-グルコシダーゼ阻害剤との併用により低血糖症状が認められた場合にはブドウ糖を投与すること。</p><p>肝機能障害、黄疸（頻度不明）<br>AST、ALT、ALP、γ-GTP、ビリルビンの著しい上昇等を伴う肝機能障害、黄疸があらわれることがある。</p><p>横紋筋融解症（頻度不明）<br>筋肉痛、脱力感、CK上昇、血中及び尿中ミオグロビン上昇を特徴とする横紋筋融解症があらわれることがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPregnant",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "13.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PMDA_OverDosage_20220920113045_29",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "17.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_EfficacyAndSafety_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:11.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "11.2",
      title: "その他の副作用",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th></th><th>5%以上</th><th>1～5%未満</th><th>1%未満</th><th>頻度不明</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">消化器注¹）</td><td rowspan="1" colspan="1">下痢（40.5%）、悪心（15.4%）、食欲不振（11.8%）、腹痛（11.5%）、嘔吐</td><td rowspan="1" colspan="1">消化不良、腹部膨満感、便秘、胃炎</td><td rowspan="1" colspan="1">胃腸障害、放屁増加</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">血液</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">貧血、白血球増加、好酸球増加、白血球減少</td><td rowspan="1" colspan="1">血小板減少</td></tr><tr><td rowspan="1" colspan="1">過敏症</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">発疹、そう痒</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">肝臓</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">肝機能異常</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">腎臓</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">BUN上昇、クレアチニン上昇</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">代謝異常</td><td rowspan="1" colspan="1">乳酸上昇</td><td rowspan="1" colspan="1">CK上昇、血中カリウム上昇</td><td rowspan="1" colspan="1">血中尿酸増加</td><td rowspan="1" colspan="1">ケトーシス</td></tr><tr><td rowspan="1" colspan="1">その他</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">めまい・ふらつき</td><td rowspan="1" colspan="1">全身倦怠感注¹）、空腹感、眠気、動悸、脱力感、発汗、味覚異常、頭重、頭痛、浮腫、ビタミンB_{12}減少注²）</td><td rowspan="1" colspan="1">筋肉痛注¹）</td></tr></tbody></table><p>注1）乳酸アシドーシスの初期症状であることもあるので注意すること。<br>注2）長期使用によりビタミンB_{12}の吸収不良があらわれることがある。</p>',
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:13",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "13",
      title: "過量投与",
    },
    kind: "section",
    excerpt:
      "<p>症状<br>乳酸アシドーシスが起こることがある。</p><p>処置<br>アシドーシスの補正（炭酸水素ナトリウム静注等）、輸液（強制利尿）、血液透析等の適切な処置を行う。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:14",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "14",
      title: "適用上の注意",
    },
    kind: "section",
    excerpt:
      "<p>薬剤調製時の注意 本剤とオルメサルタン メドキソミル製剤等との一包化は避けること。一包化して高温高湿度条件下にて保存した場合、本剤が変色することがある。</p><p>薬剤交付時の注意 PTP包装の薬剤はPTPシートから取り出して服用するよう指導すること。PTPシートの誤飲により、硬い鋭角部が食道粘膜へ刺入し、更には穿孔をおこして縦隔洞炎等の重篤な合併症を併発することがある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:15.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "15.1",
      title: "臨床使用に基づく情報",
    },
    kind: "section",
    excerpt:
      "<p>インスリン又は経口血糖降下剤の投与中にアンジオテンシン変換酵素阻害剤を投与することにより、低血糖が起こりやすいとの報告がある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.1",
      title: "血中濃度",
    },
    kind: "section",
    excerpt:
      '<p>単回投与<br>健康成人男性にメトホルミン塩酸塩を空腹時に単回経口投与したときの血漿中メトホルミン濃度推移及び薬物動態パラメータは以下のとおりであった。</p><p><strong>〈単回投与〉</strong></p><p></p><p><strong>〈単回投与〉</strong></p><table><thead><tr><th>投与量</th><th>T_{max}\n（h）</th><th>C_{max}\n（ng/mL）</th><th>AUC_{0-48}\n（ng・h/mL）</th><th>T_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">投与量</td><td rowspan="1" colspan="1">T_{max}<br>（h）</td><td rowspan="1" colspan="1">C_{max}<br>（ng/mL）</td><td rowspan="1" colspan="1">AUC_{0-48}<br>（ng・h/mL）</td><td rowspan="1" colspan="1">T_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">250mg（6例）</td><td rowspan="1" colspan="1">1.9 ± 1.1</td><td rowspan="1" colspan="1">898 ± 168</td><td rowspan="1" colspan="1">4,861 ± 577</td><td rowspan="1" colspan="1">2.9 ± 0.6</td></tr><tr><td rowspan="1" colspan="1">500mg（6例）</td><td rowspan="1" colspan="1">2.3 ± 0.9</td><td rowspan="1" colspan="1">1,341 ± 329</td><td rowspan="1" colspan="1">8,019 ± 2,347</td><td rowspan="1" colspan="1">4.0 ± 1.4</td></tr><tr><td rowspan="1" colspan="1">750mg（12例）</td><td rowspan="1" colspan="1">2.1 ± 0.7</td><td rowspan="1" colspan="1">2,163 ± 517</td><td rowspan="1" colspan="1">11,802 ± 2,221</td><td rowspan="1" colspan="1">4.7 ±1.7</td></tr></tbody></table><p><strong>〈単回投与〉</strong></p><p>平均値±標準偏差</p><p>反復投与<br>健康成人男性に1日3回メトホルミン塩酸塩500mgあるいは750mg（各9例）を6日間反復経口投与したとき、血漿中メトホルミン濃度は投与2～4日後には定常状態に達し、反復投与による蓄積性はみられなかった。</p>',
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.2",
      title: "吸収",
    },
    kind: "section",
    excerpt:
      '<p>食事の影響<br>健康成人男性12例にメトホルミン塩酸塩750mgを食後に単回経口投与したとき、空腹時投与に比べてC_{max}が約20%低下したが、AUC_{0-48}及び尿中排泄率に差は認められなかった。<br>健康成人男性にメトホルミン塩酸塩500mgを食直前及び食後に単回経口投与したときの薬物動態パラメータは以下のとおりであった。</p><p><strong>〈食事の影響〉</strong></p><table><thead><tr><th>投与時期</th><th>T_{max}\n（h）</th><th>C_{max}\n（ng/mL）</th><th>AUC_{0-24}\n（ng・h/mL）</th><th>T_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">投与時期</td><td rowspan="1" colspan="1">T_{max}<br>（h）</td><td rowspan="1" colspan="1">C_{max}<br>（ng/mL）</td><td rowspan="1" colspan="1">AUC_{0-24}<br>（ng・h/mL）</td><td rowspan="1" colspan="1">T_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">食直前（12例）</td><td rowspan="1" colspan="1">1.5 ± 0.6</td><td rowspan="1" colspan="1">1,060 ± 237</td><td rowspan="1" colspan="1">6,186 ± 1,249</td><td rowspan="1" colspan="1">4.5 ± 0.8</td></tr><tr><td rowspan="1" colspan="1">食後 （12例）</td><td rowspan="1" colspan="1">3.4 ± 0.6</td><td rowspan="1" colspan="1">1,014 ± 162</td><td rowspan="1" colspan="1">6,486 ± 823</td><td rowspan="1" colspan="1">4.0 ± 0.5</td></tr></tbody></table><p><strong>〈食事の影響〉</strong></p><p>平均値±標準偏差</p><p>生物学的利用率<br>健康成人3例にメトホルミン塩酸塩500mgを単回経口投与したときの生物学的利用率は60.6%であった（外国人データ）。</p>',
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_03",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.3",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.3",
      title: "分布",
    },
    kind: "section",
    excerpt:
      "<p>血漿蛋白結合率<br>1.1～2.8%（in vitro、ヒト血漿、0.1～100µg/mL、限外ろ過法）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.4",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.4",
      title: "代謝",
    },
    kind: "section",
    excerpt:
      "<p>本剤はほとんど代謝されない。メトホルミンは、主要なCYP分子種（CYP1A2、CYP2A6、CYP2B6、CYP2C8、CYP2C9、CYP2C19、CYP2D6、CYP2E1及びCYP3A4）の代謝活性に影響を与えなかった（in vitro）。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Interactions",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.5",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.5",
      title: "排泄",
    },
    kind: "section",
    excerpt:
      "<p>本剤は未変化体のまま尿中に排泄される。健康成人5例にメトホルミン塩酸塩500mgを単回経口投与したとき、投与48時間後までの尿中排泄率は投与量の51.6%であった（外国人データ）。ヒトのトランスポーター発現細胞（hOAT1、hOAT2、hOAT3、hOAT4、hOCT1、hOCT2、hOCT3）を用いて検討した結果、hOCT2が高い輸送能を示したことから、本剤は主にOCT2を介して尿中に排泄されると考えられた。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_03",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_Interactions",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.6",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.6",
      title: "特定の背景を有する患者",
    },
    kind: "section",
    excerpt:
      '<p>腎機能障害患者<br>腎機能正常者（クレアチニンクリアランス：＞90mL/min）、軽度（クレアチニンクリアランス：61～90mL/min）及び中等度（クレアチニンクリアランス：31～60mL/min）の腎機能障害者にメトホルミン塩酸塩850mgを空腹時に単回経口投与したときの薬物動態パラメータは以下のとおりであった（外国人データ）。</p><p><strong>〈腎機能障害患者〉</strong></p><table><thead><tr><th></th><th>C_{max}\n（µg/mL）</th><th>AUC_{0-∞}\n（µg・h/mL）</th><th>T_{1/2}\n（h）</th><th>CL_{R}\n(mL/min)</th></tr></thead><tbody><tr><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">C_{max}<br>（µg/mL）</td><td rowspan="1" colspan="1">AUC_{0-∞}<br>（µg・h/mL）</td><td rowspan="1" colspan="1">T_{1/2}<br>（h）</td><td rowspan="1" colspan="1">CL_{R}<br>(mL/min)</td></tr><tr><td rowspan="1" colspan="1">腎機能正常者(3例)</td><td rowspan="1" colspan="1">1.64±0.50</td><td rowspan="1" colspan="1">11.22±3.19</td><td rowspan="1" colspan="1">11.2±5.2</td><td rowspan="1" colspan="1">394.7±83.8</td></tr><tr><td rowspan="1" colspan="1">軽度腎機能障害者(5例)</td><td rowspan="1" colspan="1">1.86±0.52</td><td rowspan="1" colspan="1">13.22±2.00</td><td rowspan="1" colspan="1">17.3±21.2</td><td rowspan="1" colspan="1">383.6±122.3</td></tr><tr><td rowspan="1" colspan="1">中等度腎機能障害者(4例)</td><td rowspan="1" colspan="1">4.12±1.83</td><td rowspan="1" colspan="1">58.30±36.58</td><td rowspan="1" colspan="1">16.2±7.6</td><td rowspan="1" colspan="1">108.3±57.2</td></tr></tbody></table><p><strong>〈腎機能障害患者〉</strong></p><p>平均値±標準偏差<br>CL_{R}：腎クリアランス</p><p>高齢者<br>健康高齢男性（65歳以上、クレアチニンクリアランス:＞60mL/min）及び健康非高齢男性（20歳以上40歳未満、クレアチニンクリアランス:＞90mL/min）にメトホルミン塩酸塩500mgを空腹時に単回投与したときの血漿中メトホルミン濃度推移及び薬物動態パラメータは以下のとおりであった。</p><p><strong>〈高齢者〉</strong></p><p></p><p><strong>〈高齢者〉</strong></p><table><thead><tr><th></th><th>T_{max}\n（h）</th><th>C_{max}\n（ng/mL）</th><th>AUC_{0-48}\n（ng・h/mL）</th><th>T_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">T_{max}<br>（h）</td><td rowspan="1" colspan="1">C_{max}<br>（ng/mL）</td><td rowspan="1" colspan="1">AUC_{0-48}<br>（ng・h/mL）</td><td rowspan="1" colspan="1">T_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">健康高齢者（12例）</td><td rowspan="1" colspan="1">2.5 ± 1.1</td><td rowspan="1" colspan="1">1,935 ± 633</td><td rowspan="1" colspan="1">14,236 ± 3,927</td><td rowspan="1" colspan="1">4.5 ± 1.0</td></tr><tr><td rowspan="1" colspan="1">健康非高齢者（6例）</td><td rowspan="1" colspan="1">2.9 ± 1.3</td><td rowspan="1" colspan="1">1,204 ± 367</td><td rowspan="1" colspan="1">8,907 ± 2,325</td><td rowspan="1" colspan="1">3.5 ± 0.6</td></tr></tbody></table><p><strong>〈高齢者〉</strong></p><p>平均値±標準偏差</p><p>小児<br>小児2型糖尿病患者を対象とした長期投与試験において、メトホルミン塩酸塩を1日2～3回に分割して、500～2,000mg/日を投与したときの血漿中濃度173点を用いて、ポピュレーションPK解析を実施した。最終モデルから得られた母集団平均パラメータ（推定値±標準誤差）は、見かけのクリアランスが69.9±3.96L/h、見かけの分布容積が525±52.1L、吸収速度定数が1.98±0.563h⁻¹であり、これらを用いて、小児2型糖尿病患者の薬物動態パラメータを推定した結果は、下表のとおりであった。</p><p><strong>〈小児〉</strong></p><p>ポピュレーションPKモデルから推定した、小児2型糖尿病患者の薬物動態パラメータ（投与条件:1日3回反復投与後）</p><p><strong>〈小児〉</strong></p><table><thead><tr><th>1回投与量</th><th>T_{max}\n（h）</th><th>C_{max}\n（ng/mL）</th><th>AUC_{0-48}\n（ng・h/mL）</th><th>T_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">1回投与量</td><td rowspan="1" colspan="1">T_{max}<br>（h）</td><td rowspan="1" colspan="1">C_{max}<br>（ng/mL）</td><td rowspan="1" colspan="1">AUC_{0-48}<br>（ng・h/mL）</td><td rowspan="1" colspan="1">T_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">250mg（36例）</td><td rowspan="1" colspan="1">1.5 ± 0.0</td><td rowspan="1" colspan="1">521 ± 119</td><td rowspan="1" colspan="1">5,095 ± 2,814</td><td rowspan="1" colspan="1">5.4 ± 1.7</td></tr><tr><td rowspan="1" colspan="1">500mg（36例）</td><td rowspan="1" colspan="1">1.5 ± 0.0</td><td rowspan="1" colspan="1">1,042 ± 237</td><td rowspan="1" colspan="1">10,191 ± 5,629</td><td rowspan="1" colspan="1">5.4 ± 1.7</td></tr></tbody></table><p><strong>〈小児〉</strong></p><p>平均値±標準偏差</p>',
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_04",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_InfoPrecautionsDosage",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithRenalImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_05",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:16.7",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "16.7",
      title: "薬物相互作用",
    },
    kind: "section",
    excerpt:
      "<p>シメチジン<br>健康成人に対し本剤とシメチジンを併用した場合、シメチジンの薬物動態には影響がみられなかったものの、メトホルミンのC_{max}が約60%上昇し、AUC_{0-24}が約40%増加した（外国人データ）。</p><p>ドルテグラビル<br>健康成人に対し本剤とドルテグラビル50mg/日及び100mg/日を併用して反復投与した場合、メトホルミンのC_{max}がそれぞれ66%及び111%上昇し、AUCがそれぞれ79%及び145%増加した（外国人データ）。</p><p>バンデタニブ<br>健康成人に対し本剤とバンデタニブを併用して単回投与した場合、メトホルミンのC_{max}及びAUC_{0-∞}がそれぞれ50%及び74%増加し、腎クリアランスが52%減少した（外国人データ）。</p><p>その他の薬剤<br>2型糖尿病患者に対し本剤とグリベンクラミドを併用した場合、グリベンクラミドのC_{max}が約37%低下し、AUC_{0-∞}が約22%減少した。健康成人に対し本剤とニフェジピンを併用した場合、メトホルミンのC_{max}が約21%上昇し、AUC_{0-24}が約16%増加した。フロセミドを併用した場合、メトホルミンのC_{max}が約22%上昇し、フロセミドのC_{max}が約31%低下し、AUC_{0-36}が約12%減少した。プロプラノロール又はイブプロフェンを併用した場合は薬物動態パラメータに影響はなかった。いずれの薬剤も併用により薬物動態に臨床的意義のある薬物相互作用はみられなかった（外国人データ）。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_06",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_07",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PrecautionsForCombinations",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:17.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "17.1",
      title: "有効性及び安全性に関する試験",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈成人〉</strong></p><p>成人2型糖尿病患者を対象とした二重盲検比較試験を含む各種臨床試験注）において、HbA1c（NGSP）値、空腹時血糖値及びグリコアルブミン値の改善が認められた。<br>注）試験対象から以下の患者を除外した。</p><p><strong>〈成人〉</strong></p><p>投与前の血清クレアチニン値が男性1.3mg/dL以上、女性1.2mg/dL以上（酵素法）の腎機能障害を有する患者</p><p><strong>〈成人〉</strong></p><p>投与前のAST又はALTが基準値上限の2.5倍以上の患者、肝硬変患者</p><p><strong>〈成人〉</strong></p><p>20歳未満又は75歳以上の患者（長期投与試験は20歳未満のみを除外した。）</p><p><strong>〈成人〉</strong></p><p>(1)国内第Ⅱ相用量反応検討試験（単独療法）<br>食事療法・運動療法で効果不十分な2型糖尿病患者に、1回250mg又は500mgを1日3回毎食後に14週間（投与開始1週間は1回250mgを1日2回）投与した結果、HbA1c（NGSP）値（平均値±標準偏差、以下同様）はそれぞれ0.67±0.64%（106例）、1.07±0.68%（106例）低下した。<br>副作用発現頻度は、750mg/日群で47.7%（51/107例）、1,500mg/日群で69.8%（74/106例）であった。主な副作用（発現頻度10%以上）は、750mg/日群で下痢30.8%（33例）、悪心15.9%（17例）、腹痛15.0%（16例）、食欲不振11.2%（12例）、1,500mg/日群で下痢48.1%（51例）、悪心22.6%（24例）、腹痛16.0%（17例）、食欲不振15.1%（16例）であった。低血糖症の副作用は認められなかった。</p><p><strong>〈成人〉</strong></p><p>(2)国内第Ⅱ相用量反応検討試験（スルホニルウレア剤併用療法）<br>食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な2型糖尿病患者に、1回250mg又は500mgを1日3回毎食後に14週間（投与開始1週間は1回250mgを1日2回）投与した結果、HbA1c（NGSP）値はそれぞれ0.74±0.68%（102例）、1.22±0.75%（103例）低下した。<br>副作用発現頻度は、750mg/日群で58.8%（60/102例）、1,500mg/日群で75.0%(78/104例)であった。主な副作用（発現頻度10%以上）は、750mg/日群で下痢26.5%（27例）、1,500mg/日群で下痢40.4%（42例）、食欲不振14.4%（15例）、悪心13.5%（14例）であった。低血糖症の副作用は、それぞれ9.8%（10例）、21.2%（22例）に発現した。</p><p><strong>〈成人〉</strong></p><p>(3)国内第Ⅱ相長期投与試験<br>食事療法・運動療法のみ又は食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な2型糖尿病患者に、1日500mgより開始し、1日750～2,250mgを2～3回に分割して54週間投与した結果、HbA1c（NGSP）値、空腹時血糖値及びグリコアルブミン値は改善し、良好な血糖コントロールが維持された。HbA1c（NGSP）値は1.30±0.78%（165例）低下した。HbA1c（NGSP）値6.9%未満の割合は、投与開始前7.3%（12/165例）に対して14週後で65.4%（100/153例）、26週後で73.5%（108/147例）、54週後で80.7%（113/140例）であった。<br>副作用発現頻度は67.5%（114/169例）であった。主な副作用（発現頻度10%以上）は、下痢54.4%（92例）、悪心15.4%（26例）、食欲不振14.8%（25例）、腹痛10.1%（17例）であった。低血糖症の副作用は食事療法・運動療法のみの患者では発現せず、食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な患者では11.6%（10/86例）に発現した。</p><p><strong>〈小児〉</strong></p><p>(1)国内第Ⅲ相長期投与試験<br>小児2型糖尿病患者を対象とした長期投与試験注）において、HbA1c（NGSP）値、グリコアルブミン値、空腹時血糖値の改善が認められた。<br>注）試験対象から以下の患者を除外した。</p><p><strong>〈小児〉</strong></p><p><strong>〈(1)国内第Ⅲ相長期投与試験〉</strong></p><p>投与前の血清クレアチニン値が1.0mg/dL（酵素法）を超える腎機能障害を有する患者</p><p><strong>〈小児〉</strong></p><p><strong>〈(1)国内第Ⅲ相長期投与試験〉</strong></p><p>投与前のAST又はALTが基準値上限の3倍以上の患者。ただし、脂肪肝を合併している場合は基準値上限の5倍未満の患者は投与可</p><p><strong>〈小児〉</strong></p><p><strong>〈(1)国内第Ⅲ相長期投与試験〉</strong></p><p>5歳以下及び18歳以上の患者</p><p><strong>〈小児〉</strong></p><p>1日500～2,000mgを2～3回に分割して24週間（可能な場合は52週間）投与した結果は以下のとおりであった（なお、組み入れられた患者の体重は44.4～112.0kgであった）。</p><p><strong>〈小児〉</strong></p><p>（1）食事療法・運動療法で効果不十分な2型糖尿病<br>HbA1c（NGSP）値（平均値±標準偏差、以下同様）は24週間投与で0.76±0.58%（14例）低下した。52週継続例では0.71±0.69%（10例）低下した。</p><p><strong>〈小児〉</strong></p><p>（2）食事療法・運動療法に加えてスルホニルウレア剤で効果不十分な2型糖尿病<br>HbA1c（NGSP）値は24週間投与で0.40±1.87%（4例）低下した。52週継続例では0.45±0.78%（2例）低下した。</p><p><strong>〈小児〉</strong></p><p>（3）食事療法・運動療法に加えて1日750mg以下のメトホルミンで効果不十分な2型糖尿病<br>HbA1c（NGSP）値は24週間投与で0.98±1.62%（17例）低下した。52週継続例では0.65±1.17%（13例）低下した。<br>副作用発現頻度は51.4 %（19/37例）であった。主な副作用（発現頻度10%以上）は、下痢29.7%（11例）、悪心18.9%（7例）、腹痛10.8%（4例）であった。低血糖症の副作用は認められなかった。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_UseInTheElderly",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_08",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_09",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_10",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_PatientsWithHepaticImpairment",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_11",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:18",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "18",
      title: "薬効薬理",
    },
    kind: "section",
    excerpt:
      "<p>血糖降下作用 肥満を呈する糖尿病モデル動物であるdb/dbマウスにおいて、血糖値の低下作用及びHbA1c値の増加抑制作用を示す。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:18.1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "18.1",
      title: "作用機序",
    },
    kind: "section",
    excerpt:
      "<p>主に肝臓における糖新生を抑制し、膵β細胞のインスリン分泌を介することなく血糖降下作用を示す。また、末梢組織における糖取り込みの促進、小腸における糖吸収の抑制等も知られている。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#DOC_12",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:19",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "19",
      title: "有効成分に関する理化学的知見",
    },
    kind: "section",
    excerpt:
      "<p>メトホルミン塩酸塩（Metformin Hydrochloride）</p><p>1,1-Dimethylbiguanide monohydrochloride</p><p>C_{4}H_{11}N_{5}・HCl</p><p>165.62</p><p>白色の結晶又は結晶性の粉末である。水に溶けやすく、酢酸（100）にやや溶けにくく、エタノール（99.5）に溶けにくい。</p><p></p><p>約221℃（分解）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:20",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "20",
      title: "取扱い上の注意",
    },
    kind: "section",
    excerpt:
      "<p>錠剤を取り出すときに特異なにおいがすることがある。（本剤の原料に由来する成分による。）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:22",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "22",
      title: "包装",
    },
    kind: "section",
    excerpt:
      "<p>〈メトグルコ錠250mg〉<br>100錠［10錠（PTP）×10］<br>1,000錠［10錠（PTP）×100］<br>500錠［瓶、バラ、乾燥剤入り］</p><p>〈メトグルコ錠500mg〉<br>100錠［10錠（PTP）×10］<br>1,000錠［10錠（PTP）×100］<br>500錠［瓶、バラ、乾燥剤入り］</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:23",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "23",
      title: "主要文献",
    },
    kind: "section",
    excerpt:
      "<p>Dubourg J., et al.: Diabetes Obes Metab.2022; 24(4): 609-619</p><p>Tuchmann-Duplessis H., et al.: Compt. Rend. 1961; 253: 321-323</p><p>Pentikainen P.J., et al.: Eur. J. Clin. Pharmacol. 1979; 16: 195-202</p><p>Sambol N.C., et al.: J.Clin.Pharmacol. 1995; 35: 1094-1102</p><p>社内資料: 小児患者を対象とした長期投与試験における母集団薬物動態解析</p><p>Song I.H., et al.: J Acquir Immune Defic Syndr. 2016; 72(4): 400-407</p><p>Johansson, S., et al.: Clin Pharmacokinet. 2014; 53: 837-847</p><p>社内資料: 用量反応検討試験（単独療法）（2010年1月20日承認、CTD2.7.6.15）</p><p>社内資料: 用量反応検討試験（SU剤併用療法）（2010年1月20日承認、CTD2.7.6.16）</p><p>社内資料: 長期投与試験（2010年1月20日承認、CTD2.7.6.18）</p><p>社内資料: 小児患者を対象とした長期投与試験</p><p>Lee, A.J.: Pharmacotherapy.1996; 16: 327-351</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:24",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "24",
      title: "文献請求先及び問い合わせ先",
    },
    kind: "section",
    excerpt:
      "<p>住友ファーマ株式会社</p><p>〒541-0045 大阪市中央区道修町2-6-8</p><p>くすり情報センター<br>TEL 0120-034-389</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:26",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "26",
      title: "製造販売業者等",
    },
    kind: "section",
    excerpt:
      "<p>製造販売元</p><p>住友ファーマ株式会社</p><p>大阪市中央区道修町2-6-8</p><p>提携</p><p>Merck Santé（フランス）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic"],
  },
];

export const realXareltoEvidence: SourceItem[] = [
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "1",
      title: "警告",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈効能共通〉〉</strong></p><p>本剤の投与により出血が発現し、重篤な出血の場合には、死亡に至るおそれがある。本剤の使用にあたっては、出血の危険性を考慮し、本剤投与の適否を慎重に判断すること。本剤による出血リスクを正確に評価できる指標は確立されていないため、本剤投与中は、血液凝固に関する検査値のみならず、出血や貧血等の徴候を十分に観察すること。これらの徴候が認められた場合には、直ちに適切な処置を行うこと。</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>脊椎・硬膜外麻酔あるいは腰椎穿刺等との併用により、穿刺部位に血腫が生じ、神経の圧迫による麻痺があらわれるおそれがある。併用する場合には神経障害の徴候及び症状について十分注意し、異常が認められた場合には直ちに適切な処置を行うこと。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>脊椎・硬膜外麻酔あるいは腰椎穿刺等との併用により、穿刺部位に血腫が生じ、神経の圧迫による麻痺があらわれるおそれがある。硬膜外カテーテル留置中、若しくは脊椎・硬膜外麻酔又は腰椎穿刺後日の浅い場合は、本剤の投与を控えること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:2",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "2",
      title: "禁忌",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈効能共通〉〉</strong></p><p>本剤の成分に対し過敏症の既往歴のある患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>出血している患者（頭蓋内出血、消化管出血等の臨床的に重大な出血）［出血を助長するおそれがある。］</p><p><strong>〈〈効能共通〉〉</strong></p><p>凝固障害を伴う肝疾患の患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>中等度以上の肝障害（Child-Pugh分類B又はCに相当）のある患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>妊婦又は妊娠している可能性のある女性</p><p><strong>〈〈効能共通〉〉</strong></p><p>リトナビルを含有する製剤、ダルナビル、ホスアンプレナビルを投与中の患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>コビシスタットを含有する製剤を投与中の患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>イトラコナゾール、ポサコナゾール、ボリコナゾール、ミコナゾール、ケトコナゾールの経口又は注射剤を投与中の患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>エンシトレルビルを投与中の患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>ロナファルニブを投与中の患者</p><p><strong>〈〈効能共通〉〉</strong></p><p>急性細菌性心内膜炎の患者［血栓はく離に伴う血栓塞栓様症状を呈するおそれがある。］</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>腎不全（eGFR15mL/min/1.73m²未満）の患者</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>重度の腎障害（eGFR30mL/min/1.73m²未満）のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithHepaticImpairment_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithHepaticImpairment_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_UseInPregnant",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithRenalImpairment_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithRenalImpairment_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithRenalImpairment_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:3.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "3.1",
      title: "組成",
    },
    kind: "section",
    excerpt:
      "<p>1錠中リバーロキサバン</p><p>2.5mg含有</p><p>結晶セルロース、クロスカルメロースナトリウム、ヒプロメロース、乳糖水和物、ステアリン酸マグネシウム、ラウリル硫酸ナトリウム、黄色三二酸化鉄、マクロゴール4000、酸化チタン</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:3.2",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "3.2",
      title: "製剤の性状",
    },
    kind: "section",
    excerpt:
      "<p>フィルムコーティング錠</p><p>淡黄色</p><p>［図:630004_3339003F5020_1_08_fig01.gif］ ［図:630004_3339003F5020_1_08_fig02.gif］ ［図:630004_3339003F5020_1_08_fig03.gif］</p><p>6mm</p><p>2.8mm</p><p>87.5mg</p><p>［図:630004_3339003F5020_1_08_fig04.gif］</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:4",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "4",
      title: "効能又は効果",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈成人〉</strong></p><p>下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制</p><p><strong>〈小児〉</strong></p><p>Fontan手術施行後における血栓・塞栓形成の抑制</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:6",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "6",
      title: "用法及び用量",
    },
    kind: "section",
    excerpt:
      "<p>〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉<br>通常、成人にはリバーロキサバンとして2.5mgを1日2回経口投与する。</p><p>〈Fontan手術施行後における血栓・塞栓形成の抑制〉<br>通常、体重20kg以上30kg未満の小児にはリバーロキサバンとして2.5mgを1日2回、体重30kg以上50kg未満の小児には7.5mgを1日1回経口投与する。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:7",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "7",
      title: "用法及び用量に関連する注意",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>アスピリン（81～100mg/日）と併用すること。なお、患者の状態に応じて本剤又はアスピリンの中断等を考慮すること。</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>下肢血行再建術施行後の初期治療において抗血小板剤2剤併用療法が必要な場合は、アスピリンとクロピドグレルを使用すること。クロピドグレルの使用期間は必要最低限にとどめること。</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>本剤の投与は、下肢血行再建術が成功し、止血が確認できた後、早期に開始すること。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>体重20kg未満の小児等に投与する場合は、リバーロキサバンドライシロップを使用すること。体重20kg以上50kg未満で本剤（錠剤）の服用が困難な小児等には、リバーロキサバンドライシロップを選択すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "17.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_EfficacyAndSafety_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:8",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "8",
      title: "重要な基本的注意",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈効能共通〉〉</strong></p><p>プロトロンビン時間国際標準比（PT-INR）は本剤の抗凝固作用について標準化された指標でなく、活性化部分トロンボプラスチン時間（aPTT）等の凝固能検査は、本剤の抗凝固作用をモニタリングする指標として推奨されない。</p><p><strong>〈〈効能共通〉〉</strong></p><p>出血等の副作用が生じることがあるので、必要に応じて血算（ヘモグロビン値）、便潜血等の検査を実施し、急激なヘモグロビン値や血圧の低下等の出血の徴候が認められた場合には、適切な処置を行うこと。</p><p><strong>〈〈効能共通〉〉</strong></p><p>患者には、鼻出血、皮下出血、歯肉出血、血尿、喀血、吐血及び血便等、異常な出血の徴候が認められた場合には、医師に連絡するよう指導すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>抗血小板剤2剤との併用時には、出血リスクが特に増大するおそれがあるため、本剤との併用についてはさらに慎重に検討し、治療上の有益性が危険性を上回ると判断された場合のみ、これらの薬剤と併用すること。下肢血行再建術施行後の末梢動脈疾患患者を対象とした国際共同第Ⅲ相試験では、シロスタゾール、プラスグレル及びチカグレロルの併用は禁止されていたため、併用時の安全性について情報はない。</p><p><strong>〈〈効能共通〉〉</strong></p><p>本剤の投与中に手術や侵襲的処置を行う場合、臨床的に可能であれば、下肢血行再建術施行後の末梢動脈疾患患者では本剤の投与後12時間以上、Fontan手術後患者では本剤の投与後24時間以上経過した後に行うことが望ましい。手術や侵襲的処置の開始を遅らせることができない場合は、緊急性と出血リスクを評価すること。本剤の投与は、手術や侵襲的処置後、患者の臨床状態に問題がなく出血がないことを確認してから、可及的速やかに再開すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈本剤と他の抗凝固剤との切り替えにおいては、以下の点に留意すること。〉</strong></p><p>ワルファリンから本剤に切り替える必要がある場合は、ワルファリンの投与を中止した後、PT-INR等、血液凝固能検査を実施し、治療域の下限以下になったことを確認した後、可及的速やかに本剤の投与を開始すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈本剤と他の抗凝固剤との切り替えにおいては、以下の点に留意すること。〉</strong></p><p>注射剤の抗凝固剤（ヘパリン等）から本剤に切り替える場合、次回の静脈内又は皮下投与が予定された時間の0～2時間前又は持続静注中止後より、本剤の投与を開始すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈本剤と他の抗凝固剤との切り替えにおいては、以下の点に留意すること。〉</strong></p><p>本剤からワルファリンへの切り替え時において抗凝固作用が不十分になる可能性が示唆されているので、抗凝固作用が維持されるよう注意し、PT-INR等、血液凝固能検査の値が治療域の下限を超えるまでは、ワルファリンと本剤を併用すること。なお、本剤の投与終了後24時間経過するまでは、PT-INRはワルファリンの抗凝固作用を正確に反映しない。</p><p><strong>〈〈効能共通〉〉</strong></p><p><strong>〈本剤と他の抗凝固剤との切り替えにおいては、以下の点に留意すること。〉</strong></p><p>本剤から注射剤の抗凝固剤に切り替える場合、本剤の投与を中止し、次回の本剤投与が予定された時間に抗凝固剤の静脈内投与又は皮下投与を開始すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>間質性肺疾患があらわれることがあるので、咳嗽、血痰、呼吸困難、発熱等の症状があらわれた場合には、速やかに主治医に連絡するよう患者に指導すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>下肢血行再建術施行後の末梢動脈疾患患者で服用を忘れた場合は、忘れた分は服用せず、次の服用時刻に再開するよう指導すること。<br>Fontan手術後患者では、1日1回投与時に服用を忘れた場合は、同日中であれば直ちに本剤を服用し、同日の服用ができない場合は、一度に2回分を服用せず、次の服用時刻に1回分を服用するよう指導すること。1日2回投与時に1回目の服用を忘れた場合は、直ちに本剤を服用するか、2回目に2回分を服用させてもよい。2回目の服用を忘れた場合は、同日であれば直ちに服用するよう指導すること。翌日からは決められた1日1回又は2回の服用を行うよう指導すること。</p><p><strong>〈〈効能共通〉〉</strong></p><p>本剤投与中の患者で生命を脅かす出血又は止血困難な出血の発現時に本剤の抗凝固作用の中和を必要とする場合には、中和剤であるアンデキサネット アルファ（遺伝子組換え）の電子添文を必ず参照し、禁忌、用法及び用量に関連する注意、重要な基本的注意、特定の背景を有する患者に関する注意、副作用等の使用上の注意の記載を確認すること。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>Fontan手術後患者においてはFontan循環に起因する多様かつ進行性の臓器障害を生じうることから、症例ごとの血栓塞栓症の発症リスク並びに出血リスクに加え、肝機能、腎機能、合併症等の患者の状態を十分に観察し、継続投与の可否を慎重に判断すること。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>小児の抗凝固薬療法に精通した医師あるいはその指導のもとで治療を行うこと。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_InfoPrecautionsDosage_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.9",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_9",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_3",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.1",
      title: "合併症・既往歴等のある患者",
    },
    kind: "section",
    excerpt:
      "<p>出血リスクが高い患者<br>以下のような患者では、出血の危険性が増大する。</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>止血障害のある患者（血小板減少症等）</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>凝固障害のある患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>先天性又は後天性の出血性疾患のある患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>コントロールできない重症の高血圧症の患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>血管性網膜症の患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>活動性悪性腫瘍の患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>活動性の潰瘍性消化管障害の患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>消化管潰瘍発症後日の浅い患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>頭蓋内出血発症後日の浅い患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>脊髄内又は脳内に血管異常のある患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>脳脊髄や眼の手術後日の浅い患者</p><p><strong>〈出血リスクが高い患者〉</strong></p><p>気管支拡張症又は肺出血の既往のある患者</p><p>低体重の患者<br>出血の危険性が増大することがある。</p><p>潰瘍性消化管障害のおそれのある患者<br>潰瘍性消化管障害に対する適切な予防に配慮すること。</p><p>脳卒中又は一過性脳虚血発作（TIA）の既往歴のある患者<br>脳卒中又はTIAの既往歴のある下肢血行再建術施行後の末梢動脈疾患患者には、本剤投与の適否を慎重に検討すること。特に、脳卒中発症後日の浅い患者や抗血小板剤2剤を併用している患者では出血リスクが増大するおそれがある。下肢血行再建術施行後の末梢動脈疾患患者を対象とした臨床試験では、当該既往歴のある患者は除外されている。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SeriousAdverseEvents_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.2",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.2",
      title: "腎機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>腎不全の患者<br>投与しないこと。下肢血行再建術施行後の末梢動脈疾患患者を対象とした国際共同第Ⅲ相試験において、eGFR15mL/min/1.73m²未満の患者は除外されている。</p><p><strong>〈重度の腎障害のある患者〉</strong></p><p>〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉<br>本剤投与の適否を慎重に検討すること。クレアチニンクリアランス15～29mL/minの患者で本剤の血中濃度が上昇することが示唆されており、出血の危険性が増大することがある。</p><p><strong>〈重度の腎障害のある患者〉</strong></p><p>〈Fontan手術施行後における血栓・塞栓形成の抑制〉<br>投与しないこと。Fontan手術後患者を対象とした臨床試験では、eGFRが30mL/min/1.73m²未満の患者は除外されている。</p><p>中等度の腎障害のある患者<br>本剤投与の適否を慎重に検討すること。成人ではクレアチニンクリアランス30～49mL/min、小児ではeGFRが30～60mL/min/1.73m²の患者で本剤の血中濃度が上昇することが示唆されており、出血の危険性が増大することがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.12",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_12",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.13",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_13",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.13",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_13",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.3",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.3",
      title: "肝機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>凝固障害を伴う肝疾患の患者<br>投与しないこと。出血の危険性が増大するおそれがある。</p><p>中等度以上の肝障害のある患者（Child-Pugh分類B又はCに相当）<br>投与しないこと。本剤の血中濃度が上昇し、出血の危険性が増大するおそれがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.6.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_2",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.5",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.5",
      title: "妊婦",
    },
    kind: "section",
    excerpt:
      "<p>妊婦又は妊娠している可能性のある女性には投与しないこと。動物実験で胎盤通過性（ラット）、子宮内出血、母動物に毒性があらわれる用量で総奇形発生率の増加（ウサギ）、死産の増加等の胚・胎児毒性、出生児の生存率低下及び一般状態の悪化（ラット）が報告されている。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_01",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_02",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_03",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_5",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.6",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.6",
      title: "授乳婦",
    },
    kind: "section",
    excerpt:
      "<p>授乳しないことが望ましい。動物実験（ラット、経口投与）で乳汁中に移行することが報告されている。ヒトの母乳中に移行することが報告されている。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_04",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.7",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.7",
      title: "小児等",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>小児等を対象とした臨床試験は実施していない。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>2歳未満及び9歳以上の小児を対象とした臨床試験は実施していない。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "16.6.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_SpecificPopulation_3",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:9.8",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "9.8",
      title: "高齢者",
    },
    kind: "section",
    excerpt:
      "<p>一般に腎機能などの生理機能が低下している。なお、非弁膜症性心房細動患者を対象とした国内第Ⅲ相試験において75歳以上の患者では75歳未満の患者と比較し、重大な出血及び重大ではないが臨床的に問題となる出血の発現率が高かった。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:10",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "10",
      title: "相互作用",
    },
    kind: "section",
    excerpt:
      "<p>本剤は主としてチトクロームP450 3A4及び2J2（CYP3A4及びCYP2J2）により代謝される。また、本剤はP-糖タンパク及び乳癌耐性タンパク（BCRP）の基質である。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "16.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Metabolism",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:10.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "10.1",
      title: "併用禁忌",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">リトナビルを含有する製剤（ノービア、カレトラ、パキロビッド）<br>ダルナビル（プリジスタ）<br>ホスアンプレナビル（レクシヴァ）</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。</td><td rowspan="1" colspan="1">CYP3A4の強力な阻害及びP-糖タンパクの阻害によりクリアランスが減少する。</td></tr><tr><td rowspan="1" colspan="1">コビシスタットを含有する製剤（ゲンボイヤ、プレジコビックス、シムツーザ）</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。</td><td rowspan="1" colspan="1">CYP3A4の強力な阻害によりクリアランスが減少する。</td></tr><tr><td rowspan="1" colspan="1">以下の経口又は注射剤<br>イトラコナゾール（イトリゾール）<br>ポサコナゾール（ノクサフィル）<br>ボリコナゾール（ブイフェンド）<br>ミコナゾール（フロリード）<br>ケトコナゾール（国内未発売）</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。</td><td rowspan="1" colspan="1">CYP3A4の強力な阻害及びP-糖タンパクの阻害によりクリアランスが減少する。</td></tr><tr><td rowspan="1" colspan="1">エンシトレルビル（ゾコーバ）</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。</td><td rowspan="1" colspan="1">CYP3A4の強力な阻害及びP-糖タンパクの阻害によりクリアランスが減少する。</td></tr><tr><td rowspan="1" colspan="1">ロナファルニブ（ゾキンヴィ）</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。</td><td rowspan="1" colspan="1">CYP3A4の強力な阻害及びP-糖タンパクの阻害によりクリアランスが減少する。</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_7",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_8",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.9",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_9",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.10",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_10",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:10.2",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">抗凝固剤<br>ヘパリン製剤、低分子量ヘパリン製剤（エノキサパリンナトリウム等）、フォンダパリヌクスナトリウム、ワルファリンカリウム等</td><td rowspan="1" colspan="1">出血の危険性が増大するおそれがあるので、観察を十分に行い、注意すること。</td><td rowspan="1" colspan="1">両剤の抗凝固作用が相加的に増強される。</td></tr><tr><td rowspan="1" colspan="1">血小板凝集抑制作用を有する薬剤<br>抗血小板剤<br>アスピリン、クロピドグレル硫酸塩、チクロピジン塩酸塩等<br>非ステロイド性解熱鎮痛消炎剤<br>ナプロキセン、ジクロフェナクナトリウム等</td><td rowspan="1" colspan="1">出血の危険性が増大するおそれがあるので、これらの薬剤と本剤の併用については、治療上の有益性と危険性を考慮して慎重に判断すること。<br>下肢血行再建術施行後の末梢動脈疾患患者では特に本剤と抗血小板剤との併用時における非ステロイド性解熱鎮痛消炎剤の長期使用については、治療上の有益性が危険性を上回ると判断された場合のみ、これらの薬剤と併用すること。<br>Fontan手術後患者では投与中は観察を十分に行い、注意すること。</td><td rowspan="1" colspan="1">本剤の抗凝固作用と血小板凝集抑制作用により相加的に出血傾向が増強される。</td></tr><tr><td rowspan="1" colspan="1">選択的セロトニン再取り込み阻害剤<br>セロトニン・ノルアドレナリン再取り込み阻害剤</td><td rowspan="1" colspan="1">出血の危険性が増大するおそれがあるので、観察を十分に行い、注意すること。</td><td rowspan="1" colspan="1">本剤の抗凝固作用と血小板凝集抑制作用により相加的に出血傾向が増強される。</td></tr><tr><td rowspan="1" colspan="1">血栓溶解剤<br>ウロキナーゼ、t-PA製剤（アルテプラーゼ等）</td><td rowspan="1" colspan="1">出血の危険性が増大するおそれがあるので、観察を十分に行い、注意すること。</td><td rowspan="1" colspan="1">本剤の抗凝固作用とフィブリン溶解作用により相加的に出血傾向が増強される。</td></tr><tr><td rowspan="1" colspan="1">フルコナゾール<br>ホスフルコナゾール</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇したとの報告がある。<br>下肢血行再建術施行後の末梢動脈疾患患者では治療上の有益性と危険性を十分に考慮し、本剤の投与が適切と判断される患者にのみ併用すること。<br>Fontan手術後患者では治療上やむを得ないと判断された場合を除き、これらの薬剤との併用を避けること。</td><td rowspan="1" colspan="1">フルコナゾールがCYP3A4を阻害することにより本剤のクリアランスが減少するおそれがある。</td></tr><tr><td rowspan="1" colspan="1">クラリスロマイシン<br>エリスロマイシン</td><td rowspan="1" colspan="1">本剤の血中濃度が上昇したとの報告がある。<br>下肢血行再建術施行後の末梢動脈疾患患者では治療上の有益性と危険性を十分に考慮し、本剤の投与が適切と判断される患者にのみ併用すること。<br>Fontan手術後患者では治療上やむを得ないと判断された場合を除き、これらの薬剤との併用を避けること。</td><td rowspan="1" colspan="1">これらの薬剤がCYP3A4及びP-糖タンパクを阻害することにより本剤のクリアランスが減少する。</td></tr><tr><td rowspan="1" colspan="1">リファンピシン</td><td rowspan="1" colspan="1">本剤の血中濃度が低下し、抗凝固作用が減弱したとの報告がある。</td><td rowspan="1" colspan="1">リファンピシンがCYP3A4を強力に誘導し、P-糖タンパクを誘導することにより本剤のクリアランスが増加する。</td></tr><tr><td rowspan="1" colspan="1">フェニトイン<br>カルバマゼピン<br>フェノバルビタール<br>セイヨウオトギリソウ（St.John&#x27;s Wort、セント・ジョーンズ・ワート）含有食品</td><td rowspan="1" colspan="1">本剤の血中濃度が低下するおそれがある。</td><td rowspan="1" colspan="1">これらの薬剤等がCYP3A4を強力に誘導することにより本剤のクリアランスが増加する。</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "16.7.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.9",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_9",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_InfoPrecautionsDosage_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_InfoPrecautionsDosage_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_7",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_8",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_4",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:11",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "11",
      title: "副作用",
    },
    kind: "section",
    excerpt:
      "<p>次の副作用があらわれることがあるので、観察を十分に行い、異常が認められた場合には投与を中止するなど適切な処置を行うこと。</p><p>注）副作用の頻度については、非弁膜症性心房細動患者を対象とした国内第Ⅲ相試験及び海外第Ⅲ相試験、静脈血栓塞栓症患者を対象とした国内第Ⅲ相試験及び海外第Ⅲ相試験、小児の静脈血栓塞栓症患者を対象とした国際共同第Ⅲ相試験、並びに小児のFontan手術後患者を対象とした国際共同第Ⅲ相試験の結果に基づき算出した。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:11.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "11.1",
      title: "重大な副作用",
    },
    kind: "section",
    excerpt:
      "<p>出血<br>頭蓋内出血（0.09%）、脳出血（0.06%）、出血性卒中（0.06%）、眼出血（0.23%）、網膜出血（0.08%）、直腸出血（1.25%）、胃腸出血（0.74%）、メレナ（0.53%）、上部消化管出血（0.36%）、下部消化管出血（0.21%）、出血性胃潰瘍（0.14%）、関節内出血（0.16%）、コンパートメント症候群を伴う筋肉内出血（0.01%）、脾破裂に至る脾臓出血（頻度不明）等の重篤な出血があらわれることがあり、死亡に至る例が報告されている。重篤な出血等の異常が認められた場合は投与を中止すること。<br>なお、出血に伴う合併症として、ショック、腎不全、呼吸困難、浮腫、頭痛、浮動性めまい、蒼白、脱力感があらわれることがある。また、一部の例では貧血の結果として胸痛又は狭心症様の心虚血症状があらわれている。</p><p>肝機能障害・黄疸<br>ALT上昇、AST上昇を伴う肝機能障害（0.1～1%未満）、黄疸（頻度不明）があらわれることがある。</p><p>間質性肺疾患（頻度不明）<br>血痰、肺胞出血を伴う場合もあるので、咳嗽、血痰、息切れ、呼吸困難、発熱、肺音の異常等が認められた場合には、速やかに胸部X線、胸部CT、血清マーカー等の検査を実施すること。間質性肺疾患が疑われた場合には投与を中止し、副腎皮質ホルモン剤の投与等を行うこと。</p><p>血小板減少（頻度不明）</p><p>急性腎障害（頻度不明）<br>経口抗凝固薬の投与後に急性腎障害があらわれることがある。経口抗凝固薬投与後の急性腎障害の中には、血尿を認めるもの、腎生検により尿細管内に赤血球円柱を多数認めるものが報告されている,。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_7",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_05",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_06",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:11.2",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "11.2",
      title: "その他の副作用",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th></th><th>1～10%未満</th><th>0.1～1%未満</th><th>0.1%未満</th><th>頻度不明</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">精神神経系</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">頭痛、浮動性めまい、不眠</td><td rowspan="1" colspan="1">失神</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">感覚器</td><td rowspan="1" colspan="1">結膜出血</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">耳出血</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">消化器</td><td rowspan="1" colspan="1">歯肉出血</td><td rowspan="1" colspan="1">肛門出血、下痢、悪心、口腔内出血、血便、腹痛、便潜血、上腹部痛、消化不良、便秘、嘔吐、吐血、口内乾燥、胃食道逆流性疾患、胃炎</td><td rowspan="1" colspan="1">痔核、アミラーゼ上昇、リパーゼ上昇</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">循環器</td><td rowspan="1" colspan="1">血腫</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">頻脈、低血圧</td><td rowspan="1" colspan="1">血管偽動脈瘤形成</td></tr><tr><td rowspan="1" colspan="1">呼吸器</td><td rowspan="1" colspan="1">鼻出血、喀血</td><td rowspan="1" colspan="1">呼吸困難</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">血液</td><td rowspan="1" colspan="1">貧血</td><td rowspan="1" colspan="1">INR増加、ヘモグロビン減少、鉄欠乏性貧血</td><td rowspan="1" colspan="1">血小板増加症（血小板数増加等）</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">肝臓</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">ALT上昇、AST上昇、血中ビリルビン上昇、Al-P上昇</td><td rowspan="1" colspan="1">γ-GTP上昇、直接ビリルビン上昇</td><td rowspan="1" colspan="1">LDH上昇</td></tr><tr><td rowspan="1" colspan="1">腎臓</td><td rowspan="1" colspan="1">血尿</td><td rowspan="1" colspan="1">尿中血陽性</td><td rowspan="1" colspan="1">尿路出血、腎クレアチニン・クリアランス減少、血中クレアチニン上昇、腎機能障害、BUN上昇</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">生殖器</td><td rowspan="1" colspan="1">月経過多</td><td rowspan="1" colspan="1">性器出血</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">筋・骨格系</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">四肢痛、関節痛</td><td rowspan="1" colspan="1">筋肉内出血</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">皮膚</td><td rowspan="1" colspan="1">斑状出血</td><td rowspan="1" colspan="1">皮下出血、皮下血腫、脱毛、皮膚裂傷</td><td rowspan="1" colspan="1">擦過傷</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">過敏症</td><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">発疹、そう痒、アレルギー性皮膚炎</td><td rowspan="1" colspan="1">じん麻疹（全身性そう痒症等）、アレルギー反応、血管浮腫</td><td rowspan="1" colspan="1"></td></tr><tr><td rowspan="1" colspan="1">その他</td><td rowspan="1" colspan="1">挫傷</td><td rowspan="1" colspan="1">創傷出血、処置後出血、無力症、末梢性浮腫、食欲減退、疲労</td><td rowspan="1" colspan="1">限局性浮腫、倦怠感、創部分泌、発熱、硬膜下血腫</td><td rowspan="1" colspan="1"></td></tr></tbody></table>',
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:13",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "13",
      title: "過量投与",
    },
    kind: "section",
    excerpt:
      "<p>症状<br>出血性合併症が生じるおそれがある。</p><p>処置<br>吸収を抑えるために活性炭投与を考慮すること。出血が認められる場合は、以下の処置を行うこと。<br>タンパク結合率が高いので、血液透析は本剤の除去には有用でないと考えられる。</p><p><strong>〈処置〉</strong></p><p>適宜、次回の投与を延期するか中止すること。消失半減期は成人で5～13時間、小児等で1～4時間である。</p><p><strong>〈処置〉</strong></p><p>症例ごとの出血の重症度及び部位に応じた出血に対する処置を講じること。</p><p><strong>〈処置〉</strong></p><p>機械的圧迫（高度の鼻出血等）、出血管理のための外科的止血、補液及び血行動態の管理、血液製剤（合併する貧血又は凝固障害に応じて濃厚赤血球輸血、新鮮凍結血漿輸注を行う）又は血小板輸血等の適切な対症療法の開始を考慮すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "16.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_BloodLevel_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_BloodLevel_2",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:14",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "14",
      title: "適用上の注意",
    },
    kind: "section",
    excerpt:
      "<p>薬剤交付時の注意 PTP包装の薬剤はPTPシートから取り出して服用するよう指導すること。PTPシートの誤飲により、硬い鋭角部が食道粘膜へ刺入し、更には穿孔をおこして縦隔洞炎等の重篤な合併症を併発することがある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:15.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "15.1",
      title: "臨床使用に基づく情報",
    },
    kind: "section",
    excerpt:
      "<p>海外において実施された3抗体（ループスアンチコアグラント、抗カルジオリピン抗体、抗β2グリコプロテインI抗体）のいずれもが陽性で、血栓症の既往がある抗リン脂質抗体症候群患者を対象とした本剤とワルファリンの非盲検無作為化試験において、血栓塞栓性イベントの再発が、ワルファリン群61例では認められなかったのに対し、本剤群では59例中7例に認められた。</p><p>適応外であるが、海外において実施された経カテーテル的大動脈弁置換術後1～7日後の患者を対象に本剤または抗血小板薬による治療を比較した試験において、抗血小板薬群に比較して本剤群で死亡及び血栓塞栓事象が多く認められたとの報告がある。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_07",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.1",
      title: "血中濃度",
    },
    kind: "section",
    excerpt:
      '<p>単回投与<br>日本人若年健康成人男子32例にリバーロキサバン5、10、20又は40mgを空腹時に単回経口投与した際、血漿中未変化体濃度は投与後0.5～4時間に最高血漿中濃度（Cmax）に達した。リバーロキサバンの1回用量の範囲において、投与量に応じた曝露量の増加が認められた。<br>外国人健康成人男子23例に本剤2.5、5及び10mgを空腹時に単回経口投与した際、血漿中未変化体濃度は投与後0.75～6時間に最高血漿中濃度（Cmax）に達した。AUCは投与量に比例して増加した。</p><p><strong>〈単回投与〉</strong></p><p></p><p><strong>〈単回投与〉</strong></p><table><thead><tr><th>投与量</th><th>AUC\n（μg・h/L）</th><th>Cmax\n（μg/L）</th><th>tmax※\n（h）</th><th>t_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">投与量</td><td rowspan="1" colspan="1">AUC<br>（μg・h/L）</td><td rowspan="1" colspan="1">Cmax<br>（μg/L）</td><td rowspan="1" colspan="1">tmax※<br>（h）</td><td rowspan="1" colspan="1">t_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">5mg</td><td rowspan="1" colspan="1">815.5（13.2）</td><td rowspan="1" colspan="1">141.3（14.5）</td><td rowspan="1" colspan="1">1.4（0.5～2.5）</td><td rowspan="1" colspan="1">5.7（19.8）</td></tr><tr><td rowspan="1" colspan="1">10mg</td><td rowspan="1" colspan="1">1564（24.5）</td><td rowspan="1" colspan="1">226.9（18.7）</td><td rowspan="1" colspan="1">1.4（0.5～4.0）</td><td rowspan="1" colspan="1">7.1（35.3）</td></tr><tr><td rowspan="1" colspan="1">20mg</td><td rowspan="1" colspan="1">2777（26.9）</td><td rowspan="1" colspan="1">341.7（29.6）</td><td rowspan="1" colspan="1">3.3（0.5～4.0）</td><td rowspan="1" colspan="1">8.9（50.1）</td></tr><tr><td rowspan="1" colspan="1">40mg</td><td rowspan="1" colspan="1">3051（21.3）</td><td rowspan="1" colspan="1">329.4（26.1）</td><td rowspan="1" colspan="1">1.4（0.5～2.0）</td><td rowspan="1" colspan="1">12.6（40.0）</td></tr></tbody></table><p><strong>〈単回投与〉</strong></p><p>※：中央値（範囲） 幾何平均値（幾何CV（%））、n=8</p><p><strong>〈単回投与〉</strong></p><table><thead><tr><th>投与量</th><th>AUC\n（μg・h/L）</th><th>Cmax\n（μg/L）</th><th>tmax※\n（h）</th><th>t_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">投与量</td><td rowspan="1" colspan="1">AUC<br>（μg・h/L）</td><td rowspan="1" colspan="1">Cmax<br>（μg/L）</td><td rowspan="1" colspan="1">tmax※<br>（h）</td><td rowspan="1" colspan="1">t_{1/2}<br>（h）</td></tr><tr><td rowspan="1" colspan="1">2.5mg</td><td rowspan="1" colspan="1">321（28.8）</td><td rowspan="1" colspan="1">52.0（28.1）</td><td rowspan="1" colspan="1">2.0（0.75～4.0）</td><td rowspan="1" colspan="1">4.99（28.8）</td></tr><tr><td rowspan="1" colspan="1">5mg</td><td rowspan="1" colspan="1">626（18.8）</td><td rowspan="1" colspan="1">90.6（24.0）</td><td rowspan="1" colspan="1">1.5（0.75～6.0）</td><td rowspan="1" colspan="1">6.79（33.4）</td></tr><tr><td rowspan="1" colspan="1">10mg</td><td rowspan="1" colspan="1">1110（25.2）</td><td rowspan="1" colspan="1">138（29.7）</td><td rowspan="1" colspan="1">2.5（1.0～4.0）</td><td rowspan="1" colspan="1">10.8（42.2）</td></tr></tbody></table><p><strong>〈単回投与〉</strong></p><p>※：中央値（範囲） 幾何平均値（幾何CV（%））、n=23</p><p>反復投与<br>日本人高齢男女36例に、リバーロキサバン10、15又は20mgを1日1回7日間食後に反復経口投与した際、初回投与時と比較し薬物動態特性に大きな変動はなく、蓄積性も認められなかった。<br>症候性深部静脈血栓症（DVT）患者及び肺塞栓症（PE）患者を対象とした国内第Ⅲ相試験の血漿中濃度を用いた母集団薬物動態解析による薬物動態パラメータ（推定値）は、以下のとおりであった。</p><p><strong>〈反復投与〉</strong></p><table><thead><tr><th>投与量</th><th>測定日</th><th>AUC(0-24)\n（μg・h/L）</th><th>Cmax\n（μg/L）</th><th>tmax※\n（h）</th><th>t_{1/2}\n（h）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">投与量</td><td rowspan="1" colspan="1">測定日</td><td rowspan="1" colspan="1">AUC(0-24)<br>（μg・h/L）</td><td rowspan="1" colspan="1">Cmax<br>（μg/L）</td><td rowspan="1" colspan="1">tmax※<br>（h）</td><td rowspan="1" colspan="1">t_{1/2}<br>（h）</td></tr><tr><td rowspan="2" colspan="1">10mg</td><td rowspan="1" colspan="1">1日目</td><td rowspan="1" colspan="1">1443（21.0）</td><td rowspan="1" colspan="1">232.6（18.7）</td><td rowspan="1" colspan="1">3.0（1.0～4.0）</td><td rowspan="1" colspan="1">5.7（18.2）</td></tr><tr><td rowspan="1" colspan="1">7日目</td><td rowspan="1" colspan="1">1533（14.9）</td><td rowspan="1" colspan="1">246.9（10.6）</td><td rowspan="1" colspan="1">3.0（1.5～4.0）</td><td rowspan="1" colspan="1">7.7（41.2）</td></tr><tr><td rowspan="2" colspan="1">15mg</td><td rowspan="1" colspan="1">1日目</td><td rowspan="1" colspan="1">2080（26.7）</td><td rowspan="1" colspan="1">347.6（23.0）</td><td rowspan="1" colspan="1">4.0（1.0～4.0）</td><td rowspan="1" colspan="1">6.3（35.1）</td></tr><tr><td rowspan="1" colspan="1">7日目</td><td rowspan="1" colspan="1">2243（21.1）</td><td rowspan="1" colspan="1">330.6（20.8）</td><td rowspan="1" colspan="1">3.5（0.5～4.0）</td><td rowspan="1" colspan="1">8.7（26.9）</td></tr><tr><td rowspan="2" colspan="1">20mg</td><td rowspan="1" colspan="1">1日目</td><td rowspan="1" colspan="1">2419（24.6）</td><td rowspan="1" colspan="1">391.2（21.2）</td><td rowspan="1" colspan="1">2.5（2.0～4.0）</td><td rowspan="1" colspan="1">6.1（20.8）</td></tr><tr><td rowspan="1" colspan="1">7日目</td><td rowspan="1" colspan="1">2839（20.9）</td><td rowspan="1" colspan="1">398.5（24.8）</td><td rowspan="1" colspan="1">3.0（1.5～4.0）</td><td rowspan="1" colspan="1">7.7（23.6）</td></tr></tbody></table><p><strong>〈反復投与〉</strong></p><p>※：中央値（範囲） 幾何平均値（幾何CV（%））、n=12</p><p><strong>〈反復投与〉</strong></p><table><thead><tr><th>用法・用量</th><th>AUC(0-24),ss※\n（μg・h/L）</th><th>Cmax,ss※\n（μg/L）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">用法・用量</td><td rowspan="1" colspan="1">AUC(0-24),ss※<br>（μg・h/L）</td><td rowspan="1" colspan="1">Cmax,ss※<br>（μg/L）</td></tr><tr><td rowspan="1" colspan="1">15mg 1日1回</td><td rowspan="1" colspan="1">2977.5（36.8）</td><td rowspan="1" colspan="1">276.9（19.8）</td></tr><tr><td rowspan="1" colspan="1">15mg 1日2回</td><td rowspan="1" colspan="1">5955.0（36.8）</td><td rowspan="1" colspan="1">363.0（26.7）</td></tr></tbody></table><p><strong>〈反復投与〉</strong></p><p>幾何平均値（幾何CV（%））<br>※：合計72例の血漿中濃度データに基づく推定値</p>',
    columns: null,
    references: [
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "13.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_OverDosage_2",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "13.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_OverDosage_2",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_08",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.2",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.2",
      title: "吸収",
    },
    kind: "section",
    excerpt:
      "<p>バイオアベイラビリティ<br>リバーロキサバン5mg及び20mgを空腹時に経口投与した際、絶対的バイオアベイラビリティはそれぞれ112%及び66%であった（外国人データ）。</p><p><strong>〈食事の影響〉</strong></p><p>リバーロキサバン20mgを食後に投与した際、AUCは空腹時投与した際と比較し39%増加した（外国人データ）。</p><p><strong>〈食事の影響〉</strong></p><p>日本人若年健康成人男子11例に、リバーロキサバン15mgを空腹時及び食後に単回経口投与した際、食後投与時にはtmaxの遅延が認められたが、AUC、Cmaxに影響は認められなかった。</p><p><strong>〈食事の影響〉</strong></p><p>健康成人男子24例にリバーロキサバン10mgを空腹時及び食後に単回経口投与した際、食後投与時にはtmaxの遅延が認められたが、AUC、Cmaxに影響は認められなかった（外国人データ）。</p>",
    columns: null,
    references: [
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.3",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.3",
      title: "分布",
    },
    kind: "section",
    excerpt:
      "<p>分布容積<br>リバーロキサバンを静脈内投与した際、分布容積（Vss）は約50Lであった（外国人データ）。</p><p>タンパク結合率<br>In vitro試験において、リバーロキサバンは血漿タンパクと高い結合能を示し、ヒト血漿タンパク結合率は約92～95%であった。主にアルブミンに結合する。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.4",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.4",
      title: "代謝",
    },
    kind: "section",
    excerpt:
      "<p>リバーロキサバンは主にCYP3A4及びCYP2J2による代謝経路により代謝され、主要な代謝物はモルホリノン環の酸化分解体及びアミド結合の加水分解体である。In vitro試験において、リバーロキサバンが輸送タンパクであるP-糖タンパク（P-gp）及び乳癌耐性タンパク（BCRP）の基質であることが示されている。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "10",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_Interactions",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.5",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.5",
      title: "排泄",
    },
    kind: "section",
    excerpt:
      "<p>リバーロキサバンを静脈内投与した際、全身クリアランスは約10L/hであり、投与量の42%が未変化体のまま腎排泄された。健康成人男子4例に［¹⁴C］リバーロキサバン10mgを単回経口投与した際、投与量の約2/3は不活性代謝物として尿中及び糞中に排泄され、残りの約1/3が未変化体のまま腎排泄された（外国人データ）。</p>",
    columns: null,
    references: [
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.6",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.6",
      title: "特定の背景を有する患者",
    },
    kind: "section",
    excerpt:
      '<p>腎障害患者<br>軽度（クレアチニンクリアランス（CLcr）：50～79mL/min）、中等度（CLcr：30～49mL/min）及び重度（CLcr：15～29mL/min）の腎障害のある患者各8例にリバーロキサバン10mgを空腹時単回経口投与した場合、健康被験者と比較しAUCはそれぞれ1.4、1.5及び1.6倍に上昇した。第Ⅹa因子活性阻害率は1.5、1.9及び2.0倍に増加し、プロトロンビン時間（PT（秒））も1.3、2.2及び2.4倍延長した。CLcrが15mL/min未満の患者における検討は実施していない（外国人データ）。</p><p>肝障害患者<br>軽度の肝障害のある肝硬変患者（Child-Pugh分類A 8例）では、リバーロキサバン10mgを投与した際の薬物動態は健康被験者と比較してほぼ同様であり（AUCは1.2倍上昇）、薬力学的効果に差は認められなかった。中等度の肝障害のある肝硬変患者（Child-Pugh分類B 8例）では健康被験者と比較してAUCが2.3倍上昇した。なお、非結合型のAUCは2.6倍上昇した。第Ⅹa因子活性阻害率は2.6倍増加し、PT（秒）も2.1倍延長した。Child-Pugh分類Cの患者における検討は実施していない（外国人データ）。</p><p><strong>〈小児〉</strong></p><p>〈Fontan手術施行後における血栓・塞栓形成の抑制〉<br>Fontan手術後の機能的単心室症患者（2～8歳）を対象とした国際共同第Ⅲ相試験の血漿中濃度を用いた母集団薬物動態解析による曝露量（推定値）は、以下のとおりであった。国際共同第Ⅲ相試験では、非日本人成人にリバーロキサバン10mgを1日1回投与時の曝露量に相当するよう体重で調整した用法・用量※でドライシロップを投与した。<br>体重30kg以上の小児のFontan手術後の機能的単心室症患者（9歳以上）にリバーロキサバンを承認用法・用量で投与した場合の曝露量を、Fontan手術後の機能的単心室症患者（2～8歳）を対象とした国際共同第Ⅲ相試験（パートA）及び小児の急性VTE患者（18歳未満）を対象とした臨床試験の血漿中濃度を用いて構築した母集団薬物動態モデルに基づくシミュレーションにより予測した。その結果、承認用法・用量で投与した場合の曝露量は非日本人成人にリバーロキサバン10mgを1日1回投与したときと同程度であった。</p><p><strong>〈小児〉</strong></p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><table><thead><tr><th>n</th><th>AUC(0-24),ss\n（μg・h/L）</th><th>Cmax,ss\n（μg/L）</th><th>Ctrough,ss\n（μg/L）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">n</td><td rowspan="1" colspan="1">AUC(0-24),ss<br>（μg・h/L）</td><td rowspan="1" colspan="1">Cmax,ss<br>（μg/L）</td><td rowspan="1" colspan="1">Ctrough,ss<br>（μg/L）</td></tr><tr><td rowspan="1" colspan="1">76</td><td rowspan="1" colspan="1">1440（484.2～4444）</td><td rowspan="1" colspan="1">109.0（39.7～287.1）</td><td rowspan="1" colspan="1">22.8（6.4～104.7）</td></tr></tbody></table><p><strong>〈小児〉</strong></p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>幾何平均値（範囲）<br>※：Fontan手術施行後における血栓・塞栓形成の抑制で承認された用法・用量と同一</p>',
    columns: null,
    references: [
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.12",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_12",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.13",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_13",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithRenalImpairment_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithRenalImpairment_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithRenalImpairment_3",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PatientsWithHepaticImpairment_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PediatricUse_2",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:16.7",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "16.7",
      title: "薬物相互作用",
    },
    kind: "section",
    excerpt:
      "<p>リトナビル<br>健康成人男子12例にリトナビル600mgとリバーロキサバン10mgを併用投与した際、リバーロキサバンのAUCは2.5倍、Cmaxは1.6倍上昇し抗凝固作用が増強された（外国人データ）。</p><p>ケトコナゾール・フルコナゾール<br>健康成人男子20例にケトコナゾール400mgとリバーロキサバン10mgを併用投与した際、リバーロキサバンのAUCは2.6倍、Cmaxは1.7倍上昇し抗凝固作用が増強された（外国人データ）。<br>健康成人男子13例にフルコナゾール400mgとリバーロキサバン20mgを併用投与した際、リバーロキサバンのAUCは1.4倍、Cmaxは1.3倍上昇した（外国人データ）。</p><p>クラリスロマイシン・エリスロマイシン<br>健康成人男子15例にクラリスロマイシン500mgとリバーロキサバン10mgを併用投与した際、リバーロキサバンのAUCは1.5倍、Cmaxは1.4倍上昇した（外国人データ）。<br>健康成人男子15例にエリスロマイシン500mgとリバーロキサバン10mgを併用投与した際、リバーロキサバンのAUC及びCmaxともに1.3倍上昇した（外国人データ）。</p><p>リファンピシン<br>健康成人男子18例にリファンピシン（開始用量150mgより600mgまで漸増）とリバーロキサバン20mgを併用投与した際、リバーロキサバンのAUCが約50%低下し、それに伴い抗凝固作用も減弱した（外国人データ）。</p><p>エノキサパリン<br>健康成人男子10例にエノキサパリン4000IUとリバーロキサバン10mgを併用投与した際、リバーロキサバンの薬物動態に影響はなかった。抗第Ⅹa因子活性は相加的に増加したが、PT及びaPTTには影響は認められなかった（外国人データ）。</p><p>アスピリン<br>健康成人男子13例にアスピリン500mgを投与した翌日にアスピリン100mgとリバーロキサバン15mgを併用投与した際、リバーロキサバンの薬物動態及び抗凝固作用に影響は認められなかった（外国人データ）。</p><p>クロピドグレル<br>健康成人男子11例にクロピドグレル300mgを投与した翌日にクロピドグレル75mgとリバーロキサバン15mgを併用投与した際、リバーロキサバンの薬物動態に影響は認められなかった。別の試験において一部の被験者に出血時間の延長が認められたとの報告がある（外国人データ）。</p><p>ナプロキセン<br>健康成人男子11例にナプロキセン500mg1日1回反復投与時にリバーロキサバン15mgを併用投与した際、出血時間の延長は認められなかったが、一部の被験者において抗凝固作用の増強が認められた（外国人データ）。</p><p>ワルファリン<br>日本人健康成人男子12例（VKORC1遺伝子1639位のAアレルがホモ接合体を有している被験者）にワルファリンを反復投与し、PT-INRが2.0～3.0に到達した後に、リバーロキサバン15mgを1日1回反復投与に切り替えた際、aPTT、第Ⅹa因子活性阻害及び内在性トロンビン産生能（ETP）への影響は相加的であったが、PT及びPT-INRのピーク値はリバーロキサバン単独投与時と比較しそれぞれ2.3倍及び2.9倍になった。リバーロキサバン投与開始後3日目には、ワルファリンの影響は消失した。なお、薬物動態に相互作用は認められなかった。</p><p>その他の薬剤<br>ミダゾラム、ジゴキシン及びアトルバスタチンとリバーロキサバンの併用による薬物相互作用試験を実施したが、薬物動態学的相互作用は認められず、制酸剤（水酸化アルミニウムゲル・水酸化マグネシウム配合剤）、ラニチジン及びオメプラゾールは、リバーロキサバンの薬物動態に影響を及ぼさなかった（外国人データ）。</p><p>本剤の「下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制」の承認用法・用量は、2.5mg1日2回投与である。</p>",
    columns: null,
    references: [
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_8",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndicatedCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
      {
        kind: "CommentRef",
        target_section_code: "16.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_01",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ImportantPrecautions_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_PrecautionsForCombinations",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:17.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "17.1",
      title: "有効性及び安全性に関する試験",
    },
    kind: "section",
    excerpt:
      '<p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p>国際共同第Ⅲ相試験<br>下肢血行再建術施行後の症候性末梢動脈疾患患者6564例（ITT解析対象集団。日本人459例を含む）を対象とし、本剤又はプラセボ（2.5mg1日2回）とアスピリン（100mg1日1回）との併用（以下、本剤群又はプラセボ群）の有効性及び安全性を比較検討する多施設共同、無作為化、二重盲検、プラセボ対照、並行群間比較試験〔試験17454（VOYAGER試験）〕を実施した。<br>被験者は下肢血行再建術（外科的、又はハイブリッド型を含む血管内）が成功し、止血確認後に本剤群又はプラセボ群のいずれかに割付けられ、術後10日以内に投与が開始された。下肢血行再建術施行後の初期治療において抗血小板剤2剤併用療法が必要な場合は、アスピリンとクロピドグレルを使用することとされ、クロピドグレルは血行再建術後最長30日間（治験担当医師が必要と判断した場合は最長6ヵ月間）使用可能とされた。下肢血行再建術から平均5.2日後に治験薬の投与が開始され、平均投与期間は本剤群730.7日、プラセボ群745.7日であった。有効性主要評価項目は心筋梗塞、虚血性脳卒中、心血管死、急性肢虚血又は血管系の原因による大切断の複合エンドポイントであり、プラセボ群に対する本剤群の優越性が検証された（片側p=0.0043）。有効性主要評価項目及びその構成要素、並びに全死亡の発現数、発現率、プラセボ群に対する本剤群のハザード比は下表のとおりであった。<br>日本人集団においては、下肢血行再建術から平均4.7日後に治験薬の投与が開始され、平均投与期間は本剤群748.5日、プラセボ群771.8日であった。有効性主要評価項目及びその構成要素、並びに全死亡の発現数、発現率、プラセボ群に対する本剤群のハザード比は下表のとおりであった。<br>安全性に関しては、以下の成績が得られた。<br>日本人集団の安全性成績は下表のとおりであった。<br>副作用は3256例中119例（3.7%）に認められ、主な副作用は、貧血16例（0.5%）、発疹8例（0.2%）、下痢7例（0.2%）等であった。<br>日本人集団における副作用は229例中10例（4.4%）に認められ、主な副作用は貧血3例（1.3%）等であった。<br>なお、本試験では、対象を絞った有害事象の収集を行い、非重篤な有害事象については、「治験薬投与中止に至った非重篤な有害事象」、「治験医師が特に懸念があると判断した非重篤な有害事象」のみを収集した。また、出血事象については、安全性評価項目として症例報告書には記録したが、有害事象としては収集しなかった。</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><table><thead><tr><th></th><th>エンドポイント</th><th>本剤群\n（N=3286）\nn（/100患者年）</th><th>プラセボ群\n（N=3278）\nn（/100患者年）</th><th>ハザード比\n（95%信頼区間）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">エンドポイント</td><td rowspan="1" colspan="1">本剤群<br>（N=3286）<br>n（/100患者年）</td><td rowspan="1" colspan="1">プラセボ群<br>（N=3278）<br>n（/100患者年）</td><td rowspan="1" colspan="1">ハザード比<br>（95%信頼区間）</td></tr><tr><td rowspan="7" colspan="1">全体集団</td><td rowspan="1" colspan="1">有効性主要評価項目※</td><td rowspan="1" colspan="1">508（6.81）</td><td rowspan="1" colspan="1">584（8.01）</td><td rowspan="1" colspan="1">0.85<br>（0.76～0.96）</td></tr><tr><td rowspan="1" colspan="1">心筋梗塞</td><td rowspan="1" colspan="1">131（1.68）</td><td rowspan="1" colspan="1">148（1.90）</td><td rowspan="1" colspan="1">0.88<br>（0.70～1.12）</td></tr><tr><td rowspan="1" colspan="1">虚血性脳卒中</td><td rowspan="1" colspan="1">71（0.90）</td><td rowspan="1" colspan="1">82（1.04）</td><td rowspan="1" colspan="1">0.87<br>（0.63～1.19）</td></tr><tr><td rowspan="1" colspan="1">心血管死</td><td rowspan="1" colspan="1">199（2.47）</td><td rowspan="1" colspan="1">174（2.15）</td><td rowspan="1" colspan="1">1.14<br>（0.93～1.40）</td></tr><tr><td rowspan="1" colspan="1">急性肢虚血</td><td rowspan="1" colspan="1">155（2.01）</td><td rowspan="1" colspan="1">227（3.01）</td><td rowspan="1" colspan="1">0.67<br>（0.55～0.82）</td></tr><tr><td rowspan="1" colspan="1">血管系の原因による大切断</td><td rowspan="1" colspan="1">103（1.32）</td><td rowspan="1" colspan="1">115（1.48）</td><td rowspan="1" colspan="1">0.89<br>（0.68～1.16）</td></tr><tr><td rowspan="1" colspan="1">全死亡</td><td rowspan="1" colspan="1">321（3.98）</td><td rowspan="1" colspan="1">297（3.68）</td><td rowspan="1" colspan="1">1.08<br>（0.92～1.27）</td></tr></tbody></table><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>（ITT解析対象集団、無作為割付けから有効性の主解析のカットオフ日）<br>※：心筋梗塞、虚血性脳卒中、心血管死、急性肢虚血、又は血管系の原因による大切断の複合エンドポイント</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><table><thead><tr><th></th><th>エンドポイント</th><th>本剤群\n（N=230）\nn（/100患者年）</th><th>プラセボ群\n（N=229）\nn（/100患者年）</th><th>ハザード比\n（95%信頼区間）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">エンドポイント</td><td rowspan="1" colspan="1">本剤群<br>（N=230）<br>n（/100患者年）</td><td rowspan="1" colspan="1">プラセボ群<br>（N=229）<br>n（/100患者年）</td><td rowspan="1" colspan="1">ハザード比<br>（95%信頼区間）</td></tr><tr><td rowspan="7" colspan="1">日本人集団</td><td rowspan="1" colspan="1">有効性主要評価項目※</td><td rowspan="1" colspan="1">23（4.35）</td><td rowspan="1" colspan="1">31（6.00）</td><td rowspan="1" colspan="1">0.72<br>（0.42～1.24）</td></tr><tr><td rowspan="1" colspan="1">心筋梗塞</td><td rowspan="1" colspan="1">5（0.91）</td><td rowspan="1" colspan="1">9（1.67）</td><td rowspan="1" colspan="1">0.54<br>（0.18～1.62）</td></tr><tr><td rowspan="1" colspan="1">虚血性脳卒中</td><td rowspan="1" colspan="1">8（1.46）</td><td rowspan="1" colspan="1">8（1.49）</td><td rowspan="1" colspan="1">0.98<br>（0.37～2.60）</td></tr><tr><td rowspan="1" colspan="1">心血管死</td><td rowspan="1" colspan="1">4（0.71）</td><td rowspan="1" colspan="1">8（1.46）</td><td rowspan="1" colspan="1">0.46<br>（0.14～1.52）</td></tr><tr><td rowspan="1" colspan="1">急性肢虚血</td><td rowspan="1" colspan="1">5（0.90）</td><td rowspan="1" colspan="1">11（2.09）</td><td rowspan="1" colspan="1">0.44<br>（0.15～1.27）</td></tr><tr><td rowspan="1" colspan="1">血管系の原因による大切断</td><td rowspan="1" colspan="1">2（0.36）</td><td rowspan="1" colspan="1">3（0.56）</td><td rowspan="1" colspan="1">0.66<br>（0.11～3.97）</td></tr><tr><td rowspan="1" colspan="1">全死亡</td><td rowspan="1" colspan="1">14（2.50）</td><td rowspan="1" colspan="1">22（4.02）</td><td rowspan="1" colspan="1">0.61<br>（0.31～1.18）</td></tr></tbody></table><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>（ITT解析対象集団、無作為割付けから有効性の主解析のカットオフ日）<br>※：心筋梗塞、虚血性脳卒中、心血管死、急性肢虚血、又は血管系の原因による大切断の複合エンドポイント</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><table><thead><tr><th></th><th>エンドポイント※¹</th><th>本剤群\n（N=3256）\nn（/100患者年）</th><th>プラセボ群\n（N=3248）\nn（/100患者年）</th><th>ハザード比\n（95%信頼区間）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">エンドポイント※¹</td><td rowspan="1" colspan="1">本剤群<br>（N=3256）<br>n（/100患者年）</td><td rowspan="1" colspan="1">プラセボ群<br>（N=3248）<br>n（/100患者年）</td><td rowspan="1" colspan="1">ハザード比<br>（95%信頼区間）</td></tr><tr><td rowspan="6" colspan="1">全体集団</td><td rowspan="1" colspan="1">安全性主要評価項目※²</td><td rowspan="1" colspan="1">62（0.96）</td><td rowspan="1" colspan="1">44（0.67）</td><td rowspan="1" colspan="1">1.43<br>（0.97～2.10）</td></tr><tr><td rowspan="1" colspan="1">冠動脈バイパス術と関連のない出血</td><td rowspan="1" colspan="1">62（0.96）</td><td rowspan="1" colspan="1">43（0.65）</td><td rowspan="1" colspan="1">1.46<br>（0.99～2.16）</td></tr><tr><td rowspan="1" colspan="1">致死的出血</td><td rowspan="1" colspan="1">6（0.09）</td><td rowspan="1" colspan="1">6（0.09）</td><td rowspan="1" colspan="1">1.02<br>（0.33～3.15）</td></tr><tr><td rowspan="1" colspan="1">頭蓋内出血</td><td rowspan="1" colspan="1">13（0.20）</td><td rowspan="1" colspan="1">17（0.26）</td><td rowspan="1" colspan="1">0.78<br>（0.38～1.61）</td></tr><tr><td rowspan="1" colspan="1">臨床的に明らかな出血の徴候※³</td><td rowspan="1" colspan="1">46（0.71）</td><td rowspan="1" colspan="1">24（0.36）</td><td rowspan="1" colspan="1">1.94<br>（1.18～3.17）</td></tr><tr><td rowspan="1" colspan="1">冠動脈バイパス術と関連のある出血</td><td rowspan="1" colspan="1">0（0）</td><td rowspan="1" colspan="1">1※⁴（0.02）</td><td rowspan="1" colspan="1">-</td></tr></tbody></table><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>（安全性解析対象集団、治験薬投与下）<br>※1：TIMI分類に基づく<br>※2：TIMI分類の「大出血」<br>※3：5g/dL以上のヘモグロビン値の低下、ヘモグロビン値が得られていない場合は15%以上のヘマトクリット値の低下<br>※4：48時間以内に実施した5単位以上の全血又は赤血球の輸血</p><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><table><thead><tr><th></th><th>エンドポイント※¹</th><th>本剤群\n（N=229）\nn（/100患者年）</th><th>プラセボ群\n（N=229）\nn（/100患者年）</th><th>ハザード比\n（95%信頼区間）</th></tr></thead><tbody><tr><td rowspan="1" colspan="1"></td><td rowspan="1" colspan="1">エンドポイント※¹</td><td rowspan="1" colspan="1">本剤群<br>（N=229）<br>n（/100患者年）</td><td rowspan="1" colspan="1">プラセボ群<br>（N=229）<br>n（/100患者年）</td><td rowspan="1" colspan="1">ハザード比<br>（95%信頼区間）</td></tr><tr><td rowspan="6" colspan="1">日本人集団</td><td rowspan="1" colspan="1">安全性主要評価項目※²</td><td rowspan="1" colspan="1">8（1.72）</td><td rowspan="1" colspan="1">7（1.46）</td><td rowspan="1" colspan="1">1.17<br>（0.43～3.24）</td></tr><tr><td rowspan="1" colspan="1">冠動脈バイパス術と関連のない出血</td><td rowspan="1" colspan="1">8（1.72）</td><td rowspan="1" colspan="1">7（1.46）</td><td rowspan="1" colspan="1">1.17<br>（0.43～3.24）</td></tr><tr><td rowspan="1" colspan="1">致死的出血</td><td rowspan="1" colspan="1">1（0.21）</td><td rowspan="1" colspan="1">1（0.21）</td><td rowspan="1" colspan="1">1.01<br>（0.06～16.23）</td></tr><tr><td rowspan="1" colspan="1">頭蓋内出血</td><td rowspan="1" colspan="1">1（0.21）</td><td rowspan="1" colspan="1">5（1.04）</td><td rowspan="1" colspan="1">0.21<br>（0.02～1.77）</td></tr><tr><td rowspan="1" colspan="1">臨床的に明らかな出血の徴候※³</td><td rowspan="1" colspan="1">7（1.51）</td><td rowspan="1" colspan="1">2（0.41）</td><td rowspan="1" colspan="1">3.57<br>（0.74～17.17）</td></tr><tr><td rowspan="1" colspan="1">冠動脈バイパス術と関連のある出血</td><td rowspan="1" colspan="1">0（0）</td><td rowspan="1" colspan="1">0（0）</td><td rowspan="1" colspan="1">-</td></tr></tbody></table><p><strong>〈〈下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>（安全性解析対象集団、治験薬投与下）<br>※1：TIMI分類に基づく<br>※2：TIMI分類の「大出血」<br>※3：5g/dL以上のヘモグロビン値の低下、ヘモグロビン値が得られていない場合は15%以上のヘマトクリット値の低下</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p>国際共同第Ⅲ相試験<br>小児のFontan手術後4ヵ月以内の機能的単心室症患者（2～8歳）を対象に、本剤の薬物動態、薬力学、安全性及び有効性を検討する多施設共同試験（UNIVERSE試験）※¹を実施した。<br>小児のFontan手術後の機能的単心室症患者110例（安全性解析対象例数）に対して、本剤群では非日本人成人に本剤10mgを1日1回投与時の曝露量に相当するよう体重で調整された用法・用量（小児のFontan手術後患者に対する承認用法・用量のうち、体重30kg未満の区分）が投与され、対照群ではアセチルサリチル酸（ASA）約5mg/kgを1日1回投与した※²。いずれの群も投与期間は12ヵ月間とし、体重増加による用量調整は第6ヵ月時点で実施した。平均投与期間は、本剤群331.8日、対照群336.4日であった。有効性評価項目及び出血事象等は盲検下で評価された。<br>有効性主要評価項目の発現頻度（パートB、治験薬投与終了までの期間）は、本剤群1.6%、対照群8.8%であった（最大の解析対象集団）。<br>安全性主要評価項目である「重大な出血」の発現頻度（パートB、治験薬投与下）は本剤群1.6%、対照群0%であった。本剤群で認められた「重大な出血」は鼻出血であった。<br>副作用（臨床検査値異常を含む）は、本剤が投与された小児のFontan手術後の機能的単心室症患者76例中23例（30.3%）に認められた。主な副作用は、斑状出血6例（7.9%）、鼻出血3例（3.9%）、血腫3例（3.9%）であった。<br>本試験では、日本人小児のFontan手術後の機能的単心室症患者9例（本剤群8例、対照群1例）が投与を受けた。本剤群、対照群ともにあらゆる血栓性イベント（静脈又は動脈）の発現は認められなかった。「重大な出血」は、本剤群1例（輸血を要する鼻出血）で認められた。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>※1：本試験はパートA及びパートBから構成され、薬物動態及び薬力学を評価するパートAでは非盲検、非対照とし、安全性及び有効性を評価するパートBでは無作為化、非盲検、実薬対照とした。<br>※2：本剤群の76例（パートA12例、パートB64例）中61例、対照群の34例中29例が前治療として抗血小板薬又は抗凝固薬の投与を受けていた。前治療の内訳は、ASAが本剤群48例及び対照群23例、ヘパリンが本剤群18例及び対照群6例、ワルファリンが本剤群11例及び対照群5例であった。</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><table><thead><tr><th>エンドポイント</th><th>リバーロキサバン\n（N=64）</th><th>対照薬\n（N=34）</th></tr></thead><tbody><tr><td rowspan="2" colspan="1">エンドポイント</td><td rowspan="1" colspan="2">リバーロキサバン<br>（N=64）</td><td rowspan="1" colspan="2">対照薬<br>（N=34）</td></tr><tr><td rowspan="1" colspan="1">n（%）</td><td rowspan="1" colspan="1">95%CI（%）</td><td rowspan="1" colspan="1">n（%）</td><td rowspan="1" colspan="1">95%CI（%）</td></tr><tr><td rowspan="1" colspan="1">有効性主要評価項目※¹</td><td rowspan="1" colspan="1">1（1.6）</td><td rowspan="1" colspan="1">NA</td><td rowspan="1" colspan="1">3（8.8）</td><td rowspan="1" colspan="1">0.0-19.8</td></tr></tbody></table><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>NA：0例又は1例の場合CIは算出せず（最大の解析対象集団、パートB、治験薬投与終了までの期間※²）<br>※1：あらゆる血栓性イベント（静脈又は動脈）<br>※2：治験薬の初回投与から最終来院（すなわち、最終有効性評価日；第12ヵ月又は中止時来院）まで</p><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><table><thead><tr><th>エンドポイント</th><th>リバーロキサバン\n（N=64）</th><th>対照薬\n（N=34）</th></tr></thead><tbody><tr><td rowspan="2" colspan="1">エンドポイント</td><td rowspan="1" colspan="2">リバーロキサバン<br>（N=64）</td><td rowspan="1" colspan="2">対照薬<br>（N=34）</td></tr><tr><td rowspan="1" colspan="1">n（%）</td><td rowspan="1" colspan="1">95%CI（%）</td><td rowspan="1" colspan="1">n（%）</td><td rowspan="1" colspan="1">95%CI（%）</td></tr><tr><td rowspan="1" colspan="1">重大な出血※¹</td><td rowspan="1" colspan="1">1※²（1.6）</td><td rowspan="1" colspan="1">NA</td><td rowspan="1" colspan="1">0</td><td rowspan="1" colspan="1">NA</td></tr><tr><td rowspan="1" colspan="1">重大ではないが臨床的に問題となる出血</td><td rowspan="1" colspan="1">4（6.3）</td><td rowspan="1" colspan="1">0.0-13.0</td><td rowspan="1" colspan="1">3（8.8）</td><td rowspan="1" colspan="1">0.0-19.8</td></tr></tbody></table><p><strong>〈〈Fontan手術施行後における血栓・塞栓形成の抑制〉〉</strong></p><p><strong>〈国際共同第Ⅲ相試験〉</strong></p><p>NA：0例又は1例の場合CIは算出せず（安全性解析対象集団、パートB、治験薬投与下）<br>※1：安全性主要評価項目<br>※2：成人において濃厚赤血球又は全血2単位以上に相当する量の輸血</p><p>ドライシロップ</p>',
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_09",
      },
      {
        kind: "CommentRef",
        target_section_code: "17.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#TBLFN_02",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_13",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:18",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "18",
      title: "薬効薬理",
    },
    kind: "section",
    excerpt:
      "<p>抗血栓効果 本剤は、マウス、ラット又はウサギの静脈及び動脈血栓症モデルにおいて、用量依存的に血栓形成を抑制した。また、ウサギ静脈血栓症モデルにおいて、血栓形成後の血栓の増大を抑制した,,。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_10",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_11",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_12",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:18.1",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "18.1",
      title: "作用機序",
    },
    kind: "section",
    excerpt:
      "<p>本剤は、選択的かつ直接的第Ⅹa因子阻害剤であり、経口投与で効果を示す。内因系及び外因系血液凝固カスケード中の第Ⅹa因子を本剤が阻害することで、トロンビン産生及び血栓形成が抑制される。本剤はトロンビンを阻害せず、また血小板に対する直接作用を有さない。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#DOC_10",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:19",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "19",
      title: "有効成分に関する理化学的知見",
    },
    kind: "section",
    excerpt:
      "<p>リバーロキサバン（Rivaroxaban）</p><p>5-Chloro-N-({(5S)-2-oxo-3-[4-(3-oxomorpholin-4-yl)phenyl]-1,3-oxazolidin-5-yl}methyl)thiophene-2-carboxamide</p><p>C_{19}H_{18}ClN_{3}O_{5}S</p><p>435.88</p><p>本品は白色～微黄色の粉末である。</p><p></p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:21",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "21",
      title: "承認条件",
    },
    kind: "section",
    excerpt: "<p>医薬品リスク管理計画を策定の上、適切に実施すること。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:22",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "22",
      title: "包装",
    },
    kind: "section",
    excerpt: "<p>100錠［10錠（PTP）×10］</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:23",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "23",
      title: "主要文献",
    },
    kind: "section",
    excerpt:
      "<p>社内資料: 妊娠ラットにおける胎盤通過性（10mg/15mg錠2012年1月18日承認、CTD2.6.4.4.6）</p><p>社内資料: ウサギにおける胚・胎児発生に関する毒性試験（10mg/15mg錠2012年1月18日承認、CTD2.6.6.6.2.2）</p><p>社内資料: ラットにおける出生前及び出生後の発生並びに母体の機能に関する試験（10mg/15mg錠2012年1月18日承認、CTD2.6.6.6.3）</p><p>社内資料: ラットにおける乳汁中分泌（10mg/15mg錠2012年1月18日承認、CTD2.6.4.6.4）</p><p>Brodsky S, et al.: J Am Soc Nephrol. 2018; 29: 2787-2793</p><p>Zakrocka I, et al.: Adv Clin Exp Med. 2022; 31: 165-173</p><p>Pengo V, et al.: Blood. 2018; 132: 1365-1371</p><p>社内資料: 日本人急性症候性深部静脈血栓症患者及び急性症候性肺塞栓症患者における曝露量の推定</p><p>社内資料: 症候性末梢動脈疾患患者を対象とした国際共同第Ⅲ相試験（2022年6月20日承認、CTD2.7.6.1）</p><p>Perzborn E, et al.: J Thromb Haemost. 2005; 3: 514-521</p><p>Biemond BJ, et al.: Thromb Haemost. 2007; 97: 471-477</p><p>社内資料: マウスにおける血栓塞栓死予防試験（10mg/15mg錠2012年1月18日承認、CTD2.6.2.2.2.1.8）</p><p>社内資料: Fontan手術後の2～8歳の小児を対象とした第Ⅲ相試験（2023年11月24日承認、CTD2.7.6.1）</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:24",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "24",
      title: "文献請求先及び問い合わせ先",
    },
    kind: "section",
    excerpt:
      "<p>文献請求先<br>バイエル薬品株式会社・メディカルインフォメーション</p><p>〒530-0001大阪市北区梅田二丁目4番9号</p><p>バイエル医療用医薬品のお問い合わせ先</p><p>電話0120-106-398</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:26",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "26",
      title: "製造販売業者等",
    },
    kind: "section",
    excerpt:
      "<p>製造販売元</p><p>バイエル薬品株式会社</p><p>大阪市北区梅田二丁目4番9号</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic"],
  },
];

export const realCalonalEvidence: SourceItem[] = [
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "1",
      title: "警告",
    },
    kind: "section",
    excerpt:
      "<p>本剤により重篤な肝障害が発現するおそれがあることに注意し、1日総量1500mgを超す高用量で長期投与する場合には、定期的に肝機能等を確認するなど慎重に投与すること。</p><p>本剤とアセトアミノフェンを含む他の薬剤（一般用医薬品を含む）との併用により、アセトアミノフェンの過量投与による重篤な肝障害が発現するおそれがあることから、これらの薬剤との併用を避けること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ImportantPrecautions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_InfoPrecautionsDosage_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ImportantPrecautions_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "13.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_OverDosage_2",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:2",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "2",
      title: "禁忌",
    },
    kind: "section",
    excerpt:
      "<p>重篤な肝障害のある患者</p><p>本剤の成分に対し過敏症の既往歴のある患者</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.3.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_PatientsWithHepaticImpairment_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:3.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "3.1",
      title: "組成",
    },
    kind: "section",
    excerpt:
      "<p>（日局）アセトアミノフェン</p><p>1錠中 200mg</p><p>乳糖水和物、結晶セルロース、部分アルファー化デンプン、ポリビニルアルコール（部分けん化物）、ステアリン酸マグネシウム、香料</p><p>（日局）アセトアミノフェン</p><p>1錠中 300mg</p><p>乳糖水和物、結晶セルロース、部分アルファー化デンプン、ポリビニルアルコール（部分けん化物）、ステアリン酸マグネシウム、香料</p><p>（日局）アセトアミノフェン</p><p>1錠中 500mg</p><p>ステアリン酸、アルファー化デンプン、ポビドン、クロスポビドン、ステアリン酸マグネシウム</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:3.2",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "3.2",
      title: "製剤の性状",
    },
    kind: "section",
    excerpt:
      "<p>割線入り錠剤</p><p>白色</p><p>［図:172190_1141007F1063_5_07_fig01.gif］</p><p>［図:172190_1141007F1063_5_07_fig02.gif］</p><p>［図:172190_1141007F1063_5_07_fig03.gif］</p><p>10.0mm</p><p>3.3mm</p><p>300mg</p><p>SD112</p><p>わずかにメントールのにおい</p><p>苦い</p><p>素錠</p><p>白色</p><p>［図:172190_1141007F1063_5_07_fig04.gif］</p><p>［図:172190_1141007F1063_5_07_fig05.gif］</p><p>［図:172190_1141007F1063_5_07_fig06.gif］</p><p>10.0mm</p><p>4.0mm</p><p>375mg</p><p>SD113</p><p>わずかにメントールのにおい</p><p>苦い</p><p>割線入りの素錠</p><p>白色</p><p>［図:172190_1141007F1063_5_07_fig07.gif］</p><p>［図:172190_1141007F1063_5_07_fig08.gif］</p><p>［図:172190_1141007F1063_5_07_fig09.gif］</p><p>15.0mm</p><p>8.0mm</p><p>5.9mm</p><p>560mg</p><p>SD115</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:4",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "4",
      title: "効能又は効果",
    },
    kind: "section",
    excerpt:
      "<p>各種疾患及び症状における鎮痛</p><p>下記疾患の解熱・鎮痛<br>急性上気道炎（急性気管支炎を伴う急性上気道炎を含む）</p><p>小児科領域における解熱・鎮痛</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:6",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "6",
      title: "用法及び用量",
    },
    kind: "section",
    excerpt:
      "<p>〈各種疾患及び症状における鎮痛〉<br>通常、成人にはアセトアミノフェンとして、1回300～1000mgを経口投与し、投与間隔は4～6時間以上とする。なお、年齢、症状により適宜増減するが、1日総量として4000mgを限度とする。また、空腹時の投与は避けさせることが望ましい。</p><p>〈急性上気道炎（急性気管支炎を伴う急性上気道炎を含む）〉<br>通常、成人にはアセトアミノフェンとして、1回300～500mgを頓用する。なお、年齢、症状により適宜増減する。ただし、原則として1日2回までとし、1日最大1500mgを限度とする。また、空腹時の投与は避けさせることが望ましい。</p><p>〈小児科領域における解熱・鎮痛〉<br>通常、幼児及び小児にはアセトアミノフェンとして、体重1kgあたり1回10～15mgを経口投与し、投与間隔は4～6時間以上とする。なお、年齢、症状により適宜増減するが、1日総量として60mg/kgを限度とする。ただし、成人の用量を超えない。また、空腹時の投与は避けさせることが望ましい。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:7",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "7",
      title: "用法及び用量に関連する注意",
    },
    kind: "section",
    excerpt:
      '<p>幼児及び小児の1回投与量の目安は下記のとおり。</p><table><thead><tr><th>体重</th><th>1回用量</th></tr></thead><tbody><tr><td rowspan="2" colspan="1">体重</td><td rowspan="1" colspan="4">1回用量</td></tr><tr><td rowspan="1" colspan="1">アセトアミノフェン</td><td rowspan="1" colspan="1">錠200</td><td rowspan="1" colspan="1">錠300</td><td rowspan="1" colspan="1">錠500</td></tr><tr><td rowspan="1" colspan="1">10kg</td><td rowspan="1" colspan="1">100-150mg</td><td rowspan="1" colspan="1">0.5錠</td><td rowspan="1" colspan="1">－</td><td rowspan="1" colspan="1">－</td></tr><tr><td rowspan="1" colspan="1">20kg</td><td rowspan="1" colspan="1">200-300mg</td><td rowspan="1" colspan="1">1-1.5錠<br>（アセトアミノフェン200-300mg）</td><td rowspan="1" colspan="1">1錠<br>（アセトアミノフェン300mg）</td><td rowspan="1" colspan="1">0.5錠<br>（アセトアミノフェン250mg）</td></tr><tr><td rowspan="1" colspan="1">30kg</td><td rowspan="1" colspan="1">300-450mg</td><td rowspan="1" colspan="1">1.5-2錠<br>（アセトアミノフェン300-400mg）</td><td rowspan="1" colspan="1">1錠<br>（アセトアミノフェン300mg）</td><td rowspan="1" colspan="1">－</td></tr></tbody></table><p>「小児科領域における解熱・鎮痛」の効能又は効果に対する1回あたりの最大用量はアセトアミノフェンとして500mg、1日あたりの最大用量はアセトアミノフェンとして1500mgである。</p><p>他の消炎鎮痛剤との併用は避けることが望ましい。</p><p>本剤とアセトアミノフェンを含む他の薬剤（一般用医薬品を含む）との併用により、アセトアミノフェンの過量投与による重篤な肝障害が発現するおそれがあることから、特に総合感冒剤や解熱鎮痛剤等の配合剤を併用する場合は、アセトアミノフェンが含まれていないか確認し、含まれている場合は併用を避けること。</p><p>アスピリン喘息又はその既往歴のある患者に対する1回あたりの最大用量はアセトアミノフェンとして300mg以下とすること。</p>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_PediatricUse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ImportantPrecautions_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_8",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:8",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "8",
      title: "重要な基本的注意",
    },
    kind: "section",
    excerpt:
      "<p>解熱鎮痛剤による治療は原因療法ではなく対症療法であることから原因療法があればこれを行うこと。</p><p>重篤な肝障害が発現するおそれがあるので、1日総量1500mgを超す高用量で長期投与する場合には定期的に肝機能検査を行い、患者の状態を十分に観察すること。高用量でなくとも長期投与する場合にあっては定期的に肝機能検査を行うことが望ましい。また、高用量で投与する場合などは特に患者の状態を十分に観察すること。</p><p><strong>〈急性疾患に対し本剤を用いる場合には、次の事項を考慮すること。〉</strong></p><p>発熱、疼痛の程度を考慮し投与すること。</p><p><strong>〈急性疾患に対し本剤を用いる場合には、次の事項を考慮すること。〉</strong></p><p>原則として同一の薬剤の長期投与を避けること。</p><p>慢性疾患に対し本剤を用いる場合には、薬物療法以外の療法も考慮すること。</p><p>過度の体温下降、虚脱、四肢冷却等があらわれることがあるので、特に高熱を伴う高齢者及び小児等又は消耗性疾患の患者においては、投与後の患者の状態に十分注意すること。</p><p>アセトアミノフェンを含む他の薬剤と併用しないよう患者に指導すること。</p><p>アセトアミノフェンの高用量投与により副作用として腹痛・下痢がみられることがある。本剤においても同様の副作用があらわれるおそれがあり、上気道炎等に伴う消化器症状と区別できないおそれがあるので、観察を十分行い慎重に投与すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_Warnings_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_InfoPrecautionsDosage_4",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.1",
      title: "合併症・既往歴等のある患者",
    },
    kind: "section",
    excerpt:
      "<p>アルコール多量常飲者<br>肝障害があらわれやすくなる。</p><p>絶食・低栄養状態・摂食障害等によるグルタチオン欠乏、脱水症状のある患者<br>肝障害があらわれやすくなる。</p><p>消化性潰瘍又はその既往歴のある患者<br>症状が悪化又は再発を促すおそれがある。</p><p>血液の異常又はその既往歴のある患者<br>症状が悪化又は再発を促すおそれがある。</p><p>出血傾向のある患者<br>血小板機能異常が起こることがある。</p><p>心機能異常のある患者<br>症状が悪化又は心不全が増悪するおそれがある。</p><p>気管支喘息のある患者<br>症状が悪化するおそれがある。</p><p>アスピリン喘息（非ステロイド性消炎鎮痛剤による喘息発作の誘発）又はその既往歴のある患者<br>アスピリン喘息の発症にプロスタグランジン合成阻害作用が関与していると考えられ、症状が悪化又は再発を促すおそれがある。</p><p>感染症を合併している患者<br>必要に応じて適切な抗菌剤を併用し、観察を十分に行い慎重に投与すること。感染症を不顕性化するおそれがある。</p><p>重篤な腎障害・肝障害（重篤な肝障害を除く）・敗血症・栄養障害等によるピログルタミン酸蓄積の素因のある患者<br>ピログルタミン酸の排泄阻害又はグルタチオン欠乏が生じているため、本剤投与によりピログルタミン酸の蓄積が促進された結果、アニオンギャップ開大性代謝性アシドーシスが発現するおそれがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_PrecautionsForCombinations",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "7.5",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_InfoPrecautionsDosage_5",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.3",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_3",
      },
      {
        kind: "HeaderRef",
        target_section_code: "10.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_PrecautionsForCombinations",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.2",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.2",
      title: "腎機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>腎障害又はその既往歴のある患者<br>投与量の減量、投与間隔の延長を考慮すること。症状が悪化又は再発を促すおそれがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "11.1.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_7",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.3",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.3",
      title: "肝機能障害患者",
    },
    kind: "section",
    excerpt:
      "<p>重篤な肝障害のある患者<br>投与しないこと。重篤な転帰をとるおそれがある。</p><p>肝障害又はその既往歴のある患者（重篤な肝障害のある患者を除く）<br>肝障害が悪化するおそれがある。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_SeriousAdverseEvents_4",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.5",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.5",
      title: "妊婦",
    },
    kind: "section",
    excerpt:
      "<p>妊婦又は妊娠している可能性のある女性には、次のリスクを考慮し、治療上の有益性が危険性を上回ると判断される場合にのみ投与すること。</p><p>妊娠後期の女性への投与により胎児に動脈管収縮を起こすことがある。</p><p>妊娠後期のラットに投与した実験で、弱い胎仔の動脈管収縮が報告されている。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_01",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.6",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.6",
      title: "授乳婦",
    },
    kind: "section",
    excerpt:
      "<p>治療上の有益性及び母乳栄養の有益性を考慮し、授乳の継続又は中止を検討すること。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.7",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.7",
      title: "小児等",
    },
    kind: "section",
    excerpt:
      "<p>副作用の発現に特に注意し、必要最小限の使用にとどめるなど慎重に投与すること。</p><p>低出生体重児、新生児及び3ヵ月未満の乳児を対象とした有効性及び安全性を指標とした臨床試験は実施していない。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_InfoPrecautionsDosage_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:9.8",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "9.8",
      title: "高齢者",
    },
    kind: "section",
    excerpt:
      "<p>副作用の発現に特に注意し、少量から投与を開始するなど患者の状態を観察しながら慎重に投与すること。副作用があらわれやすい。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:10.2",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th>薬剤名等</th><th>臨床症状・措置方法</th><th>機序・危険因子</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">リチウム製剤<br>炭酸リチウム</td><td rowspan="1" colspan="1">他の非ステロイド性消炎鎮痛剤（インドメタシン、イブプロフェン等）で、リチウムとの併用によりリチウムの血中濃度が上昇し、リチウム中毒を呈したとの報告がある。</td><td rowspan="1" colspan="1">非ステロイド性消炎鎮痛剤は腎のプロスタグランジン合成を抑制することにより、炭酸リチウムの排泄が減少し、血中濃度が上昇すると考えられている。</td></tr><tr><td rowspan="1" colspan="1">チアジド系利尿剤<br>ヒドロクロロチアジド等</td><td rowspan="1" colspan="1">他の非ステロイド性消炎鎮痛剤（インドメタシン等）で、チアジド系利尿剤の作用を減弱することが報告されている。</td><td rowspan="1" colspan="1">非ステロイド性消炎鎮痛剤は腎のプロスタグランジン合成を抑制して水、塩類貯留が生じ、チアジド系利尿剤の排泄作用に拮抗すると考えられている。</td></tr><tr><td rowspan="1" colspan="1">アルコール（飲酒）</td><td rowspan="1" colspan="1">アルコール多量常飲者がアセトアミノフェンを服用したところ肝不全を起こしたとの報告がある。</td><td rowspan="1" colspan="1">アルコール常飲によるCYP2E1の誘導により、アセトアミノフェンから肝毒性を持つN-アセチル-p-ベンゾキノンイミンへの代謝が促進される。</td></tr><tr><td rowspan="1" colspan="1">クマリン系抗凝血剤<br>ワルファリンカリウム</td><td rowspan="1" colspan="1">クマリン系抗凝血剤の作用を増強することがあるので、減量するなど慎重に投与すること。</td><td rowspan="1" colspan="1">本剤が血漿蛋白結合部位において競合することで、抗凝血剤を遊離させ、その抗凝血作用を増強させる。</td></tr><tr><td rowspan="1" colspan="1">カルバマゼピン<br>フェノバルビタール<br>フェニトイン<br>プリミドン<br>リファンピシン<br>イソニアジド</td><td rowspan="1" colspan="1">これらの薬剤の長期連用者は、肝薬物代謝酵素が誘導され、肝障害を生じやすくなるとの報告がある。</td><td rowspan="1" colspan="1">これらの薬剤の代謝酵素誘導作用により、アセトアミノフェンから肝毒性を持つN-アセチル-p-ベンゾキノンイミンへの代謝が促進される。</td></tr><tr><td rowspan="1" colspan="1">抗生物質<br>抗菌剤</td><td rowspan="1" colspan="1">過度の体温下降を起こす頻度が高くなることから、併用する場合には観察を十分に行い、慎重に投与すること。</td><td rowspan="1" colspan="1">機序は不明である。</td></tr></tbody></table>',
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.9",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_9",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:11",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "11",
      title: "副作用",
    },
    kind: "section",
    excerpt:
      "<p>次の副作用があらわれることがあるので、観察を十分に行い、異常が認められた場合には投与を中止するなど適切な処置を行うこと。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:11.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "11.1",
      title: "重大な副作用",
    },
    kind: "section",
    excerpt:
      "<p>ショック、アナフィラキシー（いずれも頻度不明）<br>ショック、アナフィラキシー（呼吸困難、全身潮紅、血管性浮腫、蕁麻疹等）があらわれることがある。</p><p>中毒性表皮壊死融解症（Toxic Epidermal Necrolysis：TEN）、皮膚粘膜眼症候群（Stevens-Johnson症候群）、急性汎発性発疹性膿疱症（いずれも頻度不明）</p><p>喘息発作の誘発（頻度不明）</p><p>劇症肝炎、肝機能障害、黄疸（いずれも頻度不明）<br>劇症肝炎、AST、ALT、γ-GTPの上昇等を伴う肝機能障害、黄疸があらわれることがある。</p><p>顆粒球減少症（頻度不明）</p><p>間質性肺炎（頻度不明）<br>咳嗽、呼吸困難、発熱、肺音の異常等が認められた場合には、速やかに胸部X線、胸部CT、血清マーカー等の検査を実施すること。異常が認められた場合には投与を中止し、副腎皮質ホルモン剤の投与等の適切な処置を行うこと。</p><p>間質性腎炎、急性腎障害（いずれも頻度不明）</p><p>薬剤性過敏症症候群（頻度不明）<br>初期症状として発疹、発熱がみられ、更に肝機能障害、リンパ節腫脹、白血球増加、好酸球増多、異型リンパ球出現等を伴う遅発性の重篤な過敏症状があらわれることがある。なお、ヒトヘルペスウイルス6（HHV-6）等のウイルスの再活性化を伴うことが多く、投与中止後も発疹、発熱、肝機能障害等の症状が再燃あるいは遷延化することがあるので注意すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ContraIndications_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_7",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_8",
      },
      {
        kind: "HeaderRef",
        target_section_code: "1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_Warnings_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_ImportantPrecautions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.3.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_PatientsWithHepaticImpairment_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.4",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_4",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_PatientsWithRenalImpairment_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:11.2",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "11.2",
      title: "その他の副作用",
    },
    kind: "section",
    excerpt:
      '<table><thead><tr><th></th><th>頻度不明</th></tr></thead><tbody><tr><td rowspan="1" colspan="1">血液</td><td rowspan="1" colspan="1">チアノーゼ、血小板減少、血小板機能低下（出血時間の延長）</td></tr><tr><td rowspan="1" colspan="1">消化器</td><td rowspan="1" colspan="1">悪心・嘔吐、食欲不振</td></tr><tr><td rowspan="1" colspan="1">その他</td><td rowspan="1" colspan="1">過敏症</td></tr></tbody></table><p>このような症状（異常）があらわれた場合には、投与を中止すること。</p>',
    columns: null,
    references: [
      {
        kind: "CommentRef",
        target_section_code: "11.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#TBLFN_01",
      },
      {
        kind: "CommentRef",
        target_section_code: "11.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#TBLFN_01",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:13",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "13",
      title: "過量投与",
    },
    kind: "section",
    excerpt:
      "<p>症状<br>肝臓・腎臓・心筋の壊死が起こったとの報告がある。</p><p>処置<br>解毒（肝障害の軽減等）には、アセチルシステインの投与を考慮すること。</p>",
    columns: null,
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "1.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_Warnings_2",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:14",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "14",
      title: "適用上の注意",
    },
    kind: "section",
    excerpt:
      "<p>薬剤交付時の注意 PTP包装の薬剤はPTPシートから取り出して服用するよう指導すること。PTPシートの誤飲により、硬い鋭角部が食道粘膜へ刺入し、更には穿孔をおこして縦隔洞炎等の重篤な合併症を併発することがある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:15",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "15",
      title: "その他の注意",
    },
    kind: "section",
    excerpt:
      "<p>類似化合物（フェナセチン）を長期・大量投与した動物実験で、腫瘍発生が認められたとの報告がある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:15.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "15.1",
      title: "臨床使用に基づく情報",
    },
    kind: "section",
    excerpt:
      "<p>類似化合物（フェナセチン）の長期投与により、血色素異常を起こすことがある。</p><p>腎盂及び膀胱腫瘍の患者を調査したところ、類似化合物（フェナセチン）製剤を長期・大量に使用（例：総服用量1.5～27kg、服用期間4～30年）していた人が多いとの報告がある。</p><p>非ステロイド性消炎鎮痛剤を長期間投与されている女性において、一時的な不妊が認められたとの報告がある。</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:16",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "16",
      title: "薬物動態",
    },
    kind: "section",
    excerpt: "<p>は溶出挙動に基づき、と生物学的に同等とみなされた。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_06",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:16.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "16.1",
      title: "血中濃度",
    },
    kind: "section",
    excerpt:
      '<p>生物学的同等性試験〈〉<br>クロスオーバー法により、健康成人男性に、 2錠と標準製剤（細粒剤20%）2.0g（アセトアミノフェンとして400mg）をそれぞれ空腹時単回経口投与したとき、アセトアミノフェンの血中濃度及び薬物動態パラメータは以下のとおりであり、両剤の生物学的同等性が確認された。</p><p><strong>〈生物学的同等性試験〈〉〉</strong></p><table><thead><tr><th></th><th>判定パラメータ</th><th>参考パラメータ</th></tr></thead><tbody><tr><td rowspan="2" colspan="1"></td><td rowspan="1" colspan="2">判定パラメータ</td><td rowspan="1" colspan="2">参考パラメータ</td></tr><tr><td rowspan="1" colspan="1">AUC_{0-12}<br>（μg・hr/mL）</td><td rowspan="1" colspan="1">Cmax<br>（μg/mL）</td><td rowspan="1" colspan="1">Tmax<br>（hr）</td><td rowspan="1" colspan="1">t_{1/2}<br>（hr）</td></tr><tr><td rowspan="1" colspan="1">（錠剤200mg、2錠）</td><td rowspan="1" colspan="1">19.03±2.45</td><td rowspan="1" colspan="1">9.1±2.9</td><td rowspan="1" colspan="1">0.46±0.19</td><td rowspan="1" colspan="1">2.36±0.28</td></tr><tr><td rowspan="1" colspan="1">標準製剤（細粒剤20%、2.0g）</td><td rowspan="1" colspan="1">19.20±2.04</td><td rowspan="1" colspan="1">9.1±3.2</td><td rowspan="1" colspan="1">0.43±0.23</td><td rowspan="1" colspan="1">2.45±0.21</td></tr></tbody></table><p><strong>〈生物学的同等性試験〈〉〉</strong></p><p>（Mean±S.D.、n=14）</p><p><strong>〈生物学的同等性試験〈〉〉</strong></p><p></p><p><strong>〈生物学的同等性試験〈〉〉</strong></p><p>〈〉<br>クロスオーバー法により、健康成人男性に、 1錠と標準製剤（錠剤200mgと錠剤300mg各1錠）をそれぞれ空腹時単回経口投与したとき、アセトアミノフェンの血中濃度及び薬物動態パラメータは以下のとおりであり、両剤の生物学的同等性が確認された。</p><p><strong>〈生物学的同等性試験〈〉〉</strong></p><p><strong>〈〈〉〉</strong></p><table><thead><tr><th></th><th>判定パラメータ</th><th>参考パラメータ</th></tr></thead><tbody><tr><td rowspan="2" colspan="1"></td><td rowspan="1" colspan="2">判定パラメータ</td><td rowspan="1" colspan="2">参考パラメータ</td></tr><tr><td rowspan="1" colspan="1">AUC_{0-12}<br>（μg・hr/mL）</td><td rowspan="1" colspan="1">Cmax<br>（μg/mL）</td><td rowspan="1" colspan="1">Tmax<br>（hr）</td><td rowspan="1" colspan="1">t_{1/2}<br>（hr）</td></tr><tr><td rowspan="1" colspan="1">（錠剤500mg、1錠）</td><td rowspan="1" colspan="1">27.81±5.04</td><td rowspan="1" colspan="1">8.19±2.65</td><td rowspan="1" colspan="1">0.79±0.49</td><td rowspan="1" colspan="1">2.91±0.38</td></tr><tr><td rowspan="1" colspan="1">標準製剤（錠剤200mg+錠剤300mg 各1錠）</td><td rowspan="1" colspan="1">27.28±5.35</td><td rowspan="1" colspan="1">7.88±2.13</td><td rowspan="1" colspan="1">0.83±0.87</td><td rowspan="1" colspan="1">2.92±0.38</td></tr></tbody></table><p><strong>〈生物学的同等性試験〈〉〉</strong></p><p><strong>〈〈〉〉</strong></p><p>（Mean±S.D.、n=19）</p><p><strong>〈生物学的同等性試験〈〉〉</strong></p><p><strong>〈〈〉〉</strong></p><p></p>',
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_02",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_03",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:16.5",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "16.5",
      title: "排泄",
    },
    kind: "section",
    excerpt:
      "<p>代謝物は主に尿中に排泄される。健康成人男性14例にアセトアミノフェン500mgを経口単回投与した結果、投与量の約80%が投与開始24時間後までに尿中に排泄された。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_04",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:16.6",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "16.6",
      title: "特定の背景を有する患者",
    },
    kind: "section",
    excerpt:
      "<p>肝機能障害患者<br>肝硬変患者は健康成人に比べてAUC値は高く、クリアランスは低く、また半減期は長かった（外国人データ）。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_05",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:17.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "17.1",
      title: "有効性及び安全性に関する試験",
    },
    kind: "section",
    excerpt:
      "<p><strong>〈＜歯科治療後の疼痛＞〉</strong></p><p>国内臨床試験<br>歯痛及び抜歯後の疼痛を有する患者32例に対し、を2錠頓用投与した。有効率（有効以上）は歯痛に対し71.4%（5/7）、抜歯後の疼痛に対し56.0%（14/25）であった。副作用として、軽度の頭重感、胃部不快感を各1例認めたが、いずれも処置を必要とせず回復した。</p><p><strong>〈＜感冒による発熱、頭痛等の疼痛＞〉</strong></p><p><strong>〈国内臨床試験〉</strong></p><p>感冒による発熱、頭痛等の疼痛を有する患者34例に対し、を2錠頓用投与した。有効率（有効以上）は解熱に対し66.7%（4/6）、鎮痛に対し75.0%（21/28）であった。副作用として、軽度のむかつき、眠気、中等度の唾液分泌が各1例の3例に認めたが、いずれも処置を必要とせず回復した。</p><p><strong>〈＜感冒による発熱、頭痛等の疼痛＞〉</strong></p><p><strong>〈国内臨床試験〉</strong></p><p>感冒による発熱、頭痛等の疼痛を有する患者21例に対し、を2錠頓用投与した。有効率（有効以上）は解熱に対し73.3%（11/15）、鎮痛に対し50.0%（3/6）であった。副作用は認めなかった。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_07",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_08",
      },
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_09",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:18.1",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "18.1",
      title: "作用機序",
    },
    kind: "section",
    excerpt:
      "<p>アセトアミノフェンの作用の正確な部位や機序は完全には解明されていないが、作用機序としては、中枢神経系に作用し、プロスタグランジン合成、カンナビノイド受容体系又はセロトニン作動系などに影響を及ぼすと考えられている。</p>",
    columns: null,
    references: [
      {
        kind: "ReferenceBookRef",
        target_section_code: "23",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#DOC_10",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:19",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "19",
      title: "有効成分に関する理化学的知見",
    },
    kind: "section",
    excerpt:
      "<p>アセトアミノフェン（Acetaminophen）</p><p>N-(4-Hydroxyphenyl)acetamide</p><p>C_{8}H_{9}NO_{2}</p><p>151.16</p><p>白色の結晶又は結晶性の粉末である。メタノール又はエタノール（95）に溶けやすく、水にやや溶けにくく、ジエチルエーテルに極めて溶けにくい。水酸化ナトリウム試液に溶ける。</p><p></p><p>169～172℃</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:22",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "22",
      title: "包装",
    },
    kind: "section",
    excerpt:
      "<p>〈〉<br>100錠［10錠（PTP）×10］<br>1000錠［10錠（PTP）×100］<br>500錠［瓶、バラ］</p><p>〈〉<br>100錠［10錠（PTP）×10］<br>1000錠［10錠（PTP）×100］<br>500錠［瓶、バラ］</p><p>〈〉<br>100錠［10錠（PTP）×10］<br>500錠［10錠（PTP）×50］<br>500錠［瓶、バラ］</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:23",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "23",
      title: "主要文献",
    },
    kind: "section",
    excerpt:
      "<p>門間和夫 他：小児科の進歩2（診断と治療社）1983；95-101〔SYK000835〕</p><p>あゆみ製薬（株）社内資料：カロナール錠200の生物学的同等性試験</p><p>あゆみ製薬（株）社内資料：カロナール錠500の生物学的同等性試験</p><p>大西明弘 他：基礎と臨床 1993；27（11）：4310-4321〔SYK000122〕</p><p>Zapater, P.et al.：Aliment Pharmacol Ther.2004；20（1）：29-36〔SYK010993〕</p><p>あゆみ製薬（株）社内資料：カロナール錠300の生物学的同等性試験</p><p>扇内秀樹 他：基礎と臨床 1996；30（7）：1785-1790〔SYK000813〕</p><p>三木 亮 他：基礎と臨床 1996；30（7）：1773-1777〔SYK010691〕</p><p>牛嶋 久：基礎と臨床 1996；30（7）：1779-1784〔SYK000837〕</p><p>鈴木孝浩：ペインクリニック 2012；33（2）：218-226〔SYK012768〕</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:24",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "24",
      title: "文献請求先及び問い合わせ先",
    },
    kind: "section",
    excerpt:
      "<p>あゆみ製薬株式会社</p><p>〒104-0061 東京都中央区銀座四丁目12番15号</p><p>TEL：0120-137-413</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
  {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:26",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "26",
      title: "製造販売業者等",
    },
    kind: "section",
    excerpt:
      "<p>製造販売元</p><p>あゆみ製薬株式会社</p><p>東京都中央区銀座四丁目12番15号</p>",
    columns: null,
    references: [],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic"],
  },
];

export const realInteractionRows: Record<string, SourceItem> = {
  metgluco_contrast_agent: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.2:row-0",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "interaction_row",
    excerpt:
      "ヨード造影剤\n併用により乳酸アシドーシスを起こすことがある。\nヨード造影剤を用いて検査を行う場合には、本剤の投与を一時的に中止すること。\n腎機能が低下し、本剤の排泄が低下することが考えられている。",
    columns: {
      drug_name: "ヨード造影剤",
      clinical_symptoms_and_measures:
        "併用により乳酸アシドーシスを起こすことがある。\nヨード造影剤を用いて検査を行う場合には、本剤の投与を一時的に中止すること。",
      mechanism_and_risk_factors:
        "腎機能が低下し、本剤の排泄が低下することが考えられている。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  metgluco_gentamicin: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.2:row-1",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "interaction_row",
    excerpt:
      "腎毒性の強い抗生物質\nゲンタマイシン等\n併用により乳酸アシドーシスを起こすことがある。併用する場合は本剤の投与を一時的に減量・中止するなど適切な処置を行うこと。\n腎機能が低下し、本剤の排泄が低下することが考えられている。",
    columns: {
      drug_name: "腎毒性の強い抗生物質\nゲンタマイシン等",
      clinical_symptoms_and_measures:
        "併用により乳酸アシドーシスを起こすことがある。併用する場合は本剤の投与を一時的に減量・中止するなど適切な処置を行うこと。",
      mechanism_and_risk_factors:
        "腎機能が低下し、本剤の排泄が低下することが考えられている。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  metgluco_diuretics: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.2:row-2",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "interaction_row",
    excerpt:
      "利尿作用を有する薬剤\n利尿剤\nSGLT2阻害剤 等\n脱水により乳酸アシドーシスを起こすことがある。脱水症状があらわれた場合には、本剤の投与を中止し、適切な処置を行うこと。\n利尿作用を有する薬剤により、体液量が減少し脱水状態になることがある。",
    columns: {
      drug_name: "利尿作用を有する薬剤\n利尿剤\nSGLT2阻害剤 等",
      clinical_symptoms_and_measures:
        "脱水により乳酸アシドーシスを起こすことがある。脱水症状があらわれた場合には、本剤の投与を中止し、適切な処置を行うこと。",
      mechanism_and_risk_factors:
        "利尿作用を有する薬剤により、体液量が減少し脱水状態になることがある。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  metgluco_alcohol: {
    unit_id:
      "400093_3962002F2027_1_22:544d151539dfb2c6737aa3a84c6f224df75957b5aa60a6d3989f3ff3b87cf8b7:10.1:row-0",
    document_id: "400093_3962002F2027_1_22",
    product_name: "メトグルコ錠250mg／メトグルコ錠500mg",
    generic_name: "メトホルミン塩酸塩",
    product_yj_codes: ["3962002F2027", "3962002F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2023-11",
    },
    section: {
      code: "10.1",
      title: "併用禁忌",
    },
    kind: "interaction_row",
    excerpt:
      "アルコール（過度の摂取）\n乳酸アシドーシスを起こすことがある。本剤の投与中は過度のアルコール摂取（飲酒）を避けること。\n肝臓における乳酸の代謝能が低下する。また、脱水状態を来すことがある。",
    columns: {
      drug_name: "アルコール（過度の摂取）",
      clinical_symptoms_and_measures:
        "乳酸アシドーシスを起こすことがある。本剤の投与中は過度のアルコール摂取（飲酒）を避けること。",
      mechanism_and_risk_factors:
        "肝臓における乳酸の代謝能が低下する。また、脱水状態を来すことがある。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ContraIndications_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "8.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_ImportantPrecautions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "11.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22#HDR_SeriousAdverse_1",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/400093_3962002F2027_1_22",
    retrieved_by: ["logic", "jev"],
  },
  xarelto_itraconazole: {
    unit_id:
      "630004_3339003F5020_1_08:2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c:10.1:row-0",
    document_id: "630004_3339003F5020_1_08",
    product_name: "イグザレルト錠2.5mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: {
      source_label: "今回",
      version: "第8版",
      year_month: "2025-11",
    },
    section: {
      code: "10.1",
      title: "併用禁忌",
    },
    kind: "interaction_row",
    excerpt:
      "リトナビルを含有する製剤（ノービア、カレトラ、パキロビッド）\nダルナビル（プリジスタ）\nホスアンプレナビル（レクシヴァ）\n本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。\nCYP3A4の強力な阻害及びP-糖タンパクの阻害によりクリアランスが減少する。",
    columns: {
      drug_name:
        "リトナビルを含有する製剤（ノービア、カレトラ、パキロビッド）\nダルナビル（プリジスタ）\nホスアンプレナビル（レクシヴァ）",
      clinical_symptoms_and_measures:
        "本剤の血中濃度が上昇し、抗凝固作用が増強されることにより、出血の危険性が増大するおそれがある。",
      mechanism_and_risk_factors:
        "CYP3A4の強力な阻害及びP-糖タンパクの阻害によりクリアランスが減少する。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "2.6",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_6",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.7",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_7",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.8",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_8",
      },
      {
        kind: "HeaderRef",
        target_section_code: "16.7.2",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_DrugAndDrugInteractions_2",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.9",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_9",
      },
      {
        kind: "HeaderRef",
        target_section_code: "2.10",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08#HDR_ContraIndications_10",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/630004_3339003F5020_1_08",
    retrieved_by: ["logic", "jev"],
  },
  calonal_warfarin: {
    unit_id:
      "172190_1141007F1063_5_07:36d0f12d90d3f975360a7c7d936487597f183b51d647d53ae7d425ae1c4db889:10.2:row-0",
    document_id: "172190_1141007F1063_5_07",
    product_name: "カロナール錠200／カロナール錠300／カロナール錠500",
    generic_name: "アセトアミノフェン錠",
    product_yj_codes: ["1141007F1063", "1141007F2027", "1141007F3023"],
    document_revision: {
      source_label: "今回",
      version: "第5版",
      year_month: "2026-08",
    },
    section: {
      code: "10.2",
      title: "併用注意",
    },
    kind: "interaction_row",
    excerpt:
      "リチウム製剤\n炭酸リチウム\n他の非ステロイド性消炎鎮痛剤（インドメタシン、イブプロフェン等）で、リチウムとの併用によりリチウムの血中濃度が上昇し、リチウム中毒を呈したとの報告がある。\n非ステロイド性消炎鎮痛剤は腎のプロスタグランジン合成を抑制することにより、炭酸リチウムの排泄が減少し、血中濃度が上昇すると考えられている。",
    columns: {
      drug_name: "リチウム製剤\n炭酸リチウム",
      clinical_symptoms_and_measures:
        "他の非ステロイド性消炎鎮痛剤（インドメタシン、イブプロフェン等）で、リチウムとの併用によりリチウムの血中濃度が上昇し、リチウム中毒を呈したとの報告がある。",
      mechanism_and_risk_factors:
        "非ステロイド性消炎鎮痛剤は腎のプロスタグランジン合成を抑制することにより、炭酸リチウムの排泄が減少し、血中濃度が上昇すると考えられている。",
    },
    references: [
      {
        kind: "HeaderRef",
        target_section_code: "9.1.1",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_1",
      },
      {
        kind: "HeaderRef",
        target_section_code: "9.1.9",
        target_url:
          "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07#HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc_9",
      },
    ],
    url: "https://www.pmda.go.jp/PmdaSearch/iyakuDetail/172190_1141007F1063_5_07",
    retrieved_by: ["logic", "jev"],
  },
};
