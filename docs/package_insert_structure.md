# 医療用医薬品 添付文書（電子添文）の構造と記載要領

本ドキュメントは、日本における医療用医薬品の電子添文の公的な記載項目と、PMDA XMLの主なタグ対応・階層を整理したものです。タグ名や階層はPMDAのXSDと配布XMLで確認し、同名タグを使う項目は親の節を使って区別します。

---

## 1. 制度と公的根拠

### 1.1 法的根拠
- **医薬品医療機器等法（薬機法）第52条（添付文書等への記載事項）**:
  医薬品の製造販売業者は、用法、用量、その他使用及び取扱い上の必要な注意など、厚生労働省令で定める事項を公表・記載しなければならない。
- **令和3年（2021年）8月1日施行 薬機法改正**:
  - 医療用医薬品における**紙の添付文書の原則同梱廃止**。
  - 外箱等のGS1バーコード・2次元コードを通じて**PMDAのウェブサイト（電子添文）で最新情報を閲覧する運用が義務化**。

### 1.2 主管となる公式行政通知
1. **最新（現行通知）**:
   - **厚生労働省医薬・生活衛生局長通知**  
     **「医療用医薬品の電子化された添付文書の記載要領について」**  
     （令和3年6月11日 薬生発0611第1号 / 厚生労働省法令通し番号: `T210615I0010.pdf`）
2. **制度全面改正（新記載要領制定）**:
   - **厚生労働省医薬・生活衛生局長通知**  
     **「医療用医薬品の添付文書等の記載要領について」**  
     （平成29年6月8日 薬生発0608第1号）
     ※旧記載要領（平成9年通知）から約20年ぶりに全面改訂され、固定通し番号化や「原則禁忌」「慎重投与」の廃止が行われた。
3. **運用上の留意事項通知**:
   - **厚生労働省医薬・生活衛生局安全対策課長通知**  
     **「医療用医薬品の添付文書等の記載要領の留意事項について」**  
     （平成29年6月8日 薬生安発0608第1号、令和3年一部改正）

> [!NOTE]
> **※過去メモにあった `T210615I0030.pdf` との相違点について**  
> 厚生労働省が令和3年6月11日に一括発出した電子添文通知のうち、
> - `T210615I0010.pdf`（薬生発0611第1号）: **医療用医薬品**（全26項目）
> - `T210615I0020.pdf`（薬生発0611第5号）: **体外診断用医薬品**（全16項目）
> - `T210615I0030.pdf`（薬生発0611第9号）: **医療機器**（全17項目）  
> となっています。本プロジェクト（イグザレルト錠、イトリゾールカプセル等）で扱う医療用医薬品は、下記に示す**全26項目の体系**に従います。

---

## 2. 添付文書の全体構成

医療用医薬品の添付文書は、**【基本項目（ヘッダー部：ア～キ）】**と**【本体記載項目（1～26の大項目・中項目・小項目）】**で構成されます。

