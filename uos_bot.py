import os
import ssl
import json
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
        for entry in feed.entries[:60]:
            link = entry.link
            if link not in visited_in_run:
                visited_in_run.add(link)
                pub_raw = entry.get("published", "")
                pub_date = pub_raw[:10] if pub_raw else datetime.now().strftime("%Y-%m-%d")
                all_entries.append({
                    "category": category,
                    "title": entry.title,
                    "link": link,
                    "published": pub_date
                })

    categorized = {}
    banner_notices = []

    for kw in my_keywords:
        new_items = []
        old_items = []
        for item in all_entries:
            if kw in item["title"]:
                is_new = item["link"] not in seen_links
                if is_new:
                    new_items.append((item, True))
                else:
                    old_items.append((item, False))
                
                banner_notices.append({
                    "kw": kw,
                    "category": item["category"],
                    "title": item["title"],
                    "link": item["link"],
                    "published": item["published"]
                })
        
        combined = (new_items + old_items)[:MAX_PER_KEYWORD]
        if combined:
            categorized[kw] = combined
            for item, _ in combined:
                newly_seen_links.add(item["link"])

    save_seen_links(newly_seen_links)
    return categorized, banner_notices

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

def generate_notion_banner(banner_notices):
    today_str = datetime.now().strftime("%m.%d %H:%M")
    
    notices_json = json.dumps(banner_notices, ensure_ascii=False)
    keywords_json = json.dumps(my_keywords, ensure_ascii=False)
    rss_json = json.dumps(rss_urls, ensure_ascii=False)

    banner_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UOS Notice Banner</title>
<style>
  :root {{
    --bg: #ffffff; --card: #f7f6f3; --text: #37352f; --sub: #787774;
    --border: #e9e9e7; --accent: #2383e2; --new-bg: #e8f0fe; --star: #f5a623;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #191919; --card: #202020; --text: #ffffffcf; --sub: #9b9b9b;
      --border: #2f2f2f; --accent: #529cca; --new-bg: #1f3042; --star: #f5c518;
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard", sans-serif;
    background: var(--bg); color: var(--text);
    /* 노션 상단 임베드 메뉴바에 버튼이 가려지지 않도록 상단 여백을 넉넉하게 확보 */
    padding: 38px 14px 12px 14px;
  }}
  .banner {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px; flex-wrap: wrap; gap: 10px;
  }}
  .title-area {{ font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 6px; }}
  .update-time {{ font-size: 11px; color: var(--sub); font-weight: 400; }}
  .tabs {{ display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }}
  .tab {{
    background: var(--bg); border: 1px solid var(--border); color: var(--sub);
    font-size: 11px; padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: 0.15s;
  }}
  .tab.active, .tab:hover {{
    background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600;
  }}
  .refresh-btn {{
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    font-size: 12px; padding: 3px 7px; border-radius: 6px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; transition: 0.2s;
  }}
  .refresh-btn:hover {{ background: var(--border); }}
  @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
  .spinning {{ display: inline-block; animation: spin 0.8s linear infinite; }}
  .list {{
    display: flex; flex-direction: column; gap: 6px;
    max-height: 225px; overflow-y: auto; padding-right: 4px;
  }}
  .notice-item {{
    display: flex; align-items: center; gap: 7px; font-size: 13px;
    padding: 6px 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border);
  }}
  .old-item {{ font-style: italic; opacity: 0.68; }}
  .star-btn {{
    background: none; border: none; cursor: pointer; font-size: 15px;
    line-height: 1; color: var(--sub); padding: 0 2px; font-style: normal;
  }}
  .star-btn.starred {{ color: var(--star); }}
  .badge {{
    font-size: 10px; padding: 2px 5px; border-radius: 4px; font-weight: 600; white-space: nowrap;
  }}
  .badge.new {{ background: var(--new-bg); color: var(--accent); font-style: normal; }}
  .badge.old {{ background: var(--border); color: var(--sub); font-style: normal; }}
  .badge.kw {{ background: transparent; border: 1px solid var(--border); color: var(--sub); font-style: normal; }}
  .title {{
    color: var(--text); text-decoration: none; flex: 1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer;
  }}
  .new-item .title {{ font-weight: 600; color: var(--accent); }}
  .old-item .title {{ color: var(--sub); font-style: italic; }}
  .title:hover {{ text-decoration: underline; }}
  .date {{ font-size: 11px; color: var(--sub); white-space: nowrap; font-style: normal; }}
  .empty {{ font-size: 12px; color: var(--sub); padding: 18px 0; text-align: center; }}
