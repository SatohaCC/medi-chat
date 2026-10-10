"use client";

import { useState } from "react";
import { formatRevision } from "../lib/markdown";
import type { RetrievalStatus, SourceItem } from "../types/chat";
import { JEV_INTENT_META, type JevResponseData } from "./JevResponseInspector";
import { SourceEvidenceContent } from "./SourceEvidenceContent";

interface SourceEvidencePanelProps {
  sources: SourceItem[];
  retrievalStatus?: RetrievalStatus;
  jevResponse?: JevResponseData | null;
}

export function SourceEvidencePanel({
  sources,
  retrievalStatus,
  jevResponse,
}: SourceEvidencePanelProps) {
  const [selectedSection, setSelectedSection] = useState<string>("all");

  const logicCount = sources.filter((s) => s.retrieved_by?.includes("logic")).length;
  const jevCount = sources.filter((s) => s.retrieved_by?.includes("jev")).length;
  const keywordCount = sources.filter((s) => s.retrieved_by?.includes("keyword")).length;
  const totalCount = sources.length;

  const countSummary =
    keywordCount > 0
      ? `ロジック：${logicCount}件、Jev：${jevCount}件、キーワード：${keywordCount}件、合計：${totalCount}件`
      : `ロジック：${logicCount}件、Jev：${jevCount}件、合計：${totalCount}件`;

  // Extract unique sections in original sorted order
  const sectionCodesInOrder: string[] = [];
  const sectionMap = new Map<string, { code: string; title: string; count: number }>();
  for (const s of sources) {
    const code = s.section?.code || "other";
    const title = s.section?.title || "";
    const existing = sectionMap.get(code);
    if (existing) {
      existing.count += 1;
    } else {
      sectionCodesInOrder.push(code);
      sectionMap.set(code, { code, title, count: 1 });
    }
  }
  const sectionGroups = sectionCodesInOrder
    .map((code) => sectionMap.get(code))
    .filter((g): g is { code: string; title: string; count: number } => g !== undefined);

  const displayedSources =
    selectedSection === "all"
      ? sources
      : sources.filter((s) => (s.section?.code || "other") === selectedSection);

  return (
    <aside className="source-panel" aria-label="添付文書の根拠引用">
      <details
        open
        className="source-panel-details"
        style={{
          marginTop: "0",
          padding: "8px 10px",
          background: "rgba(0, 0, 0, 0.3)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          fontSize: "12px",
        }}
      >
        <summary
          style={{
            cursor: "pointer",
            fontWeight: 600,
            color: "#60a5fa",
            outline: "none",
            marginBottom: "6px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            flexWrap: "wrap",
          }}
        >
          <span>
            📄{" "}
            {retrievalStatus === "complete"
              ? `統合根拠（${countSummary}）`
              : retrievalStatus === "jev_searching"
                ? `ロジック検索根拠（ロジック：${totalCount}件、Jev：取得中...）`
                : `ロジック検索根拠（${totalCount}件）`}
          </span>
          {retrievalStatus === "jev_searching" && (
            <span
              style={{
                fontSize: "11px",
                color: "#fbbf24",
                fontWeight: 500,
              }}
            >
              ⚡ Jev判定と統合中...
            </span>
          )}
          {retrievalStatus === "complete" && (
            <span
              style={{
                fontSize: "11px",
                color: "#34d399",
                fontWeight: 500,
              }}
            >
              ✓ Jev統合完了
            </span>
          )}
          {jevResponse?.answers?.intent?.choice && (
            <span
              style={{
                fontSize: "11px",
                color:
                  jevResponse.qualifying_intents &&
                  jevResponse.qualifying_intents.length > 1
                    ? "#67e8f9"
                    : "#c084fc",
                background:
                  jevResponse.qualifying_intents &&
                  jevResponse.qualifying_intents.length > 1
                    ? "rgba(6, 182, 212, 0.15)"
                    : "rgba(168, 85, 247, 0.15)",
                border:
                  jevResponse.qualifying_intents &&
                  jevResponse.qualifying_intents.length > 1
                    ? "1px solid rgba(6, 182, 212, 0.35)"
                    : "1px solid rgba(168, 85, 247, 0.3)",
                borderRadius: "4px",
                padding: "1px 6px",
                fontWeight: 500,
              }}
            >
              ⚡ Jev:{" "}
              {jevResponse.qualifying_intents && jevResponse.qualifying_intents.length > 1
                ? `マルチ (${jevResponse.qualifying_intents
                    .map((k) => JEV_INTENT_META[k]?.label || k)
                    .join(" + ")})`
                : `${
                    JEV_INTENT_META[jevResponse.answers.intent.choice]?.label ||
                    jevResponse.answers.intent.choice
                  }${
                    jevResponse.answers.intent.confidence !== undefined
                      ? ` (${Math.round(jevResponse.answers.intent.confidence * 100)}%)`
                      : ""
                  }`}
            </span>
          )}
        </summary>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            marginTop: "6px",
          }}
        >
          {jevResponse?.qualifying_intents &&
            jevResponse.qualifying_intents.length > 1 && (
              <div
                style={{
                  padding: "6px 8px",
                  background: "rgba(6, 182, 212, 0.08)",
                  border: "1px solid rgba(6, 182, 212, 0.25)",
                  borderRadius: "6px",
                  fontSize: "11px",
                  color: "#cbd5e1",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontWeight: 600,
                    color: "#67e8f9",
                  }}
                >
                  <span>⚡ マルチセクション取得（閾値20%以上）</span>
                </div>
                <div>
                  確率20%以上の全候補項目（
                  {jevResponse.qualifying_intents
                    .map((k) => JEV_INTENT_META[k]?.label || k)
                    .join("・")}
                  ）のセクションを網羅して取得し、LLMに提供しています。
                </div>
              </div>
            )}

          {sectionGroups.length > 1 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "4px",
                padding: "6px 0",
                borderBottom: "1px dashed var(--border)",
              }}
            >
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--muted)",
                  alignSelf: "center",
                  marginRight: "2px",
                }}
              >
                セクション別:
              </span>
              <button
                type="button"
                onClick={() => setSelectedSection("all")}
                style={{
                  padding: "2px 8px",
                  borderRadius: "10px",
                  fontSize: "11px",
                  border:
                    selectedSection === "all"
                      ? "1px solid #3b82f6"
                      : "1px solid var(--border)",
                  background: selectedSection === "all" ? "#1d4ed8" : "transparent",
                  color: selectedSection === "all" ? "#fff" : "var(--fg)",
                  cursor: "pointer",
                }}
              >
                すべて ({totalCount})
              </button>
              {sectionGroups.map((g) => {
                const isSelected = selectedSection === g.code;
                return (
                  <button
                    key={g.code}
                    type="button"
                    onClick={() => setSelectedSection(isSelected ? "all" : g.code)}
                    style={{
                      padding: "2px 8px",
                      borderRadius: "10px",
                      fontSize: "11px",
                      border: isSelected
                        ? "1px solid #a855f7"
                        : "1px solid var(--border)",
                      background: isSelected ? "rgba(168, 85, 247, 0.25)" : "transparent",
                      color: isSelected ? "#e9d5ff" : "var(--muted)",
                      cursor: "pointer",
                    }}
                  >
                    [{g.code}] {g.title} ({g.count})
                  </button>
                );
              })}
            </div>
          )}

          {displayedSources.length === 0 && (
            <div
              style={{
                padding: "16px 12px",
                color: "var(--muted)",
                fontSize: "12px",
                textAlign: "center",
                background: "var(--assistant-bg)",
                borderRadius: "6px",
                border: "1px dashed var(--border)",
              }}
            >
              該当する添付文書の根拠記載は見つかりませんでした（0件）
            </div>
          )}

          {displayedSources.map((s) => (
            <div
              key={s.unit_id}
              className="source-evidence-card"
              style={{
                padding: "6px 8px",
                background: "var(--assistant-bg)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                lineHeight: 1.4,
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "6px 8px",
                  marginBottom: "6px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "baseline",
                    gap: "4px 8px",
                  }}
                >
                  <span
                    style={{
                      fontWeight: 600,
                      color: "#93c5fd",
                    }}
                  >
                    [{s.section.code}] {s.section.title}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      color: "#cbd5e1",
                    }}
                  >
                    {s.product_name}
                  </span>
                </div>
                <div>
                  {s.retrieved_by.map((source) => (
                    <span
                      key={source}
                      style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "#60a5fa",
                        background: "rgba(59, 130, 246, 0.15)",
                        border: "1px solid rgba(59, 130, 246, 0.3)",
                        borderRadius: "4px",
                        padding: "2px 6px",
                        marginLeft: "4px",
                      }}
                    >
                      {
                        {
                          logic: "ロジック取得",
                          jev: "Jev判定取得",
                          keyword: "形態素キーワード",
                        }[source]
                      }
                    </span>
                  ))}
                </div>
              </div>
              {s.columns ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "2px",
                  }}
                >
                  {s.columns.drug_name && (
                    <div>
                      <span style={{ color: "var(--muted)" }}>併用薬: </span>
                      <span>{s.columns.drug_name}</span>
                    </div>
                  )}
                  {s.columns.clinical_symptoms_and_measures && (
                    <div>
                      <span style={{ color: "var(--muted)" }}>臨床症状・措置: </span>
                      <span>{s.columns.clinical_symptoms_and_measures}</span>
                    </div>
                  )}
                  {s.columns.mechanism_and_risk_factors && (
                    <div>
                      <span style={{ color: "var(--muted)" }}>機序・危険因子: </span>
                      <span>{s.columns.mechanism_and_risk_factors}</span>
                    </div>
                  )}
                </div>
              ) : (
                <SourceEvidenceContent content={s.excerpt} />
              )}
              <div
                style={{
                  fontSize: "11px",
                  color: "var(--muted)",
                  marginTop: "8px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "2px",
                }}
              >
                <div>改訂: {formatRevision(s.document_revision)}</div>
                <div>YJコード: {s.product_yj_codes.join(", ") || "不明"}</div>
                {s.url && (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#93c5fd" }}
                  >
                    PMDAの出典を開く
                  </a>
                )}
                {s.references.length > 0 && (
                  <div>
                    参照先:{" "}
                    {s.references.map((reference, referenceIndex) => {
                      const label = [
                        reference.kind,
                        reference.target_section_code
                          ? `項目 ${reference.target_section_code}`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" / ");
                      return (
                        <span key={`${label}-${referenceIndex}`}>
                          {reference.target_url ? (
                            <a
                              href={reference.target_url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: "#93c5fd" }}
                            >
                              {label || reference.target_url}
                            </a>
                          ) : (
                            label || "参照"
                          )}
                          {referenceIndex < s.references.length - 1 ? ", " : ""}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--muted)",
                  marginTop: "4px",
                }}
              >
                単位ID: {s.unit_id}
              </div>
            </div>
          ))}
        </div>
      </details>
    </aside>
  );
}
