# Maintainer release guide

このリポジトリは公開済みです。通常の変更はブランチとPRでレビューし、CIの結果を確認してからmainへ反映します。
ユーザー向けの導入方法は[クイックスタート](QUICKSTART.ja.md)を参照してください。

## 公開前の確認

```sh
python -m pytest -q
python scripts/sync_skill_assets.py --check
python scripts/validate_distribution.py
python scripts/check_public_content.py
```

文書だけの変更で固定配布済みwheelを同じ版のまま再生成しないでください。
次の配布版を作る際は、package・CLI・pluginの版を揃え、変更履歴を更新してから生成します。

```sh
python scripts/build_marketplace.py
python scripts/validate_distribution.py
python scripts/check_public_content.py
```

生成したwheel、manifest、Skillミラーの差分もレビューします。導入経路を変えた場合は、
使い捨て環境で実npx導入と対象ホストのスモークテストを実施します。実APIの利用と費用には別途許可が必要です。

## 表示する検証範囲

ローカルfixture、SDK契約テスト、実API、実ホスト、性能比較は別々に記録します。
未実行を成功と表現せず、古いログには対象revision/版と採取条件を残します。
公開用ログは秘密値・個人情報・実環境のパスを点検し、匿名化した場合はその旨を残してください。

## 初回公開用の履歴

`scripts/publish-github.sh`、`scripts/publish_public.py`、`PUBLICATION_MANIFEST.json` と関連テストは
初回公開のための固定スナップショットを扱う履歴的な補助物です。**通常更新には使いません。**
manifestのハッシュは初回アーカイブ用で、現行mainの整合性証明ではありません。
現在のドキュメント変更後に旧manifestの確認が失敗するのは意図した挙動です。
初回公開履歴やテスト結果を後から現在の状態に書き換えないでください。

## 継続的な安全確認

GitHubのsecret scanning / push protectionとprivate vulnerability reportingを設定画面で確認してください。
このPRやファイルの追加だけで、そのリポジトリ設定が有効になるわけではありません。
認証情報が見つかった場合は公開Issueや通常PRへ値を載せず、まず失効・再発行を行い、
必要な履歴の扱いを別途確認します。通常の文書整理のためにforce-pushしません。

[Security](../SECURITY.md) · [Contributing](../CONTRIBUTING.md)
