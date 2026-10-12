# Windows Microsoft IME 手動記録

自動回帰と分離した、実form・実useChatWebSocket・実Next表示の記録用コマンドです。
既存 `e2e/helpers/chat.ts` のREST/WS doubleと固定候補を使い、外部LLM・運用DBへ接続しません。
新しい公開routeは追加していません。試験専用3132/3133が空いていることを確認してください。

リポジトリrootのPowerShellで実行します。

```powershell
$env:TEMP = Join-Path (Get-Location) 'tmp/stylex-temp'
$env:TMP = $env:TEMP
pnpm --filter frontend test:ime:manual
```

1. 自動で開くChromiumを使います。先に `http://127.0.0.1:3133/` の旧HEAD baseline、次に `http://127.0.0.1:3132/` のcurrentを操作します。Windows Microsoft IMEを日本語入力へ切り替えます。入力欄は自動でfocusされます。
2. 「てすと」をIMEで入力して変換中に、画面が指示するEnter/Tab/Escapeを操作します。Enterでは変換確定→compositionendの後、次のEnterも操作してください。
3. 候補なし/ありそれぞれ3操作、各版6ケース（計12）を別画面で記録します。画面の「このケースの記録を保存して次へ」を押してください。送信が発生して入力がdisabledになった場合も、その状態を記録し、追加操作を強行しません。
4. rootの `tmp/stylex-ime-recordings/native-baseline/` と `native-current/` に各6 JSONを保存します。ケース名ファイルは同一フォルダーの前回分を上書きするため、比較用に保存するときは実行前後にフォルダーを別名へcopyしてください。元イベント順序、capture/after-handlers、isComposing/keyCode/data、value/caret、popup/候補、focus、選択YJ、WS回数/payloadと表示source SHAが含まれます。
5. WS値はNode doubleへのasync bridge観測で、イベントDOM snapshotと別時刻です。最後のfocusは記録ボタン操作後なので、入力中のfocusは保存ボタン前のイベント行で評価します。JSONを合格期待へ自動更新しません。

旧画面は `scripts/serve-ime-baseline.mjs` が原baseline HEAD `7b46073b2fc07b9cad43072bf97ae86cbe13b916` のapp sourceを `tmp/stylex-ime-baseline/` へ採取して起動します。現在のworkingtreeを上書きしません。原source SHAをmanifestに固定・照合し、Next/React/React Compilerは同じインストール版を使います。試験環境差はdev indicator非表示、test distの型include、未使用Tailwind pluginを空PostCSSへ置く点です。原コードにはTailwind utility利用がありません。

現時点では両版の実OS IME操作は未実施です。smokeや合成イベントは実IMEbaselineの代替ではありません。実行後も各JSONは `RECORDED_UNREVIEWED` で、test runnerの成功は記録workflowの完了だけです。12ケースでcomposition/key列・変換中/確定直後/次Enter・value/caret・候補・focus・WS回数/payloadを前後照合し、意図しない送信/置換があれば既存問題と退行を分けて進行役へ判断を返してください。期待tupleを自動で改善したり、新出力から更新しません。

記録ツールだけの自動smokeは次で実行できます。OS IME成功ではありません。

```powershell
$env:MEDI_CHAT_IME_SMOKE = '1'
pnpm --filter frontend test:ime:manual
Remove-Item Env:MEDI_CHAT_IME_SMOKE
```

smoke出力は `tmp/stylex-ime-recordings/smoke-baseline/` と `smoke-current/`、状態は `SMOKE_ONLY_NOT_NATIVE_IME` です。
通常mock/real/統合からこの人手待ちsuiteは呼びません。
