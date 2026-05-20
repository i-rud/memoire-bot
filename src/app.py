import telebot
import os
import time
from datetime import datetime
from moviepy import VideoFileClip
from telebot import apihelper, types
from telebot.apihelper import ApiTelegramException

apihelper.CONNECT_TIMEOUT = 120
apihelper.READ_TIMEOUT = 120

from scores import Scores
from old_scores import Scores as OldScores
from standings import Standings
from performance_2 import Performance
from performance import Performance as PerformanceElite
from media import MediaLoader
from schedule import Schedule
from play_in import PlayInSchedule
from play_in_scores import PlayInScores
from all_performances import PerformanceSummary
from weekly_performances import WeeklyPerformances
from round_performances import RoundPerformances
from playoff_bracket import PlayoffBracket

DT_FORMAT = "%Y%m%d"
TOKEN = os.environ.get("TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))

bot = telebot.TeleBot(TOKEN)

scores = PlayInScores()
old_scores = OldScores()
standings = Standings()
performance = Performance()
performance_elite = PerformanceElite()
media_loader = MediaLoader()
schedule = PlayInSchedule()
performance_all = PerformanceSummary()
potw = WeeklyPerformances()
potr = RoundPerformances()
bracket = PlayoffBracket()

import os


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
                
                sent = False
                while not sent:
                    try:
                        bot.send_video(
                            chat_id,
                            video,
                            caption=f"🎥 {filename}",
                            width=w,
                            height=h,
                            duration=duration,
                            timeout=300,
                            supports_streaming=True
                        )
                        sent = True
                        print(f"Успешно отправлено!")
                    except ApiTelegramException as e:
                        if e.error_code == 429:
                            retry_after = e.result_json.get('parameters', {}).get('retry_after', 10)
                            print(f"⚠️ Limit 429. Retry after {retry_after}s...")
                            time.sleep(retry_after + 1)
                            video.seek(0)
                        else:
                            raise e
            time.sleep(2)

        except Exception as e:
            print(f"Ошибка при анализе или отправке {filename}: {e}")

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Не удалось удалить {file_path}: {e}")


def send_and_clear_photos(chat_id, folder_path, custom_caption=None):
    # 1. Собираем все пути к файлам
    if not os.path.exists(folder_path):
        return

    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
             if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not files:
        return

    # 2. Сортируем файлы (чтобы они шли в логичном порядке, например по имени)
    files.sort()

    # 3. Разбиваем список файлов на чанки по 10 штук (лимит Телеграма)
    chunks = [files[i:i + 10] for i in range(0, len(files), 10)]

    for chunk in chunks:
        media = []
        for i, file_path in enumerate(chunk):
            # Подпись добавляем только к первой картинке в каждом посте
            caption = (custom_caption if custom_caption else "🏀 NBA Update") if i == 0 else None

            with open(file_path, 'rb') as f:
                # Читаем байты, чтобы файл можно было удалить сразу после отправки
                media.append(types.InputMediaPhoto(f.read(), caption=caption))

        # 4. Отправляем текущую группу (альбом) с ретраями при 429
        sent = False
        while not sent:
            try:
                bot.send_media_group(chat_id, media)
                sent = True
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = e.result_json.get('parameters', {}).get('retry_after', 10)
                    print(f"⚠️ Limit 429. Retry after {retry_after}s...")
                    time.sleep(retry_after + 1)
                else:
                    print(f"Ошибка при отправке группы: {e}")
                    break
            except Exception as e:
                print(f"Неизвестная ошибка: {e}")
                break

    # 5. Удаляем ВСЕ обработанные файлы из папки
    for file_path in files:
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Не удалось удалить {file_path}: {e}")


# Глобальный словарь для группировки медиа (фото)
media_groups = {}

def handle_premium_merge(chat_id, card_file_id, photo_file_id):
    """Общий обработчик для создания премиум-карточки"""
    bot.send_message(chat_id, "⏳ Создаю премиум-карточку...")
    
    try:
        paths = []
        for file_id in [card_file_id, photo_file_id]:
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            path = f"temp_{file_id}.png"
            with open(path, 'wb') as f:
                f.write(downloaded_file)
            paths.append(path)

        # Сопоставляем пути: 1-ая - статка, 2-ая - фото игрока
        card_path = paths[0]
        photo_path = paths[1]

        # Генерируем мердж
        result_path = performance_all.generate_premium_merge(card_path, photo_path)
        
        with open(result_path, 'rb') as f:
            bot.send_photo(chat_id, f, caption="✨ Твоя премиум-карточка готова!")
            
        # Чистим временные файлы
        for p in paths + [result_path]:
            if os.path.exists(p): os.remove(p)
            
    except Exception as e:
        bot.send_message(chat_id, f"🚫 Ошибка при создании преимум-карточки: {e}")

def process_media_group(chat_id, group_id):
    """Отрабатывает, когда все фото в группе получены"""
    data = media_groups.get(group_id)
    if not data or len(data['files']) != 2:
        return

    group = data['files']
    # 1-ая - статка, 2-ая - фото игрока
    handle_premium_merge(chat_id, group[0], group[1])
    
    if group_id in media_groups:
        del media_groups[group_id]

@bot.message_handler(content_types=['photo'])
@bot.channel_post_handler(content_types=['photo'])
def handle_photos(message):
    if message.chat.id != CHANNEL_ID:
        return

    # Проверка на ответ (reply) к другой фотографии с командой /merge
    if message.reply_to_message and message.reply_to_message.photo and message.caption and "/merge" in message.caption:
        card_file_id = message.reply_to_message.photo[-1].file_id
        photo_file_id = message.photo[-1].file_id
        handle_premium_merge(message.chat.id, card_file_id, photo_file_id)
        return

    if message.media_group_id:
        gid = message.media_group_id
        if gid not in media_groups:
            media_groups[gid] = {'files': [], 'should_merge': False}
        
        # Только первое фото в альбоме содержит подпись
        if message.caption and "/merge" in message.caption:
            media_groups[gid]['should_merge'] = True
        
        media_groups[gid]['files'].append(message.photo[-1].file_id)
        
        # Если пришло 2 фото, проверяем, нужно ли объединять
        if len(media_groups[gid]['files']) == 2:
            time.sleep(1) # Небольшая пауза для стабильности
            if media_groups[gid]['should_merge']:
                process_media_group(message.chat.id, gid)
            else:
                # Если команды нет, просто очищаем данные через время (или сразу)
                del media_groups[gid]
    elif message.caption and "/merge" in message.caption:
        bot.reply_to(message, "Чтобы сделать премиум-карточку через альбом, пришли **сразу две** фотографии одним сообщением. Или ответь на фото статистики фотографией игрока с командой /merge.")


@bot.channel_post_handler(content_types=['text'])
def handle_channel_posts(message):
    print(CHANNEL_ID)
    if message.chat.id != CHANNEL_ID:
        return

    text = message.text

    if "/gen" in text:
        process_gen(message.chat.id, text)
    if "/old" in text:
        process_old(message.chat.id, text)
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
    if "/top" in text:
        process_top(message.chat.id, text)
    if "/potw" in text:
        process_potw(message.chat.id, text)
    if "/potr" in text:
        process_potr(message.chat.id, text)
    if "/bracket" in text:
        process_bracket(message.chat.id)

def process_bracket(chat_id):
    bot.send_message(chat_id, "⏳ Generating playoff bracket...")
    try:
        bracket.generate()
        send_and_clear_photos(chat_id, "images/playoff", custom_caption="🏀 NBA Playoff Bracket")
        bot.send_message(chat_id, "✅ Done")
    except Exception as e:
        bot.send_message(chat_id, f"🚫 Error generating playoff bracket: {e}")

def process_potw(chat_id, text: str):
    date = text.split(" ")[1]

    bot.send_message(chat_id, "⏳ Generating potw...")
    potw.fetch_and_aggregate(date)

    send_and_clear_photos(chat_id, "images/weekly/players")
    bot.send_message(chat_id, "✅ Done")

def process_potr(chat_id, text: str):
    # Format: /potr <round> [date]
    parts = text.split(" ")
    n_round = parts[1]
    
    # If date is provided, use it. Otherwise use today.
    if len(parts) > 2:
        date = parts[2]
    else:
        date = datetime.now().strftime("%d.%m")

    bot.send_message(chat_id, f"⏳ Generating Player of the Round {n_round}...")
    potr.fetch_and_aggregate(date, n_round)

    send_and_clear_photos(chat_id, "images/round_performances")
    bot.send_message(chat_id, "✅ Done")

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

def process_old(chat_id, text: str):
    date = text.split(" ")[1]

    try:
        print(datetime.strptime(date, DT_FORMAT))
    except Exception:
        bot.send_message(chat_id, f"🚫Invalid date format ({date}), valid format is {DT_FORMAT}")
        return

    bot.send_message(chat_id, "⏳ Generating old scores...")
    old_scores.generate(date)

    send_and_clear_photos(chat_id, "images/old_scores")

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
    print(data)
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


def process_top(chat_id, text: str):
    try:
        date = text.split(" ")[1]
    except IndexError:
        bot.send_message(chat_id, "🚫 Please provide a date: /top 20260327")
        return

    bot.send_message(chat_id, f"⏳ Generating top performances for {date}...")
    
    mvp = performance_all.fetch_and_generate(date)
    
    base_dir = "images/performances"
    if not os.path.exists(base_dir):
        bot.send_message(chat_id, "✅ No performances generated for this date.")
        return

    # Получаем список всех папок игр
    game_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    game_folders.sort()

    if not game_folders:
        bot.send_message(chat_id, "✅ No player cards met the threshold.")
    else:
        for folder in game_folders:
            folder_path = os.path.join(base_dir, folder)
            # Отправляем карточки из этой папки с именем папки в качестве подписи
            send_and_clear_photos(chat_id, folder_path, custom_caption=f"🏀 {folder.replace('_', ' ')}")
            
            # Удаляем пустую папку
            try:
                os.rmdir(folder_path)
            except Exception as e:
                print(f"Could not remove folder {folder_path}: {e}")

    send_and_clear_photos(chat_id, "images/performances")

    bot.send_message(chat_id, "✅ Batch processing complete!")


@bot.message_handler(content_types=['text'])
def handle_all_private_messages(message):
    print(f"DEBUG: Получено сообщение в ЛС от {message.chat.id}: {message.text}")
    bot.reply_to(message, f"Привет! Я тебя вижу. Твой ID: {message.chat.id}")


if __name__ == "__main__":
    print("Polling is up...")
    bot.infinity_polling(timeout=120)