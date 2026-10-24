# Pythonの証明書更新

2026年10月のeMudhra / emSign CAインシデントへの対応。
[Pythonの公式告知](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
に従い、certifiは2026.10.19以上、pipを使う環境では26.2.2以上、uvは0.13.4以上を使用する。
OSの証明書更新だけでは、古いpipに同梱された証明書への信頼は除去されない。

backend/pyproject.tomlでcertifiとuvの最低版を指定し、依存の正本をbackend/uv.lockとする。
新しいbackend環境の作成・同期には、対応済みuvで次を実行する。

```powershell
uv --version
uv sync --project backend --locked
uv export --project backend --locked --format pylock.toml --output-file backend/pylock.toml --no-emit-project
node scripts/export-vercel-requirements.mjs
```

Python本体のensurepipが古い場合、`python -m venv`や`python -m ensurepip`で
未対応のpipが入る。pipが必要なら、対応済みuvを使い、対象のPythonを明示して更新する。

```powershell
uv pip install --python .venv/Scripts/python.exe "pip>=26.2.2" "certifi>=2026.10.19"
```

2026年10月23日のローカル確認では、ルート.venvのpipを26.2.2、
ルート.venvとbackend/.venvのcertifiを2026.10.19へ更新した。
PATH上のuv 0.13.4とPython 3.12.3のpip 26.2.2 / certifi 2026.10.19は対応版だった。
backend/.venvのPython 3.14.0にはensurepip 25.2が残っているため、
Python本体の更新または上記手順による新規環境のpip更新が必要。

デプロイ先では更新済み依存で再ビルド・再デプロイし、実行環境のバージョンも確認する。
Pythonを含むコンテナを利用する場合は、公式告知に従ってレイヤーキャッシュを無効にして再ビルドする。
今回、デプロイ先・PC内の他プロジェクト・OSの証明書ストアは検証していない。
