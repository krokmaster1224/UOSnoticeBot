import os
import ssl
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 맥(Mac) 및 환경별 SSL 인증서 에러 방지
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# ==========================================
# [설정 영역] 깃허브 비밀 금고(Secrets)에서 안전하게 불러옵니다
# ==========================================
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

rss_urls = {
    "전체공지": "https://www.uos.ac.kr/rss/allBoard.do",
    "학사공지": "https://www.uos.ac.kr/rss/hBoard.do",
    "장학공지": "https://www.uos.ac.kr/rss/sBoard.do"
}

my_keywords = ["장학", "수강", "신청", "모집", "인턴", "공모전", "철학", "미디어"]
MAX_PER_KEYWORD = 5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(BASE_DIR, "seen_links.txt")
BANNER_FILE = os.path.join(BASE_DIR, "index.html")
# ==========================================

def load_seen_links():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_seen_links(seen_links):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for link in sorted(seen_links):
            f.write(link + "\n")

def collect_notices():
    seen_links = load_seen_links()
    newly_seen_links = set(seen_links)
    
    all_entries = []
    visited_in_run = set()
    
    for category, url in rss_urls.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:50]:
            link = entry.link
            if link not in visited_in_run:
                visited_in_run.add(link)
                all_entries.append({
                    "category": category,
                    "title": entry.title,
                    "link": link,
                    "published": entry.get("published", "날짜 정보 없음")[:10]
                })

    categorized = {}
    for kw in my_keywords:
        new_items = []
        old_items = []
        for item in all_entries:
            if kw in item["title"]:
                if item["link"] not in seen_links:
                    new_items.append((item, True))
                else:
                    old_items.append((item, False))
        
        combined = (new_items + old_items)[:MAX_PER_KEYWORD]
        if combined:
            categorized[kw] = combined
            for item, _ in combined:
                newly_seen_links.add(item["link"])

    save_seen_links(newly_seen_links)
    return categorized

def build_email_html(categorized):
    if not categorized:
        return None
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    html = f"<h2>📢 서울시립대학교 키워드별 맞춤 공지 ({today_str})</h2>"
    html += "<p style='font-size: 13px; color: #555;'>💡 <b>굵은 파란 글씨</b>는 새 공지이며, 하단의 <i>기울어진 회색 글씨</i>는 이전 공지입니다. (키워드당 최대 5개)</p><hr>"
    
    for kw, items in categorized.items():
        kw_html = ""
        for item, is_new in items:
            if is_new:
                kw_html += f"""
                <li style="margin-bottom: 10px;">
                    <span style="background-color: #e8f0fe; color: #1967d2; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">NEW</span>
                    <span style="font-size: 13px; color: #555;">[{item['category']}]</span>
                    <a href="{item['link']}" style="font-size: 15px; font-weight: bold; color: #1a73e8; text-decoration: none;">{item['title']}</a>
                    <span style="font-size: 12px; color: #888;"> ({item['published']})</span>
                </li>"""
            else:
                kw_html += f"""
                <li style="margin-bottom: 8px; font-style: italic; opacity: 0.75;">
                    <span style="font-size: 12px; color: #888;">[이전 · {item['category']}]</span>
                    <a href="{item['link']}" style="font-size: 14px; color: #666; text-decoration: none; font-style: italic;">{item['title']}</a>
                    <span style="font-size: 11px; color: #999;"> ({item['published']})</span>
                </li>"""
        html += f"<h3 style='margin-top: 18px; color: #333;'>🏷️ {kw} (최대 {MAX_PER_KEYWORD}개)</h3><ul>{kw_html}</ul>"
    return html

