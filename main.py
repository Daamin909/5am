from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta, timezone
import pytz
import time
import os
import traceback
from dotenv import load_dotenv


load_dotenv()


# ---------------- CONFIG ----------------
CHANNEL_ID = "C087L4MB2V9"
USER_ID = "U07GLQY6UN4"
SLACK_TOKEN=os.getenv("SLACK_TOKEN")
TEST_MODE = False
# ----------------------------------------

client = WebClient(token=SLACK_TOKEN)
IST = pytz.timezone("Asia/Kolkata")


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def fetch_messages(start_time):
    messages = []
    start_ts = start_time.timestamp()
    cursor = None
    total_fetched = 0

    while True:
        try:
            resp = client.conversations_history(
                channel=CHANNEL_ID,
                oldest=start_ts,
                cursor=cursor,
                limit=200
            )
        except SlackApiError as e:
            raise
        except Exception as e:
            raise

        batch = resp.get("messages", [])
        fetched_count = len(batch)
        total_fetched += fetched_count

        messages.extend(batch)

        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return messages


def parse_msg_datetime_ts(ts_str):
    dt_utc = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
    dt_ist = dt_utc.astimezone(IST)
    return dt_ist


def get_early_days(messages, after_hour=3.5, before_hour=6):
    days = set()
    count_user_msgs = 0
    count_early_msgs = 0

    for msg in messages:
        if msg.get("user") != USER_ID:
            continue
        count_user_msgs += 1
        ts = msg.get("ts")
        if not ts:
            continue

        try:
            msg_dt_ist = parse_msg_datetime_ts(ts)
        except Exception:
            continue

        after_h = int(after_hour)
        after_m = int((after_hour - after_h) * 60)

        after_time = msg_dt_ist.replace(hour=after_h, minute=after_m, second=0, microsecond=0)
        before_time = msg_dt_ist.replace(hour=before_hour, minute=0, second=0, microsecond=0)

        if after_time <= msg_dt_ist < before_time:
            days.add(msg_dt_ist.date())
            count_early_msgs += 1

    return days



def formatted_dates(days):
    return [f"{ordinal(d.day)} {d.strftime('%B, %Y')}" for d in sorted(days)]


def post_message_and_thread(text, thread_text):
    try:
        main = client.chat_postMessage(channel=CHANNEL_ID, text=text)
    except SlackApiError as e:
        raise
    except Exception as e:
        raise

    thread_ts = main["ts"]
    try:
        thread_msg = client.chat_postMessage(channel=CHANNEL_ID, thread_ts=thread_ts, text=thread_text)
    except SlackApiError as e:
        raise
    except Exception as e:
        raise

    return main, thread_msg


def build_stats_text(week_days, month_days,):
    stats_text = (
        f"*wake up before 5am stats*\n"
        f"• ts week: *{len(week_days)}* days :aga:\n"
        f"• ts month: *{len(month_days)}* days :aga:\n"
        f"*the dates for ts month*:\n"
    )
    if month_days:
        stats_text += "\n".join(f"• {d}" for d in formatted_dates(month_days))
    else:
        stats_text += "• None"
    return stats_text


def post_stats_if_early():
    try:
        now_ist = datetime.now(IST)
        today_start = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=IST)
        messages_today = fetch_messages(today_start - timedelta(seconds=1))
        early_today = get_early_days(messages_today, before_hour=5)
        if not early_today:
            main_text = "<@U07GLQY6UN4> dumbahh couldn't even wake up before 5 :icant:"
            one_more = "<!subteam^S09RZ5VC6UU> bully this dumbahh for not waking up :sob:"
            main = client.chat_postMessage(channel=CHANNEL_ID, text=main_text)
            thread_ts = main["ts"]
            try:
                thread_msg = client.chat_postMessage(channel=CHANNEL_ID, thread_ts=thread_ts, text=one_more)           
            except: 
                raise
            return
        week_start = now_ist - timedelta(days=7)
        month_start = now_ist - timedelta(days=30)

        week_msgs = fetch_messages(week_start)
        month_msgs = fetch_messages(month_start)

        week_days = get_early_days(week_msgs, before_hour=5)
        month_days = get_early_days(month_msgs, before_hour=5)

        main_text = "<@U07GLQY6UN4> bro thinks he tuff by waking up before 5 am :agahappi:"
        thread_text = build_stats_text(week_days, month_days)

        post_message_and_thread(main_text, thread_text)
    except Exception:
        traceback.print_exc()


def ist_scheduler_loop(target_hour=10, target_minute=50):
    last_run_date = None
    while True:
        now_ist = datetime.now(IST)
        if now_ist.hour == target_hour and now_ist.minute == target_minute:
            today = now_ist.date()
            if last_run_date != today:
                post_stats_if_early()
                last_run_date = today
            time.sleep(70)
        else:
            time.sleep(25)


if __name__ == "__main__":
    if TEST_MODE:
        post_stats_if_early()
    else:
        ist_scheduler_loop(target_hour=9, target_minute=11)
