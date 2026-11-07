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
            登録履歴
          </h2>
          <p {...stylex.props(styles.description)}>
            登録した順に表示します。上の登録順と改訂年月は異なるため、検索への適用状況も確認してください。
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
            登録履歴はありません。上の手順に沿って電子添文XMLを登録してください。
          </p>
        )}
        {!error && page && page.items.length > 0 && (
          <>
            <p {...stylex.props(styles.description)}>
              {page.total_count}件中 {page.offset + 1}〜{page.offset + page.items.length}
              件
            </p>
            <ul {...stylex.props(styles.list)}>
              {page.items.map((item) => {
                const productNames = item.products
                  .map((product) => product.brand_name)
                  .filter((name): name is string => Boolean(name));
                return (
                  <li
                    key={`${item.document_id}:${item.source_sha256}`}
                    {...stylex.props(styles.item)}
                  >
                    <div {...stylex.props(styles.row)}>
                      <h3 {...stylex.props(styles.products)}>
                        {productNames.join(" / ") || "製品名不明"}
                      </h3>
                      <span
                        {...stylex.props(
                          styles.badge,
                          item.active_yj_codes.length > 0 && styles.active,
                        )}
                      >
                        {item.active_yj_codes.length > 0
                          ? "検索に適用中"
                          : "現在は適用されていません"}
                      </span>
                    </div>
                    <p {...stylex.props(styles.description)}>
                      改訂年月: {item.revised_at}
                    </p>
                    {item.artifacts_deleted && (
                      <p>
                        この旧版の保存データは削除済みです。登録履歴のみ表示しています。
                      </p>
                    )}
                    <details>
                      <summary>管理用の詳細を表示</summary>
                      <p {...stylex.props(styles.description)}>
                        ファイル名: {item.filename ?? "記録なし"}
                      </p>
                      <p {...stylex.props(styles.description)}>
                        登録順: {item.registration_sequence}
                      </p>
                      <p {...stylex.props(styles.description)}>
                        現在適用中のYJコード: {item.active_yj_codes.join(", ") || "なし"}
                      </p>
                      <p {...stylex.props(styles.description)}>
                        登録ID: {item.document_id}
                      </p>
                      <p {...stylex.props(styles.fingerprint)}>
                        原本SHA256: {item.source_sha256}
                      </p>
                    </details>
                  </li>
                );
              })}
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
