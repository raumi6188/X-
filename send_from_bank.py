# -*- coding: utf-8 -*-
"""
原稿バンク posts.json から「次の1本」を取り出し、Gmail SMTP で送信する。
Anthropic API は使わない。送信位置は progress.json に記録する。

必要な環境変数:
    GMAIL_ADDRESS        … 送信元Gmailアドレス
    GMAIL_APP_PASSWORD   … Gmailアプリパスワード(スペース入りでも可)
    TO_ADDRESS           … 送信先(未設定ならGMAIL_ADDRESSと同じ)
"""
import os
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.header import Header

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ローカル実行時のみ .env を読む(無くてもエラーにしない)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass

GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").strip()
TO_ADDRESS = os.environ.get("TO_ADDRESS") or GMAIL_ADDRESS

POSTS_FILE = os.path.join(BASE_DIR, "posts.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = TO_ADDRESS
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [TO_ADDRESS], msg.as_string())


def main():
    posts = load_json(POSTS_FILE, [])
    total = len(posts)
    progress = load_json(PROGRESS_FILE, {"next_index": 0})
    idx = progress.get("next_index", 0)
    today = datetime.date.today().isoformat()

    # ストック切れ: 補充を促すメールを送って終了(進捗は進めない)
    if idx >= total:
        send_email(
            f"【統計×日本株】ストック切れのお知らせ {today}",
            "投稿ストックを使い切りました。次のバッチを補充してください。\n"
            f"（現在 {total} 本すべて送信済み）",
        )
        print("stock exhausted")
        return

    entry = posts[idx]
    post_text = "\n".join(entry["post_lines"])
    remaining = total - (idx + 1)

    body = (
        "■ 投稿原稿（Xにそのまま貼れます）\n"
        f"{post_text}\n\n"
        "--------------------\n"
        "■ 統計的裏付け\n"
        f"{entry['backing']}\n\n"
        "--------------------\n"
        f"（ストック {idx + 1}/{total} 本目・残り {remaining} 本）"
    )
    send_email(f"【統計×日本株 {today}】{entry['topic']}", body)

    # 送信できたら次の位置へ進めて保存
    progress["next_index"] = idx + 1
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

    print(f"sent index={idx} topic={entry['topic']} remaining={remaining}")


if __name__ == "__main__":
    main()