</style>
</head>
<body>
<div class="banner">
  <div class="header">
    <div class="title-area">
      📢 시립대 맞춤 공지 <span class="update-time" id="update-time">({today_str} 업데이트)</span>
    </div>
    <div class="tabs" id="tabs-container"></div>
  </div>
  <div class="list" id="notice-list"></div>
</div>

<script>
const KEYWORDS = {keywords_json};
const MAX_PER_KW = {MAX_PER_KEYWORD};
const RSS_URLS = {rss_json};
let rawNotices = {notices_json};
let currentTab = 'ALL';

// 1. 브라우저 로컬 저장소에서 읽은 글(클릭한 글) 및 즐겨찾기 목록 불러오기
let clickedLinks = new Set(JSON.parse(localStorage.getItem('uos_clicked_links') || '[]'));
let favoritesMap = JSON.parse(localStorage.getItem('uos_favorites_map') || '{{}}');

function saveState() {{
  localStorage.setItem('uos_clicked_links', JSON.stringify([...clickedLinks]));
  localStorage.setItem('uos_favorites_map', JSON.stringify(favoritesMap));
}}

// 2. 공지 클릭 시 즉시 읽음(회색 기울임꼴 + 하단 이동) 처리
function markAsRead(link) {{
  clickedLinks.add(link);
  if (favoritesMap[link]) {{
    favoritesMap[link].read = true;
  }}
  saveState();
  setTimeout(renderList, 80);
}}

// 3. 즐겨찾기 별표 토글 (영구 보관)
function toggleStar(event, itemStr) {{
  event.stopPropagation();
  const item = JSON.parse(decodeURIComponent(itemStr));
  if (favoritesMap[item.link]) {{
    delete favoritesMap[item.link];
  }} else {{
    favoritesMap[item.link] = {{
      kw: item.kw || '즐겨찾기',
      category: item.category || '공지',
      title: item.title,
      link: item.link,
      published: item.published
    }};
  }}
  saveState();
  renderTabs();
  renderList();
}}

// 4. 상단 카테고리 버튼 및 새로고침 버튼 렌더링
function renderTabs() {{
  const container = document.getElementById('tabs-container');
  const favCount = Object.keys(favoritesMap).length;
  let html = `<button class="tab ${{currentTab === 'ALL' ? 'active' : ''}}" onclick="switchTab('ALL')">전체</button>`;
  html += `<button class="tab ${{currentTab === 'FAV' ? 'active' : ''}}" onclick="switchTab('FAV')">⭐ 즐겨찾기${{favCount ? ' (' + favCount + ')' : ''}}</button>`;
  
  KEYWORDS.forEach(kw => {{
    html += `<button class="tab ${{currentTab === kw ? 'active' : ''}}" onclick="switchTab('${{kw}}')">${{kw}}</button>`;
  }});
  
  html += `<button class="refresh-btn" id="refresh-btn" onclick="refreshLive()" title="지금 공지 다시 긁어오기"><span id="refresh-icon">🔄</span></button>`;
  container.innerHTML = html;
}}

function switchTab(tab) {{
  currentTab = tab;
  renderTabs();
  renderList();
}}

