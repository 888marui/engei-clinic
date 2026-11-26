#!/usr/bin/env python3
"""園芸クリニックの静的ビルド。

articles.py のデータから public/ に HTML を生成する（kitchen-point-note の fetch.py と同じ型）。
使い方: python3 build.py   → public/ 以下にトップ・カテゴリハブ・症状ハブ・記事・sitemap.xml・robots.txt を出力。
依存ライブラリなし（Python 標準ライブラリのみ）。
"""
import html
import shutil
from pathlib import Path

from articles import ARTICLES, CATEGORIES, SYMPTOMS

BASE = "https://engei-clinic.com"
SITE_NAME = "園芸クリニック"  # 2026-11-27 正式決定
OUT = Path(__file__).parent / "public"

# --- ドメイン確定後に差し込むプレースホルダ（手順は README.md） ---
GA4_ID = "G-N5HMER8B3F"  # engei-clinic プロパティ（2026-11-27 作成）。空なら計測タグを出さない
GSC_VERIFICATION = ""  # Google Search Console の所有権確認メタタグの content 値。空なら出さない

CSS = """*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic UI",Meiryo,sans-serif;color:#26302a;background:#fbfbf8;line-height:1.8}
a{color:#2e6b34}header.site{background:#2e6b34;color:#fff;padding:14px 16px}header.site a{color:#fff;text-decoration:none;font-weight:700;font-size:20px}header.site .tag{display:block;font-size:12px;font-weight:400;opacity:.85}
main{max-width:760px;margin:0 auto;padding:20px 16px 48px}h1{font-size:26px;line-height:1.45;margin:8px 0 12px}h2{font-size:20px;border-left:5px solid #2e6b34;padding-left:10px;margin:32px 0 12px}h3{font-size:17px;margin:24px 0 8px}
.lead{color:#4c5a50}.conclusion{background:#eef5ee;border:1px solid #cfe0cf;border-radius:8px;padding:14px 16px}.conclusion b{display:block;margin-bottom:4px}
table.cmp{border-collapse:collapse;width:100%;margin:12px 0;font-size:15px}table.cmp th,table.cmp td{border:1px solid #d5ddd5;padding:8px 10px;text-align:left;vertical-align:top}table.cmp thead th{background:#eef5ee}
ul.chk{padding-left:20px}figure.photo{margin:16px 0}figure.photo img{max-width:100%;height:auto;border-radius:6px;display:block}figure.photo figcaption{font-size:13px;color:#66736a;margin-top:4px}.figcap{font-size:13px;color:#66736a}.card{border:1px solid #d5ddd5;border-radius:8px;padding:12px 16px;margin:10px 0;background:#fff}.card a{font-weight:700;text-decoration:none}
nav.hubs{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}nav.hubs a{border:1px solid #2e6b34;border-radius:999px;padding:4px 14px;text-decoration:none;font-size:14px}
footer.site{border-top:1px solid #d5ddd5;padding:16px;font-size:13px;color:#66736a;text-align:center}.faq h3{margin-bottom:4px}.src{font-size:14px}
"""


def esc(s):
    return html.escape(s, quote=True)


def ga_tag():
    if not GA4_ID:
        return "<!-- GA4: 測定IDは未設定（README の手順で差し込む） -->"
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>'
        f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}"
        f"gtag('js',new Date());gtag('config','{GA4_ID}');</script>"
    )


def page(path, title, body, desc=""):
    url = BASE + path
    gsc = f'<meta name="google-site-verification" content="{GSC_VERIFICATION}">' if GSC_VERIFICATION else ""
    doc = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}">
{gsc}{ga_tag()}
<style>{CSS}</style></head>
<body>
<header class="site"><a href="/">{SITE_NAME}</a><span class="tag">園芸・家庭菜園のトラブル解決（症状から探せる）</span></header>
<main>
{body}
</main>
<footer class="site">{SITE_NAME}｜病害の確定診断はできません。判断に迷う場合は地域の病害虫防除所・JAにご相談ください。</footer>
</body></html>
"""
    dest = OUT / path.strip("/")
    if path == "/":
        dest = OUT
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(doc, encoding="utf-8")
    return path


def article_card(a):
    return f'<div class="card"><a href="/guide/{a["slug"]}/">{esc(a["h1"])}</a><p>{esc(a["desc"])}</p></div>'


def hub_nav():
    cats = "".join(f'<a href="/category/{k}/">{esc(v["name"])}</a>' for k, v in CATEGORIES.items())
    syms = "".join(f'<a href="/symptom/{k}/">{esc(v["name"])}</a>' for k, v in SYMPTOMS.items())
    return f"<h2>対象から探す</h2><nav class=\"hubs\">{cats}</nav><h2>症状から探す</h2><nav class=\"hubs\">{syms}</nav>"


def build_article(a):
    if len(a["faq"]) > 5:
        raise ValueError(f'{a["slug"]}: FAQ は5件まで（現在 {len(a["faq"])} 件）')
    faq = "".join(f'<h3>Q. {esc(f["q"])}</h3><p>{esc(f["a"])}</p>' for f in a["faq"])
    srcs = []
    for s in a["sources"]:
        if s["url"]:
            srcs.append(f'<li><a href="{esc(s["url"])}" rel="nofollow noopener" target="_blank">{esc(s["label"])}</a></li>')
        else:
            srcs.append(f"<li>{esc(s['label'])}</li>")
    cat = CATEGORIES[a["cat"]]
    sym_names = "・".join(SYMPTOMS[s]["name"] for s in a["symptoms"])
    body = f"""
