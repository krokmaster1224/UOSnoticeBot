import ssl
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 맥(Mac) SSL 인증서 에러 방지
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# ==========================================
# [설정 영역] 본인의 정보로 꼭 수정해 주세요!
# ==========================================
GMAIL_ADDRESS = "ilikemovie12@gmail.com"
GMAIL_APP_PASSWORD = "vihs pcjg fesw jfjj"  # 띄어쓰기 없이 16글자만 입력해도 됩니다

# 서울시립대학교 공지사항 RSS 주소
rss_urls = {
    "전체공지": "https://www.uos.ac.kr/rss/allBoard.do",
    "학사공지": "https://www.uos.ac.kr/rss/hBoard.do",
    "장학공지": "https://www.uos.ac.kr/rss/sBoard.do"
}

# 내가 관심 있는 키워드 설정
my_keywords = ["장학", "수강", "신청", "모집", "인턴", "공모전", "철학", "미디어"]
# ==========================================

def build_email_html():
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    html_content = f"<h2>📢 서울시립대학교 맞춤 공지사항 ({today_str})</h2>"
    html_content += f"<p>설정하신 키워드(<b>{', '.join(my_keywords)}</b>)로 걸러낸 최신 공지입니다.</p><hr>"
    
    total_matched = 0

    for category, url in rss_urls.items():
        feed = feedparser.parse(url)
        category_items = ""
        
        for entry in feed.entries[:20]:
            title = entry.title
            link = entry.link
            published = entry.get('published', '날짜 정보 없음')
            
            if any(keyword in title for keyword in my_keywords):
                total_matched += 1
                category_items += f"""
                <li style="margin-bottom: 12px;">
                    <a href="{link}" style="font-size: 16px; font-weight: bold; color: #1a73e8; text-decoration: none;">{title}</a><br>
                    <span style="font-size: 12px; color: #666;">📅 작성일: {published}</span>
                </li>
                """
        
        if category_items:
            html_content += f"<h3>📌 [{category}]</h3><ul>{category_items}</ul>"
            
    if total_matched == 0:
        return None
        
    return html_content

def send_gmail(html_body):
    msg = MIMEMultipart("alternative")
    today_str = datetime.now().strftime("%m/%d")
    msg["Subject"] = f"[시립대 공지봇] {today_str} 맞춤 공지사항 정리"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS  # 나에게 보내기

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # Gmail SMTP 서버 연결 및 발송
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("✅ 이메일이 성공적으로 발송되었습니다! Gmail 메일함을 확인해 보세요.")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")

if __name__ == "__main__":
    print("공지사항을 수집하고 있습니다...")
    email_html = build_email_html()
    
    if email_html:
        print("맞춤 공지를 찾았습니다. 이메일을 발송합니다...")
        send_gmail(email_html)
    else:
        print("조건에 맞는 공지가 없어 이메일을 발송하지 않았습니다.")
