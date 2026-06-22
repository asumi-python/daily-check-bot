import os
from supabase import create_client
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))


def send_morning_notify():
    users = supabase.table("users").select("*").execute()

    for user in users.data:
        tasks = supabase.table("tasks").select("*").eq("user_id", user["id"]).execute()

        if not tasks.data:
            message = "今日の始まりです🌏\n\nタスクはまだありません。\n「追加 タスク名」で今日やることを登録しよう！"
        else:
            task_list = "\n".join([f"□ {t['title']}" for t in tasks.data])
            message = f"おはようございます！\n今日のタスクです📋\n\n{task_list}\n\n完了したら「完了 タスク名」と送ってね！"

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user["line_user_id"],
                    messages=[TextMessage(text=message)]
                )
            )
        print(f"{user['line_user_id']} に通知送信完了")


def send_evening_notify():
    from datetime import date
    today = date.today().isoformat()
    users = supabase.table("users").select("*").execute()

    for user in users.data:
        tasks = supabase.table("tasks").select("*").eq("user_id", user["id"]).execute()
        if not tasks.data:
            continue

        done_ids = {
            log["task_id"]
            for log in supabase.table("task_logs").select("task_id").eq("user_id", user["id"]).eq("date", today).execute().data
        }
        undone = [t for t in tasks.data if t["id"] not in done_ids]

        if not undone:
            message = "今日のタスクは全部完了です！お疲れさまでした！✨"
        else:
            task_list = "\n".join([f"□ {t['title']}" for t in undone])
            message = f"夜のリマインドです🌙\nまだ残っているタスクがあります！\n\n{task_list}\n\n「完了 タスク名」で記録しよう！"

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user["line_user_id"],
                    messages=[TextMessage(text=message)]
                )
            )
        print(f"{user['line_user_id']} に夜の通知送信完了")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "evening":
        send_evening_notify()
    else:
        send_morning_notify()