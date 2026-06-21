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
            continue

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


if __name__ == "__main__":
    send_morning_notify()