import * as stylex from "@stylexjs/stylex";
import Link from "next/link";
import { AppHeader } from "../../../shared/ui/AppHeader";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import alwaysSections from "../alwaysSections.json";
import logicRules from "../logicRules.json";
import { styles } from "./SearchGuideScreen.styles";

const methods = [
  {
    number: "01",
    title: "項目をルールで選ぶ",
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
    title: "本文の言葉を探す",
    badge: "形態素キーワード",
    lead: "質問から検索語を取り出して、本文を探す",
    description:
      "日本語の解析器Janomeで質問を単語に分け、検索に使う語を取り出します。不要な語を除き、一部の表現を検索向けの語に変換して、添付文書の本文を検索します。",
    example:
      "例えば「眠くなる？」を解析して基本形の「眠い」を得た後、登録済みのエイリアス定義で「眠気」「傾眠」に変換します。すべての語を同義語に広げるわけではありません。",
    note: "言葉が本文にあっても、質問に直接答える記載とは限りません。前後の文脈を確認してください。",
  },
  {
    number: "03",
    title: "質問の意図から選ぶ",
    badge: "Jev判定取得",
    lead: "Jevが質問を分類し、対応する項目を探す",
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
            <h1 {...stylex.props(styles.title)}>回答の根拠は、どう集まる？</h1>
            <p>
              選んだ医薬品の添付文書から、毎回取得する3項目と、質問に関係する記載を集めます。回答モデルは、集まった根拠を使って回答を作ります。
            </p>
          </div>
          <ol {...stylex.props(styles.flow)} aria-label="質問から回答までの流れ">
            {[
              "質問・対象医薬品",
              "警告・禁忌・重要な基本的注意を取得",
              "3つの方法で質問に応じた根拠を追加",
              "根拠を使って回答を生成",
            ].map((label, index) => (
              <li key={label} {...stylex.props(styles.step)}>
                <div {...stylex.props(styles.stepCard)}>
                  <span {...stylex.props(styles.stepNumber)}>{index + 1}</span>
                  <span>{label}</span>
                </div>
                {index < 3 && (
                  <span {...stylex.props(styles.stepArrow)} aria-hidden="true">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>
          <section {...stylex.props(styles.detail)}>
            <h2 {...stylex.props(styles.heading)}>まず、対象の医薬品を選びます</h2>
            <p>
              チャットの「@医薬品」で選択した製品が対象です。質問文に薬名を書くだけでは、検索対象は追加・変更されません。登録済みの添付文書を検索します。
            </p>
          </section>
          <section {...stylex.props(styles.card)}>
            <h2 {...stylex.props(styles.heading)}>毎回取得する3項目</h2>
            <span {...stylex.props(styles.badge)}>常時取得</span>
            <p>質問の内容にかかわらず、選んだ各製品から次の本文を取得します。</p>
            <ul {...stylex.props(styles.alwaysSections)}>
              {alwaysSections.map((section) => (
                <li key={section.code}>
                  {section.code} {section.title}
                </li>
              ))}
            </ul>
            <p {...stylex.props(styles.note)}>
              配下の項目も含め、記載がある本文だけを取得します。この3項目だけで安全性全般を確認できるわけではありません。
            </p>
          </section>
          <section {...stylex.props(styles.detail)}>
            <h2 {...stylex.props(styles.heading)}>
              質問に関係する根拠を、3つの方法で追加します
            </h2>
            <p>
              3つの方法を組み合わせて探します。一つの方法だけで選ぶ仕組みではありません。
            </p>
            <div {...stylex.props(styles.cards)}>
              {methods.map((method) => (
                <section key={method.number} {...stylex.props(styles.card)}>
                  <p {...stylex.props(styles.eyebrow)}>{method.number}</p>
                  <h3 {...stylex.props(styles.methodHeading)}>{method.title}</h3>
                  <span {...stylex.props(styles.badge)}>{method.badge}</span>
                  <p>{method.lead}</p>
                  <details {...stylex.props(styles.more)}>
                    <summary {...stylex.props(styles.summary)}>仕組みと例を見る</summary>
                    <div {...stylex.props(styles.explanation)}>
                      <p>{method.description}</p>
                      <p {...stylex.props(styles.example)}>{method.example}</p>
                      <p {...stylex.props(styles.note)}>{method.note}</p>
                    </div>
                  </details>
                  {method.number === "01" && (
                    <details {...stylex.props(styles.more)}>
                      <summary {...stylex.props(styles.summary)}>
                        ロジック検索のキーワードと対象項目を見る（{logicRules.length}
                        分類）
                      </summary>
                      <div {...stylex.props(styles.explanation)}>
                        <p>
                          質問の表記を正規化して部分一致を調べ、一致した分類すべての項目を検索します。どの語にも一致しなければ、ロジック検索の項目指定は追加しません。
                        </p>
                        <p>
                          例えば「副作用」は「作用」にも一致するため、副作用と効能・効果の両分類が対象になります。指定した項目に記載がある場合に取得します。
                        </p>
                        <LogicRules rules={logicRules} />
                      </div>
                    </details>
                  )}
                </section>
              ))}
            </div>
          </section>
          <section {...stylex.props(styles.detail)}>
            <h2 {...stylex.props(styles.heading)}>根拠カードのラベルの見方</h2>
            <p>
              カードのラベルは「なぜ、この根拠が表示されているか」を示します。例えば「常時取得」と「ロジック取得」が付いていれば、毎回取得する項目であり、質問の言葉にも一致した根拠です。
            </p>
            <p>
              常時取得の根拠を先に表示し、ロジック検索と形態素解析で見つかった根拠を順次追加します。Jevの判定を含む検索が終わると、根拠が追加・更新されます。
            </p>
            <p>
              同じ根拠のカードは一つにまとめ、取得理由を併記します。そのため、理由別の件数を足しても、カードの合計件数とは一致しない場合があります。ラベルは正しさや安全性の評価ではありません。
            </p>
          </section>
          <section {...stylex.props(styles.detail)}>
            <h2 {...stylex.props(styles.heading)}>集めた根拠を使って、回答を作ります</h2>
            <p>
              ヘッダーの「回答モデル」で選んだモデルが、取得した根拠を使って回答文を作ります。Jevは根拠を探すための意図判定を担当します。
            </p>
            <p>
              このページはチャットの仕組みの説明です。別の「キーワード検索」ページでは、入力した語から本文を直接探せます。
            </p>
            <p>
              回答は取得した根拠に基づいて生成します。必要な情報が見つからない場合は「今回取得した根拠では確認できません」と伝えるよう指示しています。添付文書全体に記載がないと確認したことを意味しません。
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
