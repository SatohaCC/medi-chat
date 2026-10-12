"use client";

import * as stylex from "@stylexjs/stylex";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Button } from "../../../shared/ui/Button";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import { ToggleButton } from "../../../shared/ui/ToggleButton";
import { type SourceItem, SourceEvidenceContent, formatRevision } from "../../chat";
import { useActiveMedicines } from "../../medicine-selection/hooks/useActiveMedicines";
import { searchPackageInserts } from "../api/searchApi";
import { styles } from "./KeywordSearchScreen.styles";

function HighlightText({ text, words }: { text: string; words: string[] }) {
  if (!text || !words.length) return <>{text}</>;
  const validWords = words.filter((w) => w.length > 0);
  if (!validWords.length) return <>{text}</>;
  const escaped = validWords.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(pattern);
  return (
    <>
      {parts.map((part, index) => {
        if (!part) return null;
        const isMatch = validWords.some((w) => w.toLowerCase() === part.toLowerCase());
        return isMatch ? (
          <mark key={`${part}-${index}`} className="search-highlight">
            {part}
          </mark>
        ) : (
          part
        );
      })}
    </>
  );
}

export function KeywordSearchScreen() {
  const [query, setQuery] = useState("");
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SourceItem[] | null>(null);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [selectedSection, setSelectedSection] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [showMedicineFilter, setShowMedicineFilter] = useState(false);

  const activeMedicines = useActiveMedicines();

  const toggleYjCode = (yjCode: string) => {
    setSelectedYjCodes((prev) =>
      prev.includes(yjCode) ? prev.filter((c) => c !== yjCode) : [...prev, yjCode],
    );
  };

  const handleSearch = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setError(null);
    try {
      const data = await searchPackageInserts(trimmed, selectedYjCodes);
      setResults(data.items);
      setSearchedQuery(data.query);
      setSelectedSection("all");
    } catch (err) {
      setError(err instanceof Error ? err.message : "検索に失敗しました");
      setResults(null);
    } finally {
      setIsSearching(false);
    }
  };

  const searchWords = searchedQuery
    .split(/[\s　]+/)
    .map((w) => w.trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);

  // Extract unique sections from results
  const sources = results ?? [];
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
    <main data-screen="keyword-search" {...stylex.props(layout.root, styles.main)}>
      <div {...stylex.props(styles.headerRow)}>
        <div>
          <h1 {...stylex.props(styles.title)}>添付文書キーワード検索</h1>
          <p {...stylex.props(styles.description)}>
            登録済み添付文書からキーワードで直接根拠を検索・確認できます。
          </p>
        </div>
        <nav {...stylex.props(styles.navLinks)}>
          <Link href="/" {...stylex.props(styles.link)}>
            チャットへ戻る
          </Link>
          <Link href="/imports" {...stylex.props(styles.link)}>
            添付文書XMLを取り込む
          </Link>
        </nav>
      </div>

      <form {...stylex.props(styles.searchForm)} onSubmit={handleSearch}>
        <input
          {...stylex.props(styles.searchInput)}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="検索キーワードを入力（例: 悪心、併用禁忌、腎機能など）"
          disabled={isSearching}
          aria-label="検索キーワード"
        />
        <Button type="submit" disabled={!query.trim() || isSearching}>
          {isSearching ? "検索中…" : "検索"}
        </Button>
      </form>

      <div {...stylex.props(styles.filterSection)}>
        <div {...stylex.props(styles.headerRow)}>
          <span {...stylex.props(styles.filterHeading)}>
            対象医薬品:{" "}
            {selectedYjCodes.length === 0
              ? "すべての医薬品（絞り込みなし）"
              : `${selectedYjCodes.length}製品を選択中`}
          </span>
          <Button
            variant="text"
            onActivate={() => setShowMedicineFilter((prev) => !prev)}
          >
            {showMedicineFilter ? "▲ 医薬品選択を閉じる" : "▼ 医薬品で絞り込む"}
          </Button>
        </div>

        {showMedicineFilter && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {activeMedicines.groups.flatMap((med) =>
                med.yj_codes.map((code, idx) => {
                  const isSelected = selectedYjCodes.includes(code);
                  const name = med.brand_names[idx] ?? med.generic_name;
                  return (
                    <ToggleButton
                      key={code}
                      selected={isSelected}
                      onSelectedChange={() => toggleYjCode(code)}
                    >
                      {name}
                    </ToggleButton>
                  );
                }),
              )}
            </div>
            {selectedYjCodes.length > 0 && (
              <div>
                <Button variant="text" onActivate={() => setSelectedYjCodes([])}>
                  すべての医薬品を対象に戻す（選択解除）
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div role="alert" {...stylex.props(styles.errorText)}>
          {error}
        </div>
      )}

      {results !== null && (
        <section
          aria-label="検索結果"
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div {...stylex.props(styles.resultSummaryBar)}>
            <span {...stylex.props(styles.resultSummaryText)}>
              📄 「{searchedQuery}」の検索結果（合計：{sources.length}件）
            </span>
          </div>

          {sectionGroups.length > 1 && (
            <div {...stylex.props(styles.sectionFilters)}>
              <span {...stylex.props(styles.filterLabel)}>セクション別:</span>
              <Button
                variant="filterAll"
                selected={selectedSection === "all"}
                onActivate={() => setSelectedSection("all")}
              >
                すべて ({sources.length})
              </Button>
              {sectionGroups.map((g) => {
                const isSelected = selectedSection === g.code;
                return (
                  <Button
                    key={g.code}
                    variant="filterSection"
                    selected={isSelected}
                    onActivate={() => setSelectedSection(isSelected ? "all" : g.code)}
                  >
                    [{g.code}] {g.title} ({g.count})
                  </Button>
                );
              })}
            </div>
          )}

          {displayedSources.length === 0 ? (
            <div {...stylex.props(styles.empty)}>
              該当する添付文書の根拠記載は見つかりませんでした（0件）
            </div>
          ) : (
            <div {...stylex.props(styles.resultsList)}>
              {displayedSources.map((s) => (
                <article
                  key={s.unit_id}
                  {...stylex.props(styles.card)}
                  data-evidence-card="true"
                >
                  <header {...stylex.props(styles.cardHeader)}>
                    <div {...stylex.props(styles.sectionTitleRow)}>
                      <span {...stylex.props(styles.sectionTitle)}>
                        [{s.section.code}]{" "}
                        <HighlightText text={s.section.title} words={searchWords} />
                      </span>
                      <span {...stylex.props(styles.productLabel)}>
                        <HighlightText text={s.product_name} words={searchWords} />
                      </span>
                    </div>
                    <div>
                      {s.retrieved_by.map((source) => (
                        <span key={source} {...stylex.props(styles.retrievalBadge)}>
                          {
                            {
                              logic: "ロジック取得",
                              jev: "Jev判定取得",
                              keyword: "キーワード一致",
                            }[source]
                          }
                        </span>
                      ))}
                    </div>
                  </header>

                  {s.columns ? (
                    <div {...stylex.props(styles.metadata)}>
                      {s.columns.drug_name && (
                        <div>
                          <span {...stylex.props(styles.metaLabel)}>併用薬: </span>
                          <span>
                            <HighlightText
                              text={s.columns.drug_name}
                              words={searchWords}
                            />
                          </span>
                        </div>
                      )}
                      {s.columns.clinical_symptoms_and_measures && (
                        <div>
                          <span {...stylex.props(styles.metaLabel)}>
                            臨床症状・措置:{" "}
                          </span>
                          <span>
                            <HighlightText
                              text={s.columns.clinical_symptoms_and_measures}
                              words={searchWords}
                            />
                          </span>
                        </div>
                      )}
                      {s.columns.mechanism_and_risk_factors && (
                        <div>
                          <span {...stylex.props(styles.metaLabel)}>
                            機序・危険因子:{" "}
                          </span>
                          <span>
                            <HighlightText
                              text={s.columns.mechanism_and_risk_factors}
                              words={searchWords}
                            />
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <SourceEvidenceContent
                      content={s.excerpt}
                      highlightWords={searchWords}
                    />
                  )}

                  <footer {...stylex.props(styles.footer)}>
                    <div>改訂: {formatRevision(s.document_revision)}</div>
                    <div>YJコード: {s.product_yj_codes.join(", ") || "不明"}</div>
                    {s.url && (
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        {...stylex.props(styles.documentLink)}
                      >
                        PMDAの出典を開く
                      </a>
                    )}
                    {s.references && s.references.length > 0 && (
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
                                  {...stylex.props(styles.referenceLink)}
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
                    <div {...stylex.props(styles.unitId)}>単位ID: {s.unit_id}</div>
                  </footer>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
