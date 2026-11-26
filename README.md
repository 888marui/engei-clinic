# 園芸クリニック— 静的ビルド基盤（Phase 0 雛形）

園芸・家庭菜園のトラブル解決サイト（ドメイン: engei-clinic.com）の雛形。
計画書は `~/workspace/engei-plan-1125.md`。このディレクトリはローカルの雛形で、
GitHub リポジトリ作成と公開はドメイン確定後に行う（下のチェックリスト）。

サイト名は「園芸クリニック」で正式決定（2026-11-27）。
決定したら `build.py` の `SITE_NAME` を差し替える。

## ビルド方式の選定

既存サイト2方式を比較し、**kitchen-point-note 型（Python）を採用**した。

| | kitchen-point-note（採用） | hakajimai-guide（Node） |
|---|---|---|
| 構成 | データファイル（guides.py）＋ビルドスクリプト（fetch.py）が public/ を生成 | build.js＋check.js＋og.py が data/*.json から生成 |
| 依存 | Python 標準ライブラリのみ | Node＋フォント取得（ビルド15〜26分かかるときがある） |
| 新規ページの登録 | データに1件追加するだけ | guides.json と order.json の二重登録が必須（片方欠けで事故の前例あり） |
| 運用実績 | 週次バッチで繰り返し運用済み、手順が手に馴染んでいる | 同左だが、登録漏れ・ogImage 形式などの固有の落とし穴が多い |

理由：園芸サイトは記事データの追加が中心で、kitchen 型の「データ1件追加→ビルド」が最も素直。
ビルドが速く依存もないため、週2〜3本の運用に合う。hakajimai 型の強み（大量の地域ページ生成）は
現時点では不要で、必要になったら後から足せる。

## 構成

```
engei-clinic-site/
  articles.py   記事データ＋カテゴリ/症状ハブの定義（2軸をデータで持つ）
  build.py      ビルドスクリプト（public/ を生成）
  public/       生成物（トップ・/category/<key>/・/symptom/<key>/・/guide/<slug>/・sitemap.xml・robots.txt・404.html）
  README.md     このファイル
```

- カテゴリ軸: 野菜（yasai）／観葉植物（kannyou）／果樹・庭木（kaju）／花・バラ（hana）
- 症状軸: 葉の症状（ha）／実のトラブル（mi）／株全体の異変（kabu）／害虫（gaichu）
- canonical は `https://engei-clinic.com` 前提（`build.py` の `BASE`）
- 記事テンプレートと書き方の注意（病害の同定を断定しない、農薬は登録確認済みのみ等）は
  `articles.py` の冒頭コメントに明記。FAQ は5件まで（build.py がチェック）

## ビルド手順

```bash
cd ~/workspace/engei-clinic-site
python3 build.py
```

`public/` が再生成される。生成物をブラウザで確認する場合は任意の静的サーバーで
`public/` を配信する（例: `python3 -m http.server -d public 8000`）。

## プレースホルダ（ドメイン確定後に差し込む）

- **GA4 測定ID**: GA4 でプロパティを作成 → `build.py` の `GA4_ID` に `G-…` を設定 → 再ビルド。
  空の間は計測タグ自体を出力しない。
- **GSC 所有権確認**: Search Console に engei-clinic.com を登録 → HTML タグ方式の
  content 値を `build.py` の `GSC_VERIFICATION` に設定 → 再ビルド・公開 → GSC で確認を実行。
  （DNS レコード方式で確認する場合はこの値は不要）

## ドメイン確定後の接続チェックリスト

1. [ ] ドメイン engei-clinic.com の取得完了（Cloudflare Registrar 想定）
2. [ ] GitHub リポジトリ作成（例: 888marui/engei-clinic）し、このディレクトリを push
3. [ ] 配信方式を決める：GitHub Pages（public/ を配信）または Cloudflare Pages。
       既存サイトの前例は GitHub Pages＋カスタムドメイン
4. [ ] DNS 設定：カスタムドメイン engei-clinic.com を配信先へ向ける（www の扱いも決める）
5. [ ] HTTPS が有効になり、canonical（https://engei-clinic.com/…）で表示できることを確認
6. [ ] GSC に登録し、所有権確認 → sitemap.xml を送信
7. [ ] GA4 プロパティ作成 → `GA4_ID` を差し込んで再ビルド・再公開 → リアルタイムで計測確認
8. [x] サイト名の正式決定（園芸クリニック、2026-11-27）→ `SITE_NAME` 差し替え済み。ロゴ・og 画像などの最小デザインは別途
9. [ ] 日報の仕組み（既存ラインの変更差分チェック）に engei-clinic.com を追加
10. [ ] Phase 0 の残件：代表クエリ（E2 トマトの葉、E5 きゅうりうどんこ病、E9 観葉）の
        AI Overview の出方と引用元を実ブラウザで確認（計画書セクション8）

## 残作業（Phase 0 完了まで）

- ドメイン取得と上記接続チェックリストの実施（GitHub push はドメイン確定後）
- サンプル記事（tomato-leaf-yellow）は体裁確認用。本執筆時に一次情報で裏取りし、
  出典URL・確認日を記入してから公開する
- Phase 1 の執筆（需要リスト順に15本、週2〜3本）は基盤接続のあと