// 5. 공지 리스트 렌더링 (안 읽은 새 글은 상단, 클릭한 글은 하단 배치)
function renderList() {{
  const listEl = document.getElementById('notice-list');
  let displayItems = [];

  if (currentTab === 'FAV') {{
    // 즐겨찾기 탭: 날짜가 지나도 사라지지 않으며 공지 게시 날짜 최신순 정렬
    displayItems = Object.values(favoritesMap).sort((a, b) => (b.published || '').localeCompare(a.published || ''));
  }} else {{
    const targetKws = currentTab === 'ALL' ? KEYWORDS : [currentTab];
    targetKws.forEach(kw => {{
      const kwItems = rawNotices.filter(n => n.kw === kw);
      // 아직 클릭하지 않은 글(새 글)과 이미 클릭한 글(이전 글) 분리
      const unread = kwItems.filter(n => !clickedLinks.has(n.link));
      const read = kwItems.filter(n => clickedLinks.has(n.link));
      // 새 글을 먼저 위로 올리고, 이미 클릭한 글은 아래로 배치해 최대 개수만큼 표시
      const combined = [...unread, ...read].slice(0, MAX_PER_KW);
      displayItems.push(...combined);
    }});
  }}

  if (displayItems.length === 0) {{
    listEl.innerHTML = `<div class="empty">${{currentTab === 'FAV' ? '☆ 버튼을 눌러 중요한 공지를 즐겨찾기에 추가해 보세요.' : '현재 해당 키워드의 최근 공지가 없습니다.'}}</div>`;
    return;
  }}

  listEl.innerHTML = displayItems.map(item => {{
    const isRead = clickedLinks.has(item.link);
    const isStarred = !!favoritesMap[item.link];
    const itemEncoded = encodeURIComponent(JSON.stringify(item));
    
    return `
      <div class="notice-item ${{isRead ? 'old-item' : 'new-item'}}">
        <button class="star-btn ${{isStarred ? 'starred' : ''}}" onclick="toggleStar(event, '${{itemEncoded}}')" title="즐겨찾기">${{isStarred ? '⭐' : '☆'}}</button>
        <span class="badge ${{isRead ? 'old' : 'new'}}">${{isRead ? '이전' : 'NEW'}}</span>
        <span class="badge kw">${{item.kw}}</span>
        <a href="${{item.link}}" target="_blank" class="title" onclick="markAsRead('${{item.link}}')">${{item.title}}</a>
        <span class="date">${{item.published}}</span>
      </div>
    `;
  }}).join('');
}}

// 6. 실시간 새로고침 (버튼 클릭 시 시립대 RSS를 즉시 다시 긁어옴)
async function refreshLive() {{
  const icon = document.getElementById('refresh-icon');
  const timeEl = document.getElementById('update-time');
  icon.classList.add('spinning');
  timeEl.textContent = '(공지 다시 불러오는 중...)';

  try {{
    const fetchedEntries = [];
    const visited = new Set();

    for (const [category, url] of Object.entries(RSS_URLS)) {{
      const apiUrl = `https://api.rss2json.com/v1/api.json?rss_url=${{encodeURIComponent(url)}}`;
      const res = await fetch(apiUrl);
      const data = await res.json();
      if (data && data.items) {{
        data.items.forEach(entry => {{
          if (!visited.has(entry.link)) {{
            visited.add(entry.link);
            const pubDate = (entry.pubDate || '').substring(0, 10);
            fetchedEntries.push({{
              category: category,
              title: entry.title,
              link: entry.link,
              published: pubDate
            }});
          }}
        }});
      }}
    }}

    if (fetchedEntries.length > 0) {{
      const updatedNotices = [];
      KEYWORDS.forEach(kw => {{
        fetchedEntries.forEach(item => {{
          if (item.title.includes(kw)) {{
            updatedNotices.push({{
              kw: kw,
              category: item.category,
              title: item.title,
              link: item.link,
              published: item.published
            }});
          }}
        }});
      }});
      rawNotices = updatedNotices;
      renderList();
    }} else {{
      // 외부 프록시 제한 시 GitHub Pages 최신 데이터 재호출
      const pageRes = await fetch(window.location.pathname + '?t=' + Date.now(), {{ cache: 'no-store' }});
      if (pageRes.ok) {{
        window.location.reload();
        return;
      }}
    }}

    const now = new Date();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const hh = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    timeEl.textContent = `(${{mm}}.${{dd}} ${{hh}}:${{min}} 실시간 갱신됨)`;
  }} catch (e) {{
    timeEl.textContent = '(새로고침 완료)';
  }} finally {{
    icon.classList.remove('spinning');
  }}
}}

// 초기 실행
renderTabs();
renderList();
</script>
</body>
</html>"""

    with open(BANNER_FILE, "w", encoding="utf-8") as f:
        f.write(banner_html)
    print("✅ 인터랙티브 노션 배너용 index.html 생성 완료!")

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
    categorized_data, banner_notices_data = collect_notices()
    generate_notion_banner(banner_notices_data)
    email_html = build_email_html(categorized_data)
    if email_html:
        send_gmail(html_body=email_html)
