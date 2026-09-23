# Maintainer publishing / release guide

このGitHubリポジトリは **すでにPublicで公開済み** です。

通常の更新では、初回公開用の`scripts/publish-github.sh` / `scripts/publish_public.py`を使いません。これらは「存在しない新規リポジトリを安全に初回公開する」ために作られたbootstrap-eraの補助コードで、既存リポジトリへの更新を拒否する設計です。

## 通常の更新フロー

1. feature/docsブランチを作る
2. 変更を実装する
3. ローカルテストと配布整合性チェックを実行する
4. PRを作成する
5. CIと差分を確認する
6. mainへマージする
7. 必要に応じてtag / GitHub Releaseを作る

## リリース前チェック

```sh
python -m pytest -q
python scripts/sync_skill_assets.py --check
python scripts/build_marketplace.py
python scripts/validate_distribution.py
```

Agent Skills経由の配布を変更した場合は、使い捨てのテストプロジェクトで実`npx`導入も確認します。

```sh
python scripts/smoke_skills_install.py --skills-version 1.7.0 --agent cursor --write --allow-downloads
```

実ホスト、Jev API、品質改善ベンチマークはそれぞれ別の検証です。

## バージョン更新

ユーザーに見える変更では、必要に応じて以下を更新します。

- package / Skill version
- `CHANGELOG.md`
- bundled wheel / integrity manifest
- marketplace metadata
- documentation

生成ミラーがあるファイルは手編集と生成物を混在させず、既存の同期スクリプトを使います。

## 公開済み導入元

標準のAgent Skills導入：

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

Claude Code：

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

Codex：

```sh
codex plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
```

詳細は [DISTRIBUTION.ja.md](DISTRIBUTION.ja.md) を参照してください。

## 初回公開用スクリプトについて

`scripts/publish-github.sh`、`scripts/publish_public.py`、`PUBLICATION_MANIFEST.json`、関連テストは初回公開時の安全確認用として現在も履歴的に残っています。

これらは **通常リリースには使用しません**。削除する場合は、関連テスト・validation docs・参照箇所も同じPRで整理してください。

## セキュリティ

- APIキーやGitHub tokenをファイルへ直書きしない
- `.env`、秘密鍵、ローカルDB、実行状態をcommitしない
- 配布wheelやmanifestの差分をレビューする
- 外部送信対象や権限変更を、リリースノートなしで広げない
- force-pushや既存公開履歴の書き換えを通常のリリース手順にしない
