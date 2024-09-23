from flask import Flask, request, jsonify, send_from_directory
import os
from moviepy.editor import VideoFileClip
import subprocess
import whisper

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/'
PROCESSED_FOLDER = 'processed/'

# ساخت پوشه‌ها
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

# بارگذاری مدل Whisper
model = whisper.load_model("base")

# مسیر برای صفحه اصلی
@app.route('/')
def index():
    return send_from_directory('', 'index.html')

# آپلود ویدیو
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'message': 'No video file uploaded'}), 400

    video = request.files['video']
    video_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(video_path)

    print(f"Video saved at: {video_path}")

    # پردازش ویدیو و تولید زیرنویس
    try:
        output_video = process_video_and_subtitle(video_path)
        return jsonify({'message': 'Subtitle generated successfully', 'video_url': output_video}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# پردازش ویدیو و ایجاد زیرنویس با Whisper
def process_video_and_subtitle(video_path):
    # مسیر ذخیره فایل زیرنویس
    srt_file = os.path.splitext(video_path)[0] + '.srt'

    # تولید زیرنویس با Whisper
    generate_subtitle_with_whisper(video_path, srt_file)

    # اضافه کردن زیرنویس به ویدیو با ffmpeg
    output_video_path = os.path.join(PROCESSED_FOLDER, os.path.basename(video_path))

    # دریافت مسیر مطلق فایل SRT
    srt_file_abs = os.path.abspath(srt_file)
    print(f"Using SRT file at: {srt_file}")

    # اطمینان از درست بودن مسیر و استفاده از ffmpeg
    command = [
        'ffmpeg', '-y', '-i', video_path, '-vf', f"subtitles='{srt_file}'",
        '-c:a', 'copy', output_video_path
    ]

    result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    if result.returncode != 0:
        print("FFmpeg stdout:", result.stdout.decode())
        print("FFmpeg stderr:", result.stderr.decode())
        raise Exception("ffmpeg failed")

    return output_video_path

# تابع تولید زیرنویس با Whisper
def generate_subtitle_with_whisper(video_path, subtitle_path):
    # استفاده از whisper برای تولید زیرنویس
    result = model.transcribe(video_path)

    # تولید فایل زیرنویس SRT
    with open(subtitle_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(result['segments']):
            start = segment['start']
            end = segment['end']
            text = segment['text']
            f.write(f"{i + 1}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text.strip()}\n\n")

# تابع فرمت‌دهی زمان به فرمت SRT
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

# سرور ویدیو
@app.route('/processed/<filename>')
def serve_processed_video(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
