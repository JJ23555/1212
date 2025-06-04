from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import datetime
import requests
import os

app = Flask(__name__)

# LINE Credentials
LINE_CHANNEL_ACCESS_TOKEN = 'WX4PwkShaEW/4EUqkLh6T4ypevbw4xfwYdS/gFoMK2HDucH/VRjpczJBT+o2h53rXPwHhOEDWiNIdJkR8M5Z6gizHivIUOJCmKAL4k3xfWc0cdpG22qqwS+2GnDHR9yzbzuHrctHPv0A7AO1TX+CQQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '9c8d9c31c064b594010fb301a28c68e0'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Google Apps Script Webhook
GOOGLE_SHEET_WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycbx-s5LuAdgRZKQbWWmdNi0g0alFH0CYLOjvIyO2WyJBLS1NniPHsBSy7J9j1KcGjoNP/exec'

# ข้อมูลจำลอง (ดึงจาก Google Sheet จริงก็ได้)
from collections import defaultdict
quiz_data = defaultdict(list)  # {student_id: [{score: 1, name: "..."}, ...]}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("Error:", e)
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()

    # รูปแบบส่งคำตอบ: รหัส:65050001,ชื่อ:สมชาย ใจดี,ข้อ:1,คำตอบ:B,คะแนน:1
    if user_text.startswith("รหัส:"):
        try:
            parts = user_text.split(",")
            student_id = parts[0].split(":")[1]
            name = parts[1].split(":")[1]
            question_no = int(parts[2].split(":")[1])
            answer = parts[3].split(":")[1]
            score = int(parts[4].split(":")[1])

            # ส่งข้อมูลไป Google Apps Script
            payload = {
                "student_id": student_id,
                "name": name,
                "question_no": question_no,
                "answer": answer,
                "score": score
            }
            requests.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload)

            # เก็บในหน่วยความจำจำลอง (หรือ query Google Sheet จริงก็ได้)
            quiz_data[student_id].append({"score": score, "name": name})

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ บันทึกคำตอบข้อ {question_no} เรียบร้อยแล้ว")
            )
        except:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ รูปแบบไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง")
            )

    elif user_text.startswith("ดูผล"):
        student_id = user_text.replace("ดูผล", "").strip()

        records = quiz_data.get(student_id, [])
        if records:
            name = records[0]['name']
            total = sum([r['score'] for r in records])
            reply = f"📊 ผลคะแนนของ {name} ({student_id})\n"
            reply += f"ทำทั้งหมด {len(records)} ข้อ\n"
            reply += f"ได้คะแนนรวม {total} คะแนน"
        else:
            reply = "❌ ไม่พบข้อมูลของรหัสนี้"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )

if __name__ == "__main__":
    app.run(port=8000)
