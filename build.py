#!/usr/bin/env python3
"""園芸クリニックの静的ビルド。

articles.py のデータから public/ に HTML を生成する（kitchen-point-note の fetch.py と同じ型）。
使い方: python3 build.py   → public/ 以下にトップ・カテゴリハブ・症状ハブ・記事・sitemap.xml・robots.txt を出力。
依存ライブラリなし（Python 標準ライブラリのみ）。
"""
import csv
import html
import io
import json
import re
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


ORG = {"@type": "Organization", "name": SITE_NAME, "url": BASE + "/"}


def ld_scripts(objs):
    if not objs:
        return ""
    return "".join(
        f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>'
        for o in objs)


def breadcrumb(items):
    """items: [(name, path), ...]（最後は path=None で現在ページ）"""
    els = []
    for i, (name, path) in enumerate(items, 1):
        el = {"@type": "ListItem", "position": i, "name": name}
        if path:
            el["item"] = BASE + path
        els.append(el)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": els}


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def extract_tables(a):
    """記事本文の切り分け表（table.cmp）を構造化データとして取り出す。"""
    out = []
    for t in re.findall(r'<table class="cmp">(.*?)</table>', a["body"], re.S):
        head = re.search(r"<thead>(.*?)</thead>", t, re.S)
        headers = [strip_tags(x) for x in re.findall(r"<th>(.*?)</th>", head.group(1), re.S)] if head else []
        rows = []
        body = re.search(r"<tbody>(.*?)</tbody>", t, re.S)
        scope = body.group(1) if body else t
        for tr in re.findall(r"<tr>(.*?)</tr>", scope, re.S):
            cells = [strip_tags(x) for x in re.findall(r"<td>(.*?)</td>", tr, re.S)]
            if cells:
                rows.append(dict(zip(headers, cells)) if headers and len(headers) == len(cells) else cells)
        out.append({"headers": headers, "rows": rows})
    return out


def ga_tag():
    if not GA4_ID:
        return "<!-- GA4: 測定IDは未設定（README の手順で差し込む） -->"
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>'
        f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}"
        f"gtag('js',new Date());gtag('config','{GA4_ID}');</script>"
    )


