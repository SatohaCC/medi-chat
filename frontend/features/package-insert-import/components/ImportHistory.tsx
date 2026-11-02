import * as stylex from "@stylexjs/stylex";
import { Button } from "../../../shared/ui/Button";
import { useImportHistory } from "../hooks/useImportHistory";
import { styles } from "./ImportHistory.styles";

export function ImportHistory() {
  const { page, loading, error, refresh, setOffset } = useImportHistory();
  return (
    <section aria-labelledby="import-history-title" {...stylex.props(styles.section)}>
      <div {...stylex.props(styles.header)}>
        <div>
          <h2 id="import-history-title" {...stylex.props(styles.title)}>
            取り込み済みXML
          </h2>
          <p {...stylex.props(styles.description)}>
            新しく登録した順に表示します。旧版の登録履歴も含みます。
          </p>
        </div>
        <Button variant="text" onActivate={refresh} disabled={loading}>
          一覧を更新
        </Button>
      </div>
      <div aria-busy={loading}>
        {loading && <p role="status">一覧を読み込み中…</p>}
        {error && <p role="alert">{error}「一覧を更新」で再試行できます。</p>}
        {!loading && !error && page?.total_count === 0 && (
          <p {...stylex.props(styles.description)}>
            取り込み済みのXMLはありません。上のフォームからXMLを登録してください。
          </p>
        )}
        {!error && page && page.items.length > 0 && (
          <>
            <p {...stylex.props(styles.description)}>
              {page.total_count}件中 {page.offset + 1}〜{page.offset + page.items.length}
              件
            </p>
            <ul {...stylex.props(styles.list)}>
              {page.items.map((item) => (
                <li
                  key={`${item.document_id}:${item.source_sha256}`}
                  {...stylex.props(styles.item)}
                >
                  <div {...stylex.props(styles.row)}>
                    <h3 {...stylex.props(styles.filename)}>
                      {item.filename ?? item.document_id}
                    </h3>
                    <span
                      {...stylex.props(
                        styles.badge,
                        item.active_yj_codes.length > 0 && styles.active,
                      )}
                    >
                      {item.active_yj_codes.length > 0
                        ? "検索に適用中"
                        : "旧版・適用なし"}
                    </span>
                  </div>
                  <p {...stylex.props(styles.products)}>
                    {item.products
                      .map((p) => p.brand_name || p.yj_code)
                      .filter(Boolean)
                      .join(" / ") || "製品名なし"}
                  </p>
                  <p {...stylex.props(styles.description)}>
                    改訂年月 {item.revised_at} · 登録順 {item.registration_sequence}
                  </p>
                  <p {...stylex.props(styles.description)}>
                    現在適用中のYJ: {item.active_yj_codes.join(", ") || "なし"}
                  </p>
                  {item.artifacts_deleted && (
                    <p {...stylex.props(styles.description)}>
                      この旧版の保存データは削除済みです。登録履歴のみ表示しています。
                    </p>
                  )}
                  <p {...stylex.props(styles.fingerprint)}>
                    原本SHA256: {item.source_sha256}
                  </p>
                </li>
              ))}
            </ul>
            <div {...stylex.props(styles.pagination)}>
              <Button
                variant="text"
                disabled={loading || page.offset === 0}
                onActivate={() => setOffset(Math.max(0, page.offset - page.limit))}
              >
                前の20件
              </Button>
              <Button
                variant="text"
                disabled={loading || page.offset + page.items.length >= page.total_count}
                onActivate={() => setOffset(page.offset + page.limit)}
              >
                次の20件
              </Button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
