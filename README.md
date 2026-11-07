# loto-analysis-feed

ロト6・ロト7の分析結果をChatGPTの定期タスクから取得するための**公開データ専用**リポジトリです。

## 公開データ

- [最新の両くじ結果](feed/latest.json)
- [ロト6](feed/loto6.json)
- [ロト7](feed/loto7.json)

生成元: `https://loto-independent-analysis.imadokogo.workers.dev`

Cloudflare Workersが直近100回を照合・分析し、GitHub Actionsがデータの検証を行って、このリポジトリの `feed/*.json` を更新します。ここには**認証情報、個人情報、購入履歴、Cloudflareのソースコードは保存しません**。

更新頻度は日本時間05:07、05:17、05:27、05:47、06:07、20:37（GitHub Actionsの実行時刻は遅れることがあります）。[手動実行](../../actions/workflows/publish.yml)もできます。

## 状態の読み方

`status: SUCCESS` は、API応答・100回照合・必須6項目・5口の形式・鮮度をこの公開用プログラムが検証した状態です。

`verificationLevel: SECONDARY_CROSSCHECK_100` は**非公式2サイト間で100回照合**したことを意味します。公式みずほ銀行CSVの照合完了を意味しません。

`scheduleVerification: UNOFFICIAL_ESTIMATE` と `purchaseCutoffOfficiallyVerified: false` は、対象抽せん日・公式ネット購入締切が別途正式確認されていないことを意味します。定期通知では公式確認なしに「公式確定」と表示してはいけません。

`status: FAILED` なら `predictions: []` になり、過去の予想を再利用しません。取得時には `mirroredAt`、`sourceCheckedAt`、`targetDrawDate`、`targetIssue` と分析範囲を確認してください。

過去データから将来の当せん番号を高精度に予測できるわけではなく、組合せによって当せん確率は変わりません。

## プログラム

- `scripts/publish.py` — Cloudflare APIを取得し、再検証して公開用JSONを生成
- `.github/workflows/publish.yml` — 日時指定・ソース変更・手動実行に対応
- `tests/test_publish.py` — 正常・不一致・鮮度不足・締切超過・取得失敗の6テスト

初回起動: GitHubの [Actions](../../actions/workflows/publish.yml) から `Run workflow` を実行するか、README等の更新に伴う自動実行を確認します。
