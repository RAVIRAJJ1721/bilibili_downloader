import requests
import os
import re
import json
import subprocess
from tqdm import tqdm

# Display banner
BANNER = r'''
 ██████╗░██╗██╗░░░░░██╗░░░████████╗██╗░░░██╗
 ██╔══██╗██║██║░░░░░██║░░░╚══██╔══╝██║░░░██║
 ██████╦╝██║██║░░░░░██║░░░░░░██║░░░╚██╗░██╔╝
 ██╔══██╗██║██║░░░░░██║░░░░░░██║░░░░╚████╔╝░
 ██████╦╝██║███████╗██║██╗░░░██║░░░░░╚██╔╝░░
 ╚═════╝░╚═╝╚══════╝╚═╝╚═╝░░░╚═╝░░░░░░╚═╝░░░
'''
print(BANNER)

# Load cookies
def load_cookies(path='cookies.txt'):
    if not os.path.exists(path):
        print("Missing cookies.txt file.")
        return ''
    with open(path, 'r') as file:
        cookies = file.read().strip().replace('\n', '; ')
    return cookies

cookies = load_cookies()

headers = {
    'referer': 'https://www.bilibili.tv/',
    'cookie': cookies
}

# Parse link
def extract_id(link):
    if '/video/' in link:
        return link.split('/video/')[-1].split('/')[0]
    elif '/play/' in link:
        numbers = re.findall(r'/play/(\d+)/(\d+)', link)
        if numbers:
            return numbers[0][1]
        numbers = re.findall(r'/play/(\d+)', link)
        if numbers:
            return numbers[0]
    return None

# Get URLs
def get_stream_urls(value, quality=64):
    is_numeric = re.fullmatch(r'\d{4,8}', value)

    if is_numeric:
        api_url = f"https://api.bilibili.tv/intl/gateway/web/playurl?ep_id={value}&device=wap&platform=web&qn=64&tf=0&type=0"
    else:
        api_url = f"https://api.bilibili.tv/intl/gateway/web/playurl?s_locale=en_US&platform=web&aid={value}&qn=120"

    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        print(f"API error: {response.status_code}")
        return None

    data = response.json()
    playurl = data.get("data", {}).get("playurl", {})
    if not playurl:
        print("Missing 'playurl' in response.")
        return None

    video_url = None
    audio_url = None

    for video in playurl.get("video", []):
        q = video.get("stream_info", {}).get("quality", 0)
        url = video.get("video_resource", {}).get("url", "")
        if q in [112, 80, 64, 32] and url:
            video_url = url
            break

    audio_resources = playurl.get("audio_resource", [])
    if audio_resources:
        audio_url = audio_resources[0].get("url")

    if video_url and audio_url:
        return video_url, audio_url
    else:
        return None

# Download file with progress bar
def download_file(url, filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        with open(filename, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True, desc=filename) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

# Merge with ffmpeg
def merge_audio_video(video_path, audio_path, output_path):
    cmd = [
        "ffmpeg", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "copy", output_path, "-y"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Main function
def download_bilibili(link, output_dir="Downloads"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    video_id = extract_id(link)
    if not video_id:
        print("Could not extract ID from link.")
        return

    result = get_stream_urls(video_id)
    if not result:
        print("Could not fetch stream URLs.")
        return

    video_url, audio_url = result
    video_file = os.path.join(output_dir, "temp_video.mp4")
    audio_file = os.path.join(output_dir, "temp_audio.mp4")
    final_file = os.path.join(output_dir, f"bilibili_{video_id}.mp4")

    print("Downloading video...")
    download_file(video_url, video_file)

    print("Downloading audio...")
    download_file(audio_url, audio_file)

    print("Merging video and audio...")
    merge_audio_video(video_file, audio_file, final_file)

    os.remove(video_file)
    os.remove(audio_file)

    print(f"\nDownload complete: {final_file}")

# === USAGE ===
# Example:
# download_bilibili("https://www.bilibili.tv/en/video/4780916840315904")