```
┌─────────────────────────────────────────────────────────────┐
│ 【基本項目（ヘッダー部：枠外・枠上）】                      │
│   ・作成又は改訂年月（版数、改訂記号）                      │
│   ・日本標準商品分類番号（87XXXX）                          │
│   ・承認番号、販売開始年月、国際誕生年月                    │
│   ・貯法、有効期間                                          │
│   ・薬効分類名、規制区分（劇薬・処方箋医薬品等）            │
│   ・販売名（一般名、識別コード等）                          │
├─────────────────────────────────────────────────────────────┤
│ 【本体記載項目（大項目 1 ～ 26）】                          │
│   1. 警告                                                   │
│   2. 禁忌（次の患者には投与しないこと）                     │
│   3. 組成・性状（3.1 組成 / 3.2 製剤の性状）                │
│   4. 効能又は効果                                           │
│   5. 効能又は効果に関連する注意                             │
│   6. 用法及び用量                                           │
│   7. 用法及び用量に関連する注意                             │
│   8. 重要な基本的注意                                       │
│   9. 特定の背景を有する患者に関する注意（9.1～9.8）         │
│   10. 相互作用（10.1 併用禁忌 / 10.2 併用注意）             │
│   11. 副作用（11.1 重大な副作用 / 11.2 その他の副作用）     │
│   12. 臨床検査結果に及ぼす影響                              │
│   13. 過量投与                                              │
│   14. 適用上の注意                                          │
│   15. その他の注意（15.1 臨床使用 / 15.2 非臨床試験）       │
│   16. 薬物動態（16.1～16.8）                                │
│   17. 臨床成績（17.1～17.3）                                │
│   18. 薬効薬理（18.1 作用機序）                             │
│   19. 有効成分に関する理化学的知見                          │
│   20. 取扱い上の注意                                        │
│   21. 承認条件                                              │
│   22. 包装                                                  │
│   23. 主要文献                                              │
│   24. 文献請求先及び問い合わせ先                            │
│   25. 保険給付上の注意                                      │
│   26. 製造販売業者等                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 基本項目（ヘッダー部：枠外・枠上事項）

添付文書の冒頭（または電子添文のヘッダーメタデータ）に配置される基本属性です。

| 記号 | 項目名 | 内容と記載要領 | PMDA XML対応タグ例 |
| :--- | :--- | :--- | :--- |
| **ア** | 作成又は改訂年月 | 作成年月、最新改訂年月、版数、改訂箇所を明記。<br>最新改訂部分には本文中に `*` マークが付与される。 | `<DateOfPreparationOrRevision>`<br>`<PreparationOrRevision>` |
| **イ** | 日本標準商品分類番号 | 総務省「日本標準商品分類」における医薬品コード（通常 `87` から始まる5桁または8桁）。 | `<Sccj>`<br>`<SccjNo>` |
| **ウ** | 承認番号、販売開始年月 | 医薬品製造販売承認番号、薬価収載年月、販売開始年月、国際誕生年月等。 | `<ApprovalEtc>`<br>`<ApprovalNo>`, `<StartingDateOfMarketing>` |
| **エ** | 貯法、有効期間 | 室温保存、気密容器、遮光、有効期間（3年など）。 | `<StorageMethod>`, `<ShelfLife>` |
| **オ** | 薬効分類名 | 薬効を表す一般的な名称（例: 持続性アンジオテンシンII受容体拮抗剤、抗凝固剤）。 | `<TherapeuticClassification>` |
| **カ** | 規制区分 | 「劇薬」「毒薬」「処方箋医薬品」「麻薬」「向精神薬」「生物由来製品」等の法的区分。 | `<RegulatoryClassification>` |
| **キ** | 販売名・一般的名称 | 承認された販売名（和名・欧名）、一般的名称（JAN・INN）、統一名称、識別コード。 | `<ApprovalBrandName>`, `<GenericName>`, `<BrandCode>` |

---

## 4. 本体記載項目（大項目 1～26 及び 中項目・小項目）

「第2 記載項目及び記載順序」に従い、**1〜26の固定番号**が付与されます。

> [!IMPORTANT]
> **通し番号（固定番号方式）の原則**:
> 該当する情報がない項目については項目自体を省略できますが、**項番を繰り上げてはならず「欠番」とします**。これにより、どの医薬品の添付文書でも「4は効能又は効果」「6は用法及び用量」「10は相互作用」「11は副作用」のように位置関係が一定に保たれます。

> **XMLタグとの対応**: すべての項目に一意な専用タグがあるわけではありません。たとえば16.8・17.3は親節に応じて同じ `<OtherInformation>` を解釈します。13の本文中に「症状」「処置」などの見出しがあっても、現行の記載要領では13.1・13.2という固定番号ではないため、本文の見出しとして保持します。18の `<OtherInformation>` も番号を推測せず18に紐付けます。

### 項目一覧とPMDA XMLタグ・記載要件

| 項番 | 項目名 | 英語表記 | PMDA XML タグ名 | 記載内容と規定 |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **警告** | Warnings | `<Warnings>` | 致死的な副作用、不可逆的な障害など、極めて重大な副作用・事故を防止するために投与前に必ず知っておくべき事項（赤枠等で強調）。 |
| **2** | **禁忌** | Contraindications | `<ContraIndications>` | **「次の患者には投与しないこと」**<br>投与により重大な健康被害が生じるため、絶対に使用してはならない対象（過敏症既往歴、重篤な臓器不全、妊婦等）。 |
| **3** | **組成・性状** | Composition and Property | `<CompositionAndProperty>` | 製剤の物理的・化学的属性。 |
| 3.1 | 組成 | Composition | `<Composition>` | 有効成分の名称・含量、添加剤（賦形剤、着色剤等）。 |
| 3.2 | 製剤の性状 | Property | `<Property>` | 剤形、外形（色、形状、直径、厚さ、質量）、識別コード（刻印、印刷）、pH、浸透圧比。 |
| **4** | **効能又は効果** | Indications or Efficacy | `<IndicationsOrEfficacy>` | 薬事承認された適応症・疾患名・病態。 |
| **5** | **効能又は効果に関連する注意** | Precautions Related to Indications | `<EfficacyRelatedPrecautions>` | 適応患者の確定診断基準、除外基準、投与対象の限定条件、他の治療法との優先順位。 |
| **6** | **用法及び用量** | Dosage and Administration | `<InfoDoseAdmin>` | 承認された用量、投与回数、投与経路、投与間隔、溶解液、調製方法。 |
| **7** | **用法及び用量に関連する注意** | Precautions Related to Dosage | `<InfoPrecautionsDosage>` | 漸増・漸減法、休薬・再開基準、腎・肝機能等に応じた用量調節、食事との関係、最大投与期間。 |
| **8** | **重要な基本的注意** | Important Precautions | `<ImportantPrecautions>` | 重大な副作用や事故を防止するための定期的検査（血液・肝腎機能・心電図等）、患者観察、車の運転等の危険作業の制限。 |
| **9** | **特定の背景を有する患者に関する注意** | Use in Specific Populations | `<UseInSpecificPopulations>` | 旧「慎重投与」を廃止し、患者集団ごとに情報と注意を集約した大項目。 |
| 9.1 | 合併症・既往歴等のある患者 | Patients with Complications etc. | `<UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc>` | 特定の合併症、既往歴、素因を有する患者に対する注意。 |
| 9.2 | 腎機能障害患者 | Patients with Renal Impairment | `<PatientsWithRenalImpairment>` | 腎不全、透析患者、eGFR低下患者等に対する注意・用量考慮。 |
| 9.3 | 肝機能障害患者 | Patients with Hepatic Impairment | `<PatientsWithHepaticImpairment>` | 肝硬変、肝炎、Child-Pugh分類に応じた注意。 |
| 9.4 | 生殖能を有する者 | Males and Females of Reproductive Potential | `<MalesAndFemalesOfReproductivePotential>` | 妊娠可能な女性、パートナーが妊娠する可能性のある男性における避妊の必要性等。 |
| 9.5 | 妊婦 | Use in Pregnant Women | `<UseInPregnant>` | 妊婦・妊娠の可能性がある女性への投与可否、有益性投与基準、動物実験データ。 |
| 9.6 | 授乳婦 | Use in Nursing Women | `<UseInNursing>` | 乳汁移行性、授乳継続か中止かの指示、乳児への影響。 |
| 9.7 | 小児等 | Pediatric Use | `<PediatricUse>` | 低出生体重児、新生児、乳児、幼児、小児に対する安全性確立状況、臨床試験データ。 |
| 9.8 | 高齢者 | Use in the Elderly | `<UseInTheElderly>` | 生理機能（腎・肝機能）低下を考慮した投与法、低用量からの開始等の注意。 |
| **10** | **相互作用** | Interactions | `<Interactions>` | 併用薬、飲食物、サプリメント等との併用に関する情報。 |
| 10.1 | 併用禁忌 | Contraindicated Combinations | `<ContraIndicatedCombinations>` | **「併用しないこと」**<br>重篤な相互作用により致死的または重大な健康被害が生じる組み合わせ。 |
| 10.2 | 併用注意 | Precautions for Combinations | `<PrecautionsForCombinations>` | **「併用に注意すること」**<br>臨床症状・措置方法、作用機序・危険因子を明記した注意。 |
| **11** | **副作用** | Adverse Reactions | `<AdverseEvents>` | 本剤投与により生じる可能性のある有害事象・有害反応。 |
| 11.1 | 重大な副作用 | Serious Adverse Reactions | `<SeriousAdverseEvents>` | 早期発見・初期対応が必要な重篤な副作用（ショック、間質性肺炎、肝機能障害等）と発現時処置。 |
| 11.2 | その他の副作用 | Other Adverse Reactions | `<OtherAdverseEvents>` | 器官別大分類（SOC）および発現頻度（5%以上、0.1〜5%未満、0.1%未満、頻度不明等）のマトリクス。 |
| **12** | **臨床検査結果に及ぼす影響** | Influence on Laboratory Values | `<InfluenceOnLaboratoryValues>`<br>別名 `<EffectsOnLaboratoryTests>` も受理 | 薬剤そのものの影響で見かけ上の検査値変動（検査薬への干渉、偽陽性・偽陰性）が生じる場合。 |
| **13** | **過量投与** | Overdosage | `<OverDosage>` | 推奨用量を超えて過量投与された場合の情報。 |
| **14** | **適用上の注意** | Precautions for Application | `<PrecautionsForApplication>` | 調剤時、薬剤交付時（PTPシート誤飲防止、吸湿防止等）、薬剤投与時（注射速度、配合変化等）。 |
| **15** | **その他の注意** | Other Precautions | `<OtherPrecautions>` | 1〜14に該当しないが留意すべき情報。 |
| 15.1 | 臨床使用に基づく情報 | Information Based on Clinical Use | `<InformationBasedOnClinicalUse>` | 市販後や海外疫学調査における二次発がん、心血管イベントなどの報告。 |
| 15.2 | 非臨床試験に基づく情報 | Information Based on Non-Clinical Use | `<InformationBasedOnNonClinicalUse>` | 変異原性試験、がん原性試験、生殖発生毒性試験などの動物実験所見。 |
| **16** | **薬物動態** | Pharmacokinetics | `<Pharmacokinetics>` | 体内動態パラメータ。 |
| 16.1 | 血中濃度 | Blood Level | `<BloodLevel>` | 単回投与、反復投与時のCmax、AUC、Tmax、消失半減期（T1/2）、生物学的同等性試験等。 |
| 16.2 | 吸収 | Absorption | `<Absorption>` | バイオアベイラビリティ、食事の影響（食後・空腹時）。 |
| 16.3 | 分布 | Distribution | `<Distribution>` | 組織移行性、血漿蛋白結合率、分布容積。 |
| 16.4 | 代謝 | Metabolism | `<Metabolism>` | 代謝経路、関与する代謝酵素（CYP3A4等）、主代謝物、活性の有無。 |
| 16.5 | 排泄 | Excretion | `<Excretion>` | 尿中排泄率、糞中排泄率、全身クリアランス。 |
| 16.6 | 特定の背景を有する患者 | Specific Populations | `<SpecificPopulation>` | 腎機能障害者、肝機能障害者、高齢者等におけるPKパラメータ比較。 |
| 16.7 | 薬物相互作用 | Drug-Drug Interactions | `<DrugAndDrugInteractions>` | in vitro 代謝阻害/誘導試験、併用時のAUC・Cmax変化率等の臨床相互作用データ。 |
| 16.8 | その他 | Other Information | 親が `<Pharmacokinetics>` の `<OtherInformation>` | トランスポーター（P-gp等）への関与など。 |
| **17** | **臨床成績** | Clinical Studies | `<ResultsOfClinicalTrials>` | 承認根拠となった臨床試験結果。 |
| 17.1 | 有効性及び安全性に関する試験 | Efficacy and Safety Trials | `<EfficacyAndSafety>` | 第III相検証的試験、国際共同治験における主要評価項目、奏効率、全生存期間等の成績。 |
| 17.2 | 製造販売後調査等 | Post-Marketing Surveillance | `<PostMarketingSurveillance>` | 使用成績調査、特定使用成績調査などの市販後データ。 |
| 17.3 | その他 | Other Studies | 親が `<ResultsOfClinicalTrials>` の `<OtherInformation>` | 臨床薬理試験、用量設定試験等。 |
| **18** | **薬効薬理** | Pharmacology | `<EfficacyPharmacology>` | 薬理学的作用機序および薬理活性。 |
| 18.1 | 作用機序 | Mechanism of Action | `<MechanismOfAction>` | 分子標的、受容体結合、酵素阻害などの詳細な機序。 |
| **19** | **有効成分に関する理化学的知見** | Physicochemical Properties | `<PhyschemOfActIngredients>` | 有効成分の科学的プロファイル。<br>一般的名称、化学名、分子式、分子量、構造式、性状（融点、溶解度、解離定数、分配係数等）。 |
| **20** | **取扱い上の注意** | Precautions for Handling | `<PrecautionsForHandling>` | 開封後の保存（吸湿・遮光）、シリンジの取扱い、廃棄方法など。 |
| **21** | **承認条件** | Conditions of Approval | `<ConditionsOfApproval>` | 承認時に課された条件（医薬品リスク管理計画［RMP］の確実な実施、全例調査義務など）。 |
| **22** | **包装** | Packaging | `<Package>` | PTPシート（100錠等）、バラ包装、バイアル等の包装規格・単位。 |
| **23** | **主要文献** | Main Literature | `<MainLiterature>` | 本文中に引用された社内資料、公表論文、国際学会発表等の文献リスト。 |
| **24** | **文献請求先及び問い合わせ先** | Addressee of Literature Requests | `<AddresseeOfLiteratureRequest>` | 医療関係者向けのくすり相談窓口、学術情報部の名称、所在地、電話番号、受付時間、WebサイトURL。 |
| **25** | **保険給付上の注意** | Precautions for Insurance Benefits | `<AttentionOfInsurance>`<br>別名 `<PrecautionsForInsuranceCoverage>` も受理 | 保険給付上の留意点等（該当がある場合のみ）。 |
| **26** | **製造販売業者等** | Marketing Authorization Holder | `<NameAddressManufact>` | 製造販売業者、販売元等の情報。 |
`<Manufacturer>` 等の製造販売業者情報は26の内容です。現行記載要領に26.1・26.2の固定小項目番号はないため、パーサーでは26として扱います。

---

## 5. 「使用上の注意」の範囲定義

日本の薬事制度において、医療従事者が日常的に参照する「**使用上の注意**」は、上記のうち以下の範囲を指します。

- **使用上の注意の対象範囲**:
  - **「1. 警告」から「15. その他の注意」まで**
  - **ただし、「3. 組成・性状」「4. 効能又は効果」「6. 用法及び用量」を除く。**
  - （すなわち、1, 2, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15 の各項目が該当する）

---

## 6. PMDA 電子添文 XMLの技術仕様と構造

PMDAで公表・配信されている電子添文XMLは、以下の仕様に基づき作成されています。

### 6.1 名前空間とルート要素
- **XML Namespace**:  
  `http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0`
- **ルート要素**:  
  `<PackIns>`

### 6.2 主要タグの階層構造
```
<PackIns xmlns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0">
  <!-- 基本項目 -->
  <PackageInsertNo>...</PackageInsertNo>
  <CompanyIdentifier>...</CompanyIdentifier>
  <DateOfPreparationOrRevision>
    <PreparationOrRevision id="今回">...</PreparationOrRevision>
    <PreparationOrRevision id="前回">...</PreparationOrRevision>
  </DateOfPreparationOrRevision>
  <Sccj><SccjNo>...</SccjNo></Sccj>
  <TherapeuticClassification><Detail>...</Detail></TherapeuticClassification>
  <ApprovalEtc><DetailBrandName id="BRD_Drug1">...</DetailBrandName></ApprovalEtc>
  <GenericName><Detail>...</Detail></GenericName>

  <!-- 本体項目（1〜26） -->
  <Warnings heading="fixing" id="HDR_Warnings">...</Warnings>
  <ContraIndications heading="fixing" id="HDR_ContraIndications">...</ContraIndications>
  <CompositionAndProperty heading="fixing" id="HDR_CompositionAndProperty">
    <Composition heading="fixing" id="HDR_Composition">...</Composition>
    <Property heading="fixing" id="HDR_Property">...</Property>
  </CompositionAndProperty>
  <IndicationsOrEfficacy heading="fixing" id="HDR_IndicationsOrEfficacy">...</IndicationsOrEfficacy>
  <EfficacyRelatedPrecautions heading="fixing" id="HDR_EfficacyRelatedPrecautions">...</EfficacyRelatedPrecautions>
  <InfoDoseAdmin heading="fixing" id="HDR_InfoDoseAdmin">...</InfoDoseAdmin>
  <InfoPrecautionsDosage heading="fixing" id="HDR_InfoPrecautionsDosage">...</InfoPrecautionsDosage>
  <ImportantPrecautions heading="fixing" id="HDR_ImportantPrecautions">...</ImportantPrecautions>
  <UseInSpecificPopulations heading="fixing" id="HDR_UseInSpecificPopulations">
    <UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc heading="fixing">...</UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc>
    <PatientsWithRenalImpairment heading="fixing">...</PatientsWithRenalImpairment>
    <PatientsWithHepaticImpairment heading="fixing">...</PatientsWithHepaticImpairment>
    <MalesAndFemalesOfReproductivePotential heading="fixing">...</MalesAndFemalesOfReproductivePotential>
    <UseInPregnant heading="fixing">...</UseInPregnant>
    <UseInNursing heading="fixing">...</UseInNursing>
    <PediatricUse heading="fixing">...</PediatricUse>
    <UseInTheElderly heading="fixing">...</UseInTheElderly>
  </UseInSpecificPopulations>
  <Interactions heading="fixing" id="HDR_Interactions">
    <ContraIndicatedCombinations heading="fixing">
      <Drug>
        <DrugName>...</DrugName>
        <ClinSymptomsAndMeasures>...</ClinSymptomsAndMeasures>
        <MechanismAndRiskFactors>...</MechanismAndRiskFactors>
      </Drug>
    </ContraIndicatedCombinations>
    <PrecautionsForCombinations heading="fixing">...</PrecautionsForCombinations>
  </Interactions>
  <AdverseEvents heading="fixing" id="HDR_AdverseEvents">
    <SeriousAdverseEvents heading="fixing">...</SeriousAdverseEvents>
    <OtherAdverseEvents heading="fixing">
      <AdverseReactionDescription>
        <Category>消化器</Category>
        <Frequency>5%以上</Frequency>
        <Content>悪心、嘔吐</Content>
      </AdverseReactionDescription>
    </OtherAdverseEvents>
  </AdverseEvents>
  <InfluenceOnLaboratoryValues heading="fixing" id="HDR_InfluenceOnLaboratoryValues">...</InfluenceOnLaboratoryValues>
  <OverDosage heading="fixing" id="HDR_OverDosage">
    <OrderedList>
      <Item><Header><Lang>症状</Lang></Header><Detail><Lang>...</Lang></Detail></Item>
      <Item><Header><Lang>処置</Lang></Header><Detail><Lang>...</Lang></Detail></Item>
    </OrderedList>
  </OverDosage>
  <PrecautionsForApplication heading="fixing" id="HDR_PrecautionsForApplication">...</PrecautionsForApplication>
  <OtherPrecautions heading="fixing" id="HDR_OtherPrecautions">
    <InformationBasedOnClinicalUse heading="fixing">...</InformationBasedOnClinicalUse>
    <InformationBasedOnNonClinicalUse heading="fixing">...</InformationBasedOnNonClinicalUse>
  </OtherPrecautions>
  <Pharmacokinetics heading="fixing" id="HDR_Pharmacokinetics">
    <BloodLevel heading="fixing">...</BloodLevel>
    <Absorption heading="fixing">...</Absorption>
    <Distribution heading="fixing">...</Distribution>
    <Metabolism heading="fixing">...</Metabolism>
    <Excretion heading="fixing">...</Excretion>
    <SpecificPopulation heading="fixing">...</SpecificPopulation>
    <DrugAndDrugInteractions heading="fixing">...</DrugAndDrugInteractions>
    <OtherInformation heading="fixing">...</OtherInformation>
  </Pharmacokinetics>
  <ResultsOfClinicalTrials heading="fixing" id="HDR_ResultsOfClinicalTrials">
    <EfficacyAndSafety heading="fixing">...</EfficacyAndSafety>
    <PostMarketingSurveillance heading="fixing">...</PostMarketingSurveillance>
    <OtherInformation heading="fixing">...</OtherInformation>
  </ResultsOfClinicalTrials>
  <EfficacyPharmacology heading="fixing" id="HDR_EfficacyPharmacology">
    <MechanismOfAction heading="fixing">...</MechanismOfAction>
    <OtherInformation heading="fixing">...</OtherInformation>
  </EfficacyPharmacology>
  <PhyschemOfActIngredients heading="fixing" id="HDR_PhyschemOfActIngredients">...</PhyschemOfActIngredients>
  <PrecautionsForHandling heading="fixing" id="HDR_PrecautionsForHandling">...</PrecautionsForHandling>
  <ConditionsOfApproval heading="fixing" id="HDR_ConditionsOfApproval">...</ConditionsOfApproval>
  <Package heading="fixing" id="HDR_Package">...</Package>
  <MainLiterature heading="fixing" id="HDR_MainLiterature">
    <Reference id="DOC_01">...</Reference>
  </MainLiterature>
  <AddresseeOfLiteratureRequest heading="fixing" id="HDR_AddresseeOfLiteratureRequest">
    <AddresseeInfo>...</AddresseeInfo>
  </AddresseeOfLiteratureRequest>
  <AttentionOfInsurance heading="fixing" id="HDR_AttentionOfInsurance">...</AttentionOfInsurance>
  <NameAddressManufact heading="fixing" id="HDR_NameAddressManufact">
    <Manufacturer>...</Manufacturer>
  </NameAddressManufact>
