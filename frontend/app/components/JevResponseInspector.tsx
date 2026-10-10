"use client";

import { useState } from "react";

export interface JevAnswer {
  type?: string;
  choice?: string;
  confidence?: number;
  probabilities?: Record<string, number>;
}

export interface JevResponseData {
  model?: string;
  request_id?: string;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    [key: string]: unknown;
  };
  answers?: Record<string, JevAnswer>;
  qualifying_intents?: string[];
  error?: string;
  [key: string]: unknown;
}

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

function CopyJsonButton({ data }: { data: unknown }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      style={{
        padding: "2px 8px",
        fontSize: "11px",
        borderRadius: "4px",
        border: "1px solid var(--border)",
        background: copied ? "#065f46" : "#262626",
        color: copied ? "#34d399" : "#d4d4d4",
        cursor: "pointer",
        transition: "all 0.15s ease",
      }}
    >
      {copied ? "✓ コピー完了" : "JSONをコピー"}
    </button>
  );
}

export function JevResponseInspector({ response }: { response: JevResponseData }) {
  const [activeTab, setActiveTab] = useState<"summary" | "raw">("summary");
  const [showAllProbabilities, setShowAllProbabilities] = useState(false);

  const intentAnswer = response.answers?.intent;
  const choice = intentAnswer?.choice;
  const confidence = intentAnswer?.confidence;
  const probabilities = intentAnswer?.probabilities;
  const meta = choice ? JEV_INTENT_META[choice] : null;

  const allSortedProbabilities = probabilities
    ? Object.entries(probabilities).sort(([, a], [, b]) => b - a)
    : [];

  const displayedProbabilities = showAllProbabilities
    ? allSortedProbabilities
    : allSortedProbabilities.slice(0, 8);

  return (
    <details className="jev-inspector-details">
      <summary className="jev-inspector-summary">
        <div
          style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}
        >
          <span>⚡ Jev レスポンス確認</span>
          {choice && (
            <span className="jev-intent-badge">
              {meta ? `${meta.label} (${choice})` : choice}
            </span>
          )}
          {response.qualifying_intents && response.qualifying_intents.length > 1 && (
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: "#67e8f9",
                background: "rgba(6, 182, 212, 0.18)",
                border: "1px solid rgba(6, 182, 212, 0.35)",
                borderRadius: "4px",
                padding: "2px 6px",
              }}
            >
              マルチ取得:{" "}
              {response.qualifying_intents
                .map((k) => JEV_INTENT_META[k]?.label || k)
                .join(" ＋ ")}
            </span>
          )}
          {confidence !== undefined && (
            <span className="jev-confidence-pill">
              確信度: {Math.round(confidence * 100)}%
            </span>
          )}
          {response.model && (
            <span style={{ fontSize: "11px", color: "var(--muted)" }}>
              {response.model}
            </span>
          )}
          {response.error && (
            <span style={{ fontSize: "11px", color: "#f87171" }}>⚠️ エラー</span>
          )}
        </div>
        <span style={{ fontSize: "11px", color: "var(--muted)" }}>クリックで展開</span>
      </summary>

      <div className="jev-inspector-body">
        {response.error && (
          <div
            style={{
              color: "#f87171",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              padding: "8px",
              borderRadius: "6px",
            }}
          >
            Jevエラー: {response.error}
          </div>
        )}

        <div
          className="jev-tab-nav"
          role="tablist"
          aria-label="Jevインスペクター表示切替"
        >
          <button
            type="button"
            role="tab"
            id="jev-tab-summary"
            aria-selected={activeTab === "summary"}
            aria-controls="jev-panel-summary"
            className={`jev-tab-item ${activeTab === "summary" ? "active" : ""}`}
            onClick={() => setActiveTab("summary")}
          >
            <span>📊 判定サマリー & 確率分布</span>
          </button>
          <button
            type="button"
            role="tab"
            id="jev-tab-raw"
            aria-selected={activeTab === "raw"}
            aria-controls="jev-panel-raw"
            className={`jev-tab-item ${activeTab === "raw" ? "active" : ""}`}
            onClick={() => setActiveTab("raw")}
          >
            <span>📄 生レスポンス (JSON)</span>
          </button>
        </div>

        {activeTab === "summary" && (
          <div
            id="jev-panel-summary"
            role="tabpanel"
            aria-labelledby="jev-tab-summary"
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            {choice && (
              <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                <div style={{ color: "var(--muted)", fontSize: "11px" }}>
                  判定項目 (Intent):
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                  <span style={{ fontWeight: 600, color: "#e9d5ff", fontSize: "13px" }}>
                    {meta?.label || choice}
                  </span>
                  <span style={{ color: "#c084fc", fontSize: "11px" }}>({choice})</span>
                  {confidence !== undefined && confidence >= 0.2 && (
                    <span
                      style={{
                        fontSize: "10px",
                        color: "#c084fc",
                        background: "rgba(168, 85, 247, 0.18)",
                        border: "1px solid rgba(168, 85, 247, 0.4)",
                        borderRadius: "3px",
                        padding: "1px 5px",
                        fontWeight: 600,
                      }}
                    >
                      [対象]
                    </span>
                  )}
                </div>
                {meta?.desc && (
                  <div style={{ color: "var(--muted)", fontSize: "11px" }}>
                    {meta.desc}
                  </div>
                )}
              </div>
            )}

            {confidence !== undefined && (
              <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "11px",
                  }}
                >
                  <span style={{ color: "var(--muted)" }}>確信度 (Confidence):</span>
                  <span style={{ fontWeight: 600, color: "#34d399" }}>
                    {(confidence * 100).toFixed(1)}% ({confidence.toFixed(2)})
                  </span>
                </div>
                <div className="jev-prob-bar-container">
                  <div
                    className="jev-prob-bar"
                    style={{ width: `${Math.min(Math.max(confidence * 100, 0), 100)}%` }}
                  />
                </div>
              </div>
            )}

            {response.qualifying_intents && response.qualifying_intents.length > 1 && (
              <div
                style={{
                  padding: "8px 10px",
                  borderRadius: "6px",
                  background: "rgba(6, 182, 212, 0.08)",
                  border: "1px solid rgba(6, 182, 212, 0.25)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: "#67e8f9",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <span>⚡ マルチセクション取得（閾値20%以上）</span>
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                    {response.qualifying_intents.length}項目を統合取得
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "#cbd5e1", lineHeight: 1.4 }}>
                  確率20%以上の複数セクションを検出し、添付文書の該当箇所を網羅して検索・引用しました:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {response.qualifying_intents.map((intentKey) => {
                    const prob = probabilities?.[intentKey];
                    const probPct =
                      prob !== undefined ? `${(prob * 100).toFixed(1)}%` : null;
                    const itemMeta = JEV_INTENT_META[intentKey];
                    return (
                      <div
                        key={intentKey}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "3px 8px",
                          borderRadius: "4px",
                          background: "rgba(6, 182, 212, 0.15)",
                          border: "1px solid rgba(6, 182, 212, 0.3)",
                          color: "#e0f2fe",
                          fontSize: "11px",
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>
                          {itemMeta?.label || intentKey}
                        </span>
                        {probPct && (
                          <span style={{ color: "#38bdf8", fontWeight: 600 }}>
                            {probPct}
                          </span>
                        )}
                        <span
                          style={{
                            fontSize: "10px",
                            color: "#67e8f9",
                            background: "rgba(6, 182, 212, 0.2)",
                            borderRadius: "3px",
                            padding: "0 3px",
                          }}
                        >
                          [対象]
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {allSortedProbabilities.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    color: "var(--muted)",
                    fontSize: "11px",
                    fontWeight: 500,
                  }}
                >
                  <span>
                    候補項目と確率分布 (
                    {showAllProbabilities
                      ? `全${allSortedProbabilities.length}項目`
                      : `上位${displayedProbabilities.length}項目`}
                    ):
                  </span>
                  {allSortedProbabilities.length > 8 && (
                    <button
                      type="button"
                      onClick={() => setShowAllProbabilities((prev) => !prev)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "#93c5fd",
                        fontSize: "11px",
                        cursor: "pointer",
                        textDecoration: "underline",
                        padding: 0,
                      }}
                    >
                      {showAllProbabilities
                        ? "上位8件に戻す"
                        : `全${allSortedProbabilities.length}件を表示`}
                    </button>
                  )}
                </div>
                {displayedProbabilities.map(([key, prob]) => {
                  const probPct = (prob * 100).toFixed(1);
                  const itemMeta = JEV_INTENT_META[key];
                  const isWinner = key === choice;
                  const isQualifying =
                    (response.qualifying_intents?.includes(key) ?? false) || prob >= 0.2;
                  return (
                    <div key={key} className="jev-prob-row">
                      <span
                        style={{
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          color: isWinner
                            ? "#e9d5ff"
                            : isQualifying
                              ? "#67e8f9"
                              : "#cbd5e1",
                          fontWeight: isWinner || isQualifying ? 600 : 400,
                        }}
                        title={itemMeta?.label || key}
                      >
                        {itemMeta?.label || key}
                        {isQualifying && (
                          <span
                            style={{
                              marginLeft: "6px",
                              fontSize: "10px",
                              color: isWinner ? "#c084fc" : "#38bdf8",
                              background: isWinner
                                ? "rgba(168, 85, 247, 0.18)"
                                : "rgba(6, 182, 212, 0.18)",
                              border: isWinner
                                ? "1px solid rgba(168, 85, 247, 0.4)"
                                : "1px solid rgba(6, 182, 212, 0.4)",
                              borderRadius: "3px",
                              padding: "1px 4px",
                              fontWeight: 600,
                            }}
                          >
                            [対象]
                          </span>
                        )}
                      </span>
                      <div className="jev-prob-bar-container">
                        <div
                          className="jev-prob-bar"
                          style={{
                            width: `${Math.min(Math.max(prob * 100, 0), 100)}%`,
                            background: isWinner
                              ? "linear-gradient(90deg, #a855f7, #38bdf8)"
                              : isQualifying
                                ? "linear-gradient(90deg, #06b6d4, #38bdf8)"
                                : "rgba(255, 255, 255, 0.25)",
                          }}
                        />
                      </div>
                      <span
                        style={{
                          textAlign: "right",
                          color: isWinner
                            ? "#34d399"
                            : isQualifying
                              ? "#38bdf8"
                              : "var(--muted)",
                          fontWeight: isWinner || isQualifying ? 600 : 400,
                        }}
                      >
                        {probPct}%
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            <div
              className="jev-meta-row"
              style={{ paddingTop: "6px", borderTop: "1px dashed var(--border)" }}
            >
              {response.model && <div>モデル: {response.model}</div>}
              {response.request_id && <div>リクエストID: {response.request_id}</div>}
              {response.usage && (
                <div>
                  トークン: 入力 {response.usage.input_tokens ?? 0} / 出力{" "}
                  {response.usage.output_tokens ?? 0}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "raw" && (
          <div
            id="jev-panel-raw"
            role="tabpanel"
            aria-labelledby="jev-tab-raw"
            className="jev-raw-json-container"
          >
            <div className="jev-raw-json-header">
              <span>Jev API 生レスポンス (JSON)</span>
              <CopyJsonButton data={response} />
            </div>
            <pre className="jev-raw-json-code">
              <code>{JSON.stringify(response, null, 2)}</code>
            </pre>
          </div>
        )}
      </div>
    </details>
  );
}
