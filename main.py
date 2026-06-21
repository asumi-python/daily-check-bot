import os
from datetime import date
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def get_or_create_user(line_user_id):
    result = supabase.table("users").select("*").eq("line_user_id", line_user_id).execute()
    if result.data:
        return result.data[0]
    new_user = supabase.table("users").insert({"line_user_id": line_user_id}).execute()
    return new_user.data[0]


def add_task(user_id, title, is_routine=False):
    supabase.table("tasks").insert({
        "user_id": user_id,
        "title": title,
        "is_routine": is_routine
    }).execute()


def get_tasks(user_id):
    result = supabase.table("tasks").select("*").eq("user_id", user_id).execute()
    return result.data


def complete_task(user_id, title):
    # タイトルが部分一致するタスクを検索
    result = supabase.table("tasks").select("*").eq("user_id", user_id).ilike("title", f"%{title}%").execute()
    if not result.data:
        return None
    task = result.data[0]
    today = date.today().isoformat()
    # 既に完了済みか確認
    existing = supabase.table("task_logs").select("*").eq("task_id", task["id"]).eq("date", today).execute()
    if existing.data:
        return f"「{task['title']}」は今日すでに完了済みです！"
    supabase.table("task_logs").insert({
        "task_id": task["id"],
        "user_id": user_id,
        "date": today,
        "is_done": True
    }).execute()
    return f"「{task['title']}」を完了しました！お疲れさまでした！"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@app.route("/")
def index():
    return "毎日チェックBot 動いてます！"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text.strip()
    line_user_id = event.source.user_id
    user = get_or_create_user(line_user_id)
    user_id = user["id"]

    if user_message.startswith("追加 "):
        title = user_message[3:]
        add_task(user_id, title)
        reply = f"「{title}」をタスクに追加しました！"

    elif user_message.startswith("ルーティン追加 "):
        title = user_message[8:]
        add_task(user_id, title, is_routine=True)
        reply = f"「{title}」をルーティンタスクに追加しました！"

    elif user_message == "タスク一覧":
        tasks = get_tasks(user_id)
        if tasks:
            today = date.today().isoformat()
            done_ids = {
                log["task_id"]
                for log in supabase.table("task_logs").select("task_id").eq("user_id", user_id).eq("date", today).execute().data
            }
            task_list = "\n".join([
                f"{'✅' if t['id'] in done_ids else '・'}{t['title']}"
                for t in tasks
            ])
            reply = f"📋 タスク一覧\n{task_list}"
        else:
            reply = "タスクはまだありません。\n「追加 タスク名」で追加できます！"

    elif user_message.startswith("完了 "):
        title = user_message[3:]
        result = complete_task(user_id, title)
        if result is None:
            reply = f"「{title}」というタスクが見つかりませんでした。"
        else:
            reply = result

    else:
        reply = "コマンド一覧：\n・追加 タスク名\n・ルーティン追加 タスク名\n・タスク一覧\n・完了 タスク名"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )


if __name__ == "__main__":
    app.run(port=5000)