</PackIns>
```

### 6.3 パーサーの節番号対応

`tools/structure_pmda_xml.py` では、固定番号をタグ名から直接付与する項目と、親節とタグ名の組み合わせで付与する項目を分けて定義しています。欠番は詰めず、各項目に定めた番号をそのまま出力します。12・25は配布資料に見られるタグ名の別表記も同じ番号として扱います。13の「症状」「処置」などの見出しと18配下の自由項目は原文のまま保持し、記載要領にない番号は付与しません。

PMDAはXML利用にXSDが必要と案内しています。現時点のパーサーは上記の節番号マッピングと原文保持・本文網羅性を検証しますが、XSDによる全XML妥当性検証は行いません。そのため、ここでいう事前対応は医療用医薬品の固定項目と既知のタグ表記を対象にしたものです。旧様式SGMLや医療機器・体外診断用医薬品XMLは別対応です。

---

## 7. 医療機器・体外診断薬・一般用医薬品との比較

日本の薬機法下では、製品カテゴリーごとに添付文書の記載要領が個別に定められています。

| カテゴリ | 根拠通知番号（令和3年改正） | 大項目数 | 主な構成と特徴 |
| :--- | :--- | :---: | :--- |
| **医療用医薬品**<br>*(本プロジェクト対象)* | 薬生発0611第1号<br>（旧: 薬生発0608第1号） | **26項目** | 1. 警告 〜 26. 製造販売業者等。<br>医師・薬剤師向けの高度な臨床薬理・薬物動態・相互作用・副作用データを固定番号で厳密に構造化。 |
| **医療機器**<br>*(pmda.md参照PDF)* | 薬生発0611第9号<br>（通知通し: `T210615I0030.pdf`） | **17項目** | （1）作成又は改訂年月、（2）承認番号等、（3）類別及び一般的名称等、（4）販売名、（5）警告、（6）禁忌・禁止、（7）形状・構造及び原理等、（8）使用目的又は効果、（9）使用方法等、（10）使用上の注意、（11）臨床成績、（12）保管方法及び有効期間等、（13）取扱い上の注意、（14）保守・点検に係る事項、（15）承認条件、（16）主要文献及び文献請求先、（17）製造販売業者及び製造業者の氏名又は名称等 |
| **体外診断用医薬品 (IVD)** | 薬生発0611第5号<br>（通知通し: `T210615I0020.pdf`） | **16項目** | 測定原理、試薬の構成、操作方法、判定法、キャリブレーション、性能（感度、特異度等）、臨床的意義等。 |
| **一般用医薬品 (OTC)** | 平成23年薬食発0330第1号等 | セクション制 | 一般生活者向け。「してはいけないこと」「相談すること」「効能・効果」「用法・用量」「成分・分量」「保管及び取扱い上の注意」など平易な表現。 |

---

## 8. 公開されている公式情報源リンク

1. **厚生労働省（法令・通知等データベース）**:
   - [医療用医薬品の電子化された添付文書の記載要領について（薬生発0611第1号: T210615I0010.pdf）](https://www.mhlw.go.jp/hourei/doc/tsuchi/T210615I0010.pdf)
   - [医療機器の電子化された添付文書の記載要領について（薬生発0611第9号: T210615I0030.pdf）](https://www.mhlw.go.jp/hourei/doc/tsuchi/T210615I0030.pdf)
   - [医療用医薬品の添付文書等の記載要領について（新記載要領制定: 薬生発0608第1号）](https://www.mhlw.go.jp/hourei/doc/tsuchi/T170613I0010.pdf)
2. **PMDA（独立行政法人 医薬品医療機器総合機構）**:
   - [PMDA 医療用医薬品 添付文書情報検索ポータル](https://www.pmda.go.jp/PmdaSearch/iyakuSearch/)
   - [添付文書情報のダウンロードについて（XMLとXSDの案内）](https://www.info.pmda.go.jp/psearch/html/menu_tenpu_download.pdf)
   - [電子添文（XML/SGML）作成関連情報・IKWサイト](https://www.pmda.go.jp/)
3. **日本製薬工業協会（JPMA）**:
   - [医療用医薬品添付文書情報の電子ファイル作成の手引き ―XML形式―](https://www.jpma.or.jp/information/evaluation/results/allotment/lofurc000000c744-att/xml_guidance.pdf)
