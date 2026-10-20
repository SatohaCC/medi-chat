import * as stylex from "@stylexjs/stylex";
import Link from "next/link";
import { AppHeader } from "../../../shared/ui/AppHeader";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import logicRules from "../logicRules.json";
import { styles } from "./SearchGuideScreen.styles";

const methods = [
  {
    number: "01",
    title: "ロジック検索",
    badge: "ロジック取得",
    lead: "決められた言葉から、調べる項目を選ぶ",
    description:
      "質問に含まれる言葉を、あらかじめ定義したルールと照合します。一致した言葉に対応する添付文書の項目を検索します。",
    example:
      "例えば「併用禁忌」は「併用」と「禁忌」に一致し、相互作用の項目と「2 禁忌」の両方を検索します。",
    note: "定義された言葉に反応するため、別の言い回しや文脈を拾えない場合があります。",
  },
  {
    number: "02",
    title: "形態素解析＋エイリアス変換",
    badge: "形態素キーワード",
    lead: "質問を単語に分け、本文に含まれる言葉を探す",
    description:
      "日本語の解析器Janomeで質問を単語に分け、検索に使う語を取り出します。不要な語を除き、一部の表現を検索向けの語に変換して、添付文書の本文を検索します。",
    example:
      "例えば「眠くなる？」を解析して基本形の「眠い」を得た後、登録済みのエイリアス定義で「眠気」「傾眠」に変換します。すべての語を同義語に広げるわけではありません。",
    note: "言葉が本文にあっても、質問に直接答える記載とは限りません。前後の文脈を確認してください。",
  },
  {
    number: "03",
    title: "Jevによる判定",
    badge: "Jev判定取得",
    lead: "エイリアスで拾いきれない言い回しを、意図の判定で補う",
    description:
      "エイリアス変換で対応できるのは、あらかじめ登録した表現に限られます。さまざまな言い回しや、単語だけでは捉えにくい質問の意図を補うためにJevを使います。Jevで質問の意図を判定し、採用条件を満たした判定を添付文書の項目に対応付けて、登録済みの添付文書から根拠を取得します。",
    example:
      "質問を「相互作用・飲み合わせ」などの意図として判定し、対応する項目を探します。",
    note: "Jevも、すべての言い回しや意図を正しく判定できるとは限りません。判定を利用できない場合や採用条件を満たさない場合は、Jevによる検索条件は追加されません。",
  },
];

function LogicRules({ rules }: { rules: typeof logicRules }) {
  return (
    <dl {...stylex.props(styles.rules)}>
      {rules.map((rule) => (
        <div key={rule.priority} {...stylex.props(styles.rule)}>
          <dt {...stylex.props(styles.terms)}>
            分類 {rule.priority}：{rule.keywords.map((word) => `「${word}」`).join("・")}
          </dt>
          <dd>
            <p>いずれかの言葉に一致すると、次の項目を検索します。</p>
            <ul {...stylex.props(styles.sections)}>
              {rule.sections.map((section) => (
                <li key={section.code}>
                  {section.code} {section.title}
                </li>
              ))}
            </ul>
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function SearchGuideScreen() {
  return (
    <div {...stylex.props(layout.root)}>
      <AppHeader />
      <main {...stylex.props(styles.main)}>
        <article {...stylex.props(styles.article)}>
          <div {...stylex.props(styles.intro)}>
            <p {...stylex.props(styles.eyebrow)}>検索の仕組み</p>
            <h1 {...stylex.props(styles.title)}>3つの方法で、添付文書の根拠を探す</h1>
            <p>
              チャットでは、@医薬品で選択した製品を対象に、質問の言葉と意図を別々の方法で調べ、登録済み添付文書から回答に使う根拠を集めます。質問文に薬名を書くだけでは、検索対象を追加・変更しません。
            </p>
          </div>
          <ol {...stylex.props(styles.flow)} aria-label="質問から回答までの流れ">
            <li {...stylex.props(styles.step)}>質問・対象医薬品</li>
            <li {...stylex.props(styles.step)}>3つの方法で根拠を検索</li>
            <li {...stylex.props(styles.step)}>根拠を使って回答を生成</li>
          </ol>
          <div {...stylex.props(styles.cards)}>
            {methods.map((method) => (
              <section key={method.number} {...stylex.props(styles.card)}>
                <p {...stylex.props(styles.eyebrow)}>{method.number}</p>
                <h2 {...stylex.props(styles.heading)}>{method.title}</h2>
                <span {...stylex.props(styles.badge)}>{method.badge}</span>
                <p {...stylex.props(styles.lead)}>{method.lead}</p>
                <p>{method.description}</p>
                <p {...stylex.props(styles.example)}>{method.example}</p>
                {method.number === "01" && (
                  <>
                    <h3 {...stylex.props(styles.lead)}>実際のキーワードと検索項目</h3>
                    <p>
                      質問に以下の語が含まれるかを照合します。英字の大文字・小文字、文字幅や空白などを正規化したうえで部分一致を調べ、一致した分類すべての項目を検索します。同じ分類や根拠は重複して表示しません。
                    </p>
                    <LogicRules rules={logicRules.slice(0, 3)} />
                    <details {...stylex.props(styles.more)}>
                      <summary {...stylex.props(styles.summary)}>
                        残りのキーワードと項目を見る（{logicRules.length - 3}分類）
                      </summary>
                      <LogicRules rules={logicRules.slice(3)} />
                    </details>
                    <p>
                      部分一致のため、「副作用」は「作用」にも一致し、副作用と効能・効果の両分類が検索対象になります。どの語にも一致しなければ、ロジック検索による項目指定は追加しません。指定項目の記載が対象製品にある場合に、根拠として取得されます。
                    </p>
                  </>
                )}
                <p {...stylex.props(styles.note)}>{method.note}</p>
              </section>
            ))}
          </div>
          <section {...stylex.props(styles.detail)}>
            <h2 {...stylex.props(styles.heading)}>根拠カードのラベルの見方</h2>
            <p>
              ラベルは、その根拠を取得した方法を示します。同じ根拠を複数の方法で取得した場合は、複数のラベルが付きます。ラベルの数や取得方法は、医学的な正しさや安全性の評価ではありません。
            </p>
            <p>
              ロジック検索と形態素解析で見つかった根拠は、先に表示される場合があります。Jevの判定を含む検索が終わると、根拠が追加・更新されます。
            </p>
          </section>
          <section {...stylex.props(styles.detail)}>
            <h2 {...stylex.props(styles.heading)}>根拠を探す処理と、回答を作る処理</h2>
            <p>
              Jevは質問の意図を判定するために使います。ヘッダーの「回答モデル」は、取得した根拠をもとに回答文を作るモデルを選ぶものです。
            </p>
            <p>
              この3方式はチャットの根拠取得についての説明です。「キーワード検索」ページは、入力した検索語から本文を探すための画面です。
            </p>
            <Link href="/" {...stylex.props(styles.link)}>
              チャットで試す →
            </Link>
          </section>
        </article>
      </main>
    </div>
  );
}
