import telebot
import os
import time
from datetime import datetime
from moviepy import VideoFileClip
from telebot import apihelper

apihelper.CONNECT_TIMEOUT = 120
apihelper.READ_TIMEOUT = 120

from scores import Scores
from standings import Standings
from performance_2 import Performance
from performance import PerformanceElite
from media import MediaLoader
from schedule import Schedule

DT_FORMAT = "%Y%m%d"
TOKEN = os.environ.get("TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))

bot = telebot.TeleBot(TOKEN)

scores = Scores()
standings = Standings()
performance = Performance()
performance_elite = PerformanceElite()
media_loader = MediaLoader()
schedule = Schedule()

import os
from telebot import types


def send_videos_from_dir(chat_id, folder_path='downloads'):
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv')
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(video_extensions)]

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        try:
            # Узнаем размеры видео
            clip = VideoFileClip(file_path)
            w, h = clip.size
            duration = clip.duration
            clip.close()  # Важно закрыть файл, чтобы не было ошибок доступа

            with open(file_path, 'rb') as video:
                print(f"Отправка вертикального видео ({w}x{h}): {filename}...")

                bot.send_video(
                    chat_id,
                    video,
                    caption=f"🎥 {filename}",
                    width=w,  # Передаем ширину
                    height=h,  # Передаем высоту
                    duration=duration,  # И длительность для корректного плеера
                    timeout=300,
                    supports_streaming=True  # Позволяет смотреть видео до полной загрузки
                )

            print(f"Успешно отправлено!")
            time.sleep(2)

        except Exception as e:
            print(f"Ошибка при анализе или отправке {filename}: {e}")

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Не удалось удалить {file_path}: {e}")


def send_and_clear_photos(chat_id, folder_path):
    # 1. Собираем все пути к файлам
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
             if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not files:
        return

    # 2. Сортируем файлы (чтобы они шли в логичном порядке, например по имени)
    files.sort()

    # 3. Разбиваем список файлов на чанки по 10 штук
    # Используем list comprehension для создания списка списков
    chunks = [files[i:i + 4] for i in range(0, len(files), 4)]

    for chunk in chunks:
        media = []
        for i, file_path in enumerate(chunk):
            # Подпись добавляем только к первой картинке в каждом посте
            caption = "🏀 NBA Update" if i == 0 else None

            with open(file_path, 'rb') as f:
                # Читаем байты, чтобы файл можно было удалить сразу после отправки
                media.append(types.InputMediaPhoto(f.read(), caption=caption))

        # 4. Отправляем текущую группу (альбом)
        try:
            bot.send_media_group(chat_id, media)
        except Exception as e:
            print(f"Ошибка при отправке группы: {e}")

    # 5. Удаляем ВСЕ обработанные файлы из папки
    for file_path in files:
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Не удалось удалить {file_path}: {e}")


@bot.channel_post_handler(content_types=['text'])
def handle_channel_posts(message):
    print(CHANNEL_ID)
    if message.chat.id != CHANNEL_ID:
        return

    text = message.text

    if "/gen" in text:
        process_gen(message.chat.id, text)
    if "/perf" in text:
        process_perf(message.chat.id, text)
    if "/video" in text:
        process_video(message.chat.id, text)
    if "/schedule" in text:
        process_schedule(message.chat.id, text)
    if "/insta" in text:
        process_insta(message.chat.id, text)
    if "/standings" in text:
        process_standings(message.chat.id)
    if "/elite" in text:
        process_perf_elite(message.chat.id, text)

def process_insta(chat_id, text: str):
    date = text.split(" ")[1]

    bot.send_message(chat_id, "⏳ Downloading insta photos...")
    media_loader.download_instagram_photos(date)

    send_and_clear_photos(chat_id, "downloads/insta")
    bot.send_message(chat_id, "✅ Done")


def process_schedule(chat_id, text: str):
    date = text.split(" ")[1]

    bot.send_message(chat_id, "⏳ Generating schedule...")
    schedule.generate(date)

    send_and_clear_photos(chat_id, "images/schedule")
    bot.send_message(chat_id, "✅ Done")


def process_video(chat_id, text: str):
    url = text.split(" ")[1]

    try:
        bot.send_message(chat_id, "⏳ Loading video...")
        media_loader.download_video(url, "downloads")

        send_videos_from_dir(chat_id, "downloads")
    except Exception as e:
        print(f"🚫Something went wrong ({e})")


def process_standings(chat_id):
    bot.send_message(chat_id, "⏳ Generating standings...")
    standings.generate()

    send_and_clear_photos(chat_id, "images/standings")

    bot.send_message(chat_id, "✅ Done")

def process_gen(chat_id, text: str):
    date = text.split(" ")[1]

    try:
        print(datetime.strptime(date, DT_FORMAT))
    except Exception:
        bot.send_message(chat_id, f"🚫Invalid date format ({date}), valid format is {DT_FORMAT}")
        return

    bot.send_message(chat_id, "⏳ Generating scores...")
    headlines = scores.generate(date)
    bot.send_message(chat_id, f"Day MVP:\n{headlines}")

    send_and_clear_photos(chat_id, "images/scores")

    bot.send_message(chat_id, "⏳ Generating standings...")
    standings.generate()

    send_and_clear_photos(chat_id, "images/standings")

    bot.send_message(chat_id, "✅ Done")

def process_perf_elite(chat_id, text: str):
    data = text.split(" ")[1].split("|")

    bot.send_message(chat_id, "⏳ Generating performance...")
    performance_elite.generate(
        name=data[0].replace("+", " "),
        date=data[1].replace("+", " "),
        home=data[2],
        away=data[3],
        url=data[4],
        stats=data[5].replace("+", " "),
        layout=data[6]
    )

    send_and_clear_photos(chat_id, "images/performances")
    bot.send_message(chat_id, "✅ Done")

def process_perf(chat_id, text: str):
    data = text.split(" ")[1].split("|")

    bot.send_message(chat_id, "⏳ Generating performance...")
    performance.generate(
        name=data[0].replace("+", " "),
        date=data[1].replace("+", " "),
        home=data[2],
        away=data[3],
        url=data[4],
        stats=data[5].replace("+", " "),
        layout=data[6]
    )

    send_and_clear_photos(chat_id, "images/performances")
    bot.send_message(chat_id, "✅ Done")


if __name__ == "__main__":
    print("Polling is up...")
    bot.infinity_polling(timeout=120)