def page(path, title, body, desc="", ld=None):
    url = BASE + path
    gsc = f'<meta name="google-site-verification" content="{GSC_VERIFICATION}">' if GSC_VERIFICATION else ""
    doc = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}">
{gsc}{ga_tag()}{ld_scripts(ld)}
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
    url = f'{BASE}/guide/{a["slug"]}/'
    art = {"@context": "https://schema.org", "@type": "Article",
           "headline": a["h1"], "description": a["desc"], "url": url,
           "mainEntityOfPage": url, "dateModified": a["checked"],
           "author": ORG, "publisher": ORG}
    img = re.search(r'<img src="(/assets/[^"]+)"', a["body"])
    if img:
        art["image"] = BASE + img.group(1)
    ld = [art, breadcrumb([("トップ", "/"), (cat["name"], f'/category/{a["cat"]}/'), (a["h1"], None)])]
    if a["faq"]:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage",
                   "mainEntity": [{"@type": "Question", "name": f["q"],
                                   "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                                  for f in a["faq"]]})
    return page(f'/guide/{a["slug"]}/', a["title"], body, a["desc"], ld)


def build_data():
    """各記事の切り分け表を CSV / JSON で公開し、案内ページ（引用ガイド付き）を出す。"""
    records = []
    for a in ARTICLES:
        tables = extract_tables(a)
        records.append({
            "slug": a["slug"],
            "title": a["h1"],
            "url": f'{BASE}/guide/{a["slug"]}/',
            "category": CATEGORIES[a["cat"]]["name"],
            "symptoms": [SYMPTOMS[s]["name"] for s in a["symptoms"]],
            "checked": a["checked"],
            "sources": [s["url"] for s in a["sources"] if s["url"]],
            "tables": tables,
        })
    updated = max(a["checked"] for a in ARTICLES)
    data_dir = OUT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "園芸クリニック 症状の切り分けデータ",
        "description": "園芸・家庭菜園の症状について、様子から原因の候補と判別点を整理した切り分け表のデータ。各記事の一次情報の確認日つき。",
        "url": f"{BASE}/data/",
        "updated": updated,
        "publisher": SITE_NAME,
        "articles": records,
    }
    (data_dir / "symptoms.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["記事slug", "記事タイトル", "記事URL", "カテゴリ", "症状", "列1見出し", "列1", "列2見出し", "列2", "列3見出し", "列3", "確認日"])
    for r in records:
        for t in r["tables"]:
            hs = t["headers"]
            for row in t["rows"]:
                cells = [row.get(h, "") for h in hs] if isinstance(row, dict) else list(row)
                cells = (cells + ["", "", ""])[:3]
                h3 = (hs + ["", "", ""])[:3]
                w.writerow([r["slug"], r["title"], r["url"], r["category"], "・".join(r["symptoms"]),
                            h3[0], cells[0], h3[1], cells[1], h3[2], cells[2], r["checked"]])
    (data_dir / "symptoms.csv").write_text(buf.getvalue(), encoding="utf-8")

    n_rows = sum(len(t["rows"]) for r in records for t in r["tables"])
    body = f"""
<h1>公開データ｜症状の切り分け表（CSV・JSON）</h1>
<p class="lead">園芸クリニックの各記事に入れている「原因の切り分け表」を、機械で読みやすいデータとして公開しています。症状の様子から、原因の候補と判別点を引ける形です。</p>
<h2>ダウンロード</h2>
<ul>
<li><a href="/data/symptoms.json">symptoms.json</a>（記事ごと・表の見出しと行をそのまま構造化）</li>
<li><a href="/data/symptoms.csv">symptoms.csv</a>（1行＝切り分け表の1行に平たくしたもの）</li>
</ul>
<p>収録：記事 {len(records)} 本・切り分け {n_rows} 行（{esc(updated)} 時点）。各レコードに、記事URL・カテゴリ・症状・一次情報の確認日・出典URLを含みます。</p>
<h2>再利用と引用について</h2>
<p>出典として「園芸クリニック（engei-clinic.com）」と記事またはこのページへのリンクを明記いただければ、事前の連絡なしで引用・再利用できます。内容は一次情報（メーカー・自治体・研究機関の公開資料）を確認して整理したものですが、病害の確定診断には使えません。利用する際は、各記事の出典と確認日もあわせてご確認ください。</p>
<h2>データの作り方</h2>
<p>各記事の切り分け表をそのまま機械可読化したものです。表の見出し（例：様子／候補／判別点）は記事ごとに異なる場合があるため、CSV では見出し名も列に入れています。記事を更新すると、このデータも同じ内容に更新されます。</p>
"""
    ld = [
        {"@context": "https://schema.org", "@type": "Dataset",
         "name": "園芸クリニック 症状の切り分けデータ",
         "description": payload["description"], "url": f"{BASE}/data/",
         "dateModified": updated, "creator": ORG,
         "distribution": [
             {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{BASE}/data/symptoms.json"},
             {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{BASE}/data/symptoms.csv"}]},
        breadcrumb([("トップ", "/"), ("公開データ", None)]),
    ]
    return page("/data/", f"公開データ｜{SITE_NAME}", body,
                "園芸クリニックの切り分け表をCSV・JSONで公開。症状の様子・原因の候補・判別点を、確認日と出典つきで再利用できます。", ld)


def build_llms():
    lines = [
        f"# {SITE_NAME}",
        "",
        "> 園芸・家庭菜園のトラブルを、症状から原因の切り分けと対処を探せるサイトです。病害の同定は断定せず、メーカー・自治体・研究機関などの一次情報を確認して書いています。各記事に出典と確認日を載せています。",
        "",
        "## 主要ページ",
        f"- [トップ]({BASE}/)",
    ]
    for k, v in CATEGORIES.items():
        lines.append(f'- [{v["name"]}のトラブル]({BASE}/category/{k}/): {v["desc"]}')
    for k, v in SYMPTOMS.items():
        lines.append(f'- [症状：{v["name"]}]({BASE}/symptom/{k}/): {v["desc"]}')
    lines.append(f"- [公開データ（切り分け表 CSV・JSON）]({BASE}/data/): 各記事の切り分け表を機械可読データで公開。出典明記で再利用可。")
    lines += ["", "## 記事"]
    for a in ARTICLES:
        lines.append(f'- [{a["h1"]}]({BASE}/guide/{a["slug"]}/): {a["desc"]}（確認日 {a["checked"]}）')
    lines.append("")
    return "\n".join(lines)


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
    top_ld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": BASE + "/"},
        {"@context": "https://schema.org", **ORG},
    ]
    urls.append(page("/", f"{SITE_NAME}｜園芸・家庭菜園のトラブル解決",
                     f"<h1>園芸・家庭菜園のトラブル解決</h1>"
                     f"<p class=\"lead\">葉が黄色い、実がならない、急にしおれた——症状から原因の切り分けと対処を探せるサイトです。病害の同定は断定せず、見分け方と相談先まで案内します。</p>"
                     f"{hub_nav()}<h2>記事一覧</h2>{cards}"
                     f"<h2>公開データ</h2><p>各記事の「原因の切り分け表」を、CSV・JSONのデータとして公開しています。再利用の条件と引用のしかたは<a href=\"/data/\">公開データのページ</a>にまとめています。</p>",
                     "園芸・家庭菜園のトラブルを症状から探せるサイト。野菜・観葉植物・果樹・庭木・花バラの症状の見分け方と対処を、一次情報を確認してまとめます。",
                     top_ld))

    # カテゴリハブ
    for key, c in CATEGORIES.items():
        items = [a for a in ARTICLES if a["cat"] == key]
        cards = "".join(article_card(a) for a in items) or "<p>記事は準備中です。</p>"
        ld = [breadcrumb([("トップ", "/"), (c["name"], None)])]
        urls.append(page(f"/category/{key}/", f'{c["name"]}のトラブル｜{SITE_NAME}',
                         f"<h1>{esc(c['name'])}のトラブル</h1><p class=\"lead\">{esc(c['desc'])}</p>{cards}", c["desc"], ld))

    # 症状ハブ
    for key, s in SYMPTOMS.items():
        items = [a for a in ARTICLES if key in a["symptoms"]]
        cards = "".join(article_card(a) for a in items) or "<p>記事は準備中です。</p>"
        ld = [breadcrumb([("トップ", "/"), (s["name"], None)])]
        urls.append(page(f"/symptom/{key}/", f'{s["name"]}｜{SITE_NAME}',
                         f"<h1>{esc(s['name'])}</h1><p class=\"lead\">{esc(s['desc'])}</p>{cards}", s["desc"], ld))

    # 記事
    for a in ARTICLES:
        urls.append(build_article(a))

    # 公開データ（切り分け表の CSV / JSON ＋ 案内ページ）
    urls.append(build_data())

    # llms.txt
    (OUT / "llms.txt").write_text(build_llms(), encoding="utf-8")

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
