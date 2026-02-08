import yt_dlp
import instaloader
import os

class MediaLoader:
    def download_video(self, url, output_path='downloads'):
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{output_path}/%(title).50s [%(id)s].%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': False,
            'no_warnings': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Error: {e}")

    def download_instagram_photos(self, url, output_path='downloads'):
        loader = instaloader.Instaloader(
            download_videos=False,  # Нам нужны только фото
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,  # Не создаем лишние .json и .txt файлы
            post_metadata_txt_pattern=''
        )

        """Скачивает все фото из поста (включая карусели)"""
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        try:
            # Извлекаем shortcode из ссылки (например, 'DC_xP4uO8zW')
            shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]

            # Загружаем пост по коду
            post = instaloader.Post.from_shortcode(loader.context, shortcode)

            print(f"Начинаю загрузку фото из поста: {shortcode}")

            # Переходим в папку загрузки, чтобы instaloader не мусорил в корне
            original_dir = os.getcwd()
            os.chdir(output_path)

            # Скачиваем пост (target — это имя подпапки внутри downloads)
            loader.download_post(post, target=f"insta")

            # Возвращаемся в исходную директорию
            os.chdir(original_dir)
            print(f"Все фото успешно сохранены в {output_path}")

        except Exception as e:
            print(f"Ошибка при скачивании фото из Instagram: {e}")