def generate_notion_banner(categorized):
    today_str = datetime.now().strftime("%m.%d %H:%M 업데이트")
    
    tabs_html = '<button class="tab active" onclick="filterKw(\'ALL\', this)">전체</button>'
    items_html = ""
    
    for kw, items in categorized.items():
        tabs_html += f'<button class="tab" onclick="filterKw(\'{kw}\', this)">{kw}</button>'
        for item, is_new in items:
            if is_new:
                items_html += f"""
                <div class="notice-item new-item" data-kw="{kw}">
                    <span class="badge new">NEW</span>
                    <span class="badge kw">{kw}</span>
                    <a href="{item['link']}" target="_blank" class="title">{item['title']}</a>
                    <span class="date">{item['published']}</span>
                </div>"""
            else:
                items_html += f"""
                <div class="notice-item old-item" data-kw="{kw}">
                    <span class="badge old">이전</span>
                    <span class="badge kw">{kw}</span>
                    <a href="{item['link']}" target="_blank" class="title">{item['title']}</a>
                    <span class="date">{item['published']}</span>
                </div>"""

    if not items_html:
        items_html = '<div class="empty">현재 설정된 키워드에 해당하는 공지가 없습니다.</div>'

    banner_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UOS Notice Banner</title>
<style>
  :root {{
    --bg: #ffffff; --card: #f7f6f3; --text: #37352f; --sub: #787774;
    --border: #e9e9e7; --accent: #2383e2; --new-bg: #e8f0fe;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #191919; --card: #202020; --text: #ffffffcf; --sub: #9b9b9b;
      --border: #2f2f2f; --accent: #529cca; --new-bg: #1f3042;
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif;
    background: var(--bg); color: var(--text); padding: 12px 14px;
  }}
  .banner {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px; /* 상단 베젤(여백)을 위아래로 넉넉하게 확장 */
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px; flex-wrap: wrap; gap: 10px;
  }}
  .title-area {{ font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 6px; }}
  .update-time {{ font-size: 11px; color: var(--sub); font-weight: 400; }}
  .tabs {{ display: flex; gap: 5px; flex-wrap: wrap; }}
  .tab {{
    background: var(--bg); border: 1px solid var(--border); color: var(--sub);
    font-size: 11px; padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: 0.15s;
  }}
  .tab.active, .tab:hover {{
    background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600;
  }}
  .list {{
    display: flex; flex-direction: column; gap: 6px;
    max-height: 220px; overflow-y: auto; padding-right: 4px;
  }}
  .notice-item {{
    display: flex; align-items: center; gap: 7px; font-size: 13px;
    padding: 6px 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border);
  }}
  .old-item {{ font-style: italic; opacity: 0.68; }}
  .badge {{
    font-size: 10px; padding: 2px 5px; border-radius: 4px; font-weight: 600; white-space: nowrap;
  }}
  .badge.new {{ background: var(--new-bg); color: var(--accent); font-style: normal; }}
  .badge.old {{ background: var(--border); color: var(--sub); font-style: normal; }}
  .badge.kw {{ background: transparent; border: 1px solid var(--border); color: var(--sub); font-style: normal; }}
  .title {{
    color: var(--text); text-decoration: none; flex: 1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .new-item .title {{ font-weight: 600; color: var(--accent); }}
  .title:hover {{ text-decoration: underline; }}
  .date {{ font-size: 11px; color: var(--sub); white-space: nowrap; font-style: normal; }}
</style>
</head>
<body>
<div class="banner">
  <div class="header">
    <div class="title-area">
      🏫 UOS ANNOUNCEMENT <span class="update-time">({today_str})</span>
    </div>
    <div class="tabs">{tabs_html}</div>
  </div>
  <div class="list" id="notice-list">{items_html}</div>
</div>
<script>
function filterKw(kw, btn) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.notice-item').forEach(el => {{
    el.style.display = (kw === 'ALL' || el.dataset.kw === kw) ? 'flex' : 'none';
  }});
}}
</script>
</body>
</html>"""

    with open(BANNER_FILE, "w", encoding="utf-8") as f:
        f.write(banner_html)
    print("✅ 노션 배너용 index.html 생성 완료!")

def send_gmail(html_body):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("⚠️ 이메일 또는 앱 비밀번호 환경변수가 설정되지 않아 메일 발송을 건너뜁니다.")
        return
    msg = MIMEMultipart("alternative")
    today_str = datetime.now().strftime("%m/%d")
    msg["Subject"] = f"[시립대 공지봇] {today_str} 키워드별 맞춤 공지 정리"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("✅ 이메일 발송 완료!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")

if __name__ == "__main__":
    categorized_data = collect_notices()
    generate_notion_banner(categorized_data)
    email_html = build_email_html(categorized_data)
    if email_html:
        send_gmail(html_body=email_html)