<p class="figcap"><a href="/category/{a['cat']}/">{esc(cat['name'])}</a>｜症状：{esc(sym_names)}</p>
<h1>{esc(a["h1"])}</h1>
<p class="lead">{esc(a["lead"])}</p>
<div class="conclusion"><b>結論</b>{esc(a["conclusion"])}</div>
{a["body"]}
<div class="faq"><h2>よくある質問</h2>{faq}</div>
<h2>出典・確認日</h2>
<ul class="src">{''.join(srcs)}</ul>
<p class="figcap">確認日：{esc(a["checked"])}（確認できた範囲だけを書いています）</p>
"""
    return page(f'/guide/{a["slug"]}/', a["title"], body, a["desc"])


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    # 写真などの静的アセット（assets/ があれば public/assets/ へそのままコピー）
    assets = Path(__file__).parent / "assets"
    if assets.exists():
        shutil.copytree(assets, OUT / "assets")
    urls = []

    # トップ
    cards = "".join(article_card(a) for a in ARTICLES)
    urls.append(page("/", f"{SITE_NAME}｜園芸・家庭菜園のトラブル解決",
                     f"<h1>園芸・家庭菜園のトラブル解決</h1>"
                     f"<p class=\"lead\">葉が黄色い、実がならない、急にしおれた——症状から原因の切り分けと対処を探せるサイトです。病害の同定は断定せず、見分け方と相談先まで案内します。</p>"
                     f"{hub_nav()}<h2>記事一覧</h2>{cards}",
                     "園芸・家庭菜園のトラブルを症状から探せるサイト。野菜・観葉植物・果樹・庭木・花バラの症状の見分け方と対処を、一次情報を確認してまとめます。"))

    # カテゴリハブ
    for key, c in CATEGORIES.items():
        items = [a for a in ARTICLES if a["cat"] == key]
        cards = "".join(article_card(a) for a in items) or "<p>記事は準備中です。</p>"
        urls.append(page(f"/category/{key}/", f'{c["name"]}のトラブル｜{SITE_NAME}',
                         f"<h1>{esc(c['name'])}のトラブル</h1><p class=\"lead\">{esc(c['desc'])}</p>{cards}", c["desc"]))

    # 症状ハブ
    for key, s in SYMPTOMS.items():
        items = [a for a in ARTICLES if key in a["symptoms"]]
        cards = "".join(article_card(a) for a in items) or "<p>記事は準備中です。</p>"
        urls.append(page(f"/symptom/{key}/", f'{s["name"]}｜{SITE_NAME}',
                         f"<h1>{esc(s['name'])}</h1><p class=\"lead\">{esc(s['desc'])}</p>{cards}", s["desc"]))

    # 記事
    for a in ARTICLES:
        urls.append(build_article(a))

    # sitemap.xml / robots.txt
    sm = "".join(f"<url><loc>{BASE}{u}</loc></url>" for u in urls)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n', encoding="utf-8")
    (OUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Content-Signal: search=yes, ai-input=yes, ai-train=yes\n"
        "Allow: /\n\n"
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        f"Sitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    (OUT / "404.html").write_text(
        f"<!DOCTYPE html><html lang=\"ja\"><head><meta charset=\"utf-8\"><title>ページが見つかりません｜{SITE_NAME}</title></head>"
        f"<body><h1>ページが見つかりません</h1><p><a href=\"/\">トップへ戻る</a></p></body></html>\n", encoding="utf-8")

    print(f"built {len(urls)} pages -> {OUT}")


if __name__ == "__main__":
    main()
