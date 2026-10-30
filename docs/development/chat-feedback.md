# 回答へのユーザー評価

正常完了した回答の下に、React Ariaによる「いいね」「よくない」を表示する。再クリックで評価を取り消す。選択は即時反映し、保存に失敗したら直前の確定状態へ戻して再試行を表示する。送信中の連打を防止するが、ボタンの透明度は変えない。「いいね」のアニメーションは`prefers-reduced-motion`に従う。

## 設定

通常のLangSmith設定に加え、`MEDI_CHAT_FEEDBACK_SECRET`へ暗号学的乱数による32バイト以上の秘密文字列を設定する。同じ環境の全backendインスタンスで共通の値を使い、Gitやログへ出力しない。LangSmithから取得するAPIキーとは別の、アプリが管理する署名鍵である。

署名鍵の欠落・長さ不足、LangSmithトレース無効、APIキー未設定、サンプリング率が1以外の場合、評価機能を無効化する。回答生成は継続する。ローカル設定の反映にはbackendを再起動する。

## 保存と表示

- REST回答およびWebSocketの`text_done`に、評価対象のrun・ユーザー・プロジェクト・有効期限を結び付けた署名付き`feedback_token`を返す。有効期間は24時間。
- `PUT /api/chat/feedback`で`feedback_token`と`rating`を送る。`up`は1、`down`は0、`null`は取消。既存の認証・Origin・CSRF検証も適用する。
- LangSmithのキーは`user_feedback`。回答・ユーザーごとの安定したfeedback IDを使用し、再送・変更で重複させない。取消は削除し、削除済みへの取消も成功とする。評価作成時にはログイン中の`user_id`を`source_info`および`extra`へ記録し、評価者を識別可能とする。
- SDKは専用ワーカーで実行し、外部APIが応答するまで成功を返さない。APIキーをブラウザへ渡さず、評価トークンや評価値をLLMの会話履歴へ含めない。
- LangSmithの対象プロジェクトで`medi_chat.stream_answer`または`medi_chat.answer_question`のrunを開くと評価を確認できる。検索準備用のrunは評価対象にしない。

コメント入力・再読み込み後の評価復元・評価からの自動学習は対象外。

## 検証

ケースは[テスト仕様](chat-feedback-test-spec.md)を参照する。BackendのAPI・署名・SDK境界テストと、`frontend/e2e/chat-feedback.spec.ts`のブラウザテストを分けて実行する。SDKダブルを使う検証は、実LangSmithの保存成功を証明するものではない。
