import os, time, requests
import yt_dlp
import zipfile

from datetime import datetime
from tqdm import tqdm
from pytube import Playlist, YouTube
from youtube_transcript_api import YouTubeTranscriptApi

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located as presence,
    element_to_be_clickable as clickable,
)

from bs4 import BeautifulSoup
from guessit import guessit


def is_internet_connected():
    try:
        response = requests.get("https://www.google.com", timeout=5)
        return response.status_code == 200

    except requests.exceptions.RequestException:
        return False


def download_req_tqdm(url, filepath):
    response = requests.get(url, stream=True, allow_redirects=True)
    total_size = int(response.headers.get("content-length", 0))
    with open(filepath, "wb") as f, tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        desc=filepath,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))


def download_req_tqdm_resumable(url, filepath):
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
    else:
        file_size = 0

    response = requests.head(url)
    total_size = int(response.headers.get("content-length", 0))

    headers = {"Range": f"bytes={file_size}-"}

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f, tqdm(
            total=total_size,
            initial=file_size,
            unit="B",
            unit_scale=True,
            desc=filepath,
        ) as pbar:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))


def download_scheduled(links, names, dl_time_str, dirpath=""):
    """dl_time_str : 00:00 - 23:59"""
    dl_time = datetime.strptime(dl_time_str, "%H:%M").time()

    if all(isinstance(x, str) and ".txt" in x for x in (links, names)):
        links, names = (open(x).read().splitlines() for x in (links, names))

    print("-" * 100)
    print(f"Your files will be downloaded at {dl_time.hour:02}:{dl_time.minute:02}")

    while datetime.now().time() < dl_time:
        time.sleep(1)

    for i, (link, name) in enumerate(zip(links, names), 1):
        while True:
            try:
                download_req_tqdm_resumable(link, os.path.join(dirpath, name))
                print(f"{i}: {name}")
                break
            except Exception as err:
                print(err, name)

    print("-" * 100)


def auto_sub_dl(dirpath, url="https://subf2m.co"):
    movies = [
        movie
        for movie in os.listdir(dirpath)
        if "title" in guessit(movie) and "year" in guessit(movie)
    ]

    os.makedirs(dirpath + "/srt", exist_ok=True)
    for movie in movies:
        g = guessit(movie)
        name = g["title"]
        year = str(g["year"])
        print(f"{name} {year}")

        response = requests.get(f"{url}/subtitles/searchbytitle?query={name}+&l=")
        s = BeautifulSoup(response.content, "html.parser")
        links = (l for l in s.find_all("div", {"class": "title"}) if year in l.text)

        link = next(links, None)
        if link:
            link = link.find("a")["href"]

            response = requests.get(f"{url}{link}")
            s = BeautifulSoup(response.content, "html.parser")
            link = s.find("a", {"class": "download"})["href"]

            response = requests.get(f"{url}{link}")
            s = BeautifulSoup(response.content, "html.parser")
            link = s.find("div", {"class": "download"}).find("a")["href"]

            response = requests.get(f"{url}{link}", stream=True)
            with open(f"{dirpath}/srt/subtitle.zip", "wb") as handle:
                for data in tqdm(response.iter_content()):
                    handle.write(data)

            with zipfile.ZipFile(f"{dirpath}/srt/subtitle.zip", "r") as zipf:
                files = list(zipf.namelist())

                for f in files:
                    if f.endswith(".srt"):
                        zipf.extract(f, f"{dirpath}/srt")
                        subname = movie[:-3] + "srt"
                        os.rename(
                            f"{dirpath}/srt/{f}",
                            f"{dirpath}/srt/{subname}",
                        )
                        break


def aparat_playlist(playlist_url, dirpath, quality="480"):
    """quality (360-480-720-1080)"""
    driver = webdriver.Firefox()
    webwait = WebDriverWait(driver, 60)

    driver.get(playlist_url)
    time.sleep(8)

    playlist_id = playlist_url.split("/")[-1]
    pages_xpath = f'//*[@id="thumb{playlist_id}"]/div/div[2]/a'
    webwait.until(presence((By.XPATH, pages_xpath)))

    video_urls = []
    for element in driver.find_elements(By.XPATH, pages_xpath):
        video_urls.append(element.get_attribute("href"))

    links = []
    names = []
    for video_url in video_urls:
        while True:
            try:
                driver.get(video_url)
                time.sleep(4)

                name_xpath = '//*[@id="primary"]/div[2]/div[1]/h1/span'
                webwait.until(presence((By.XPATH, name_xpath)))
                name = driver.find_element(By.XPATH, name_xpath).text
                unaccept = '\\/:?"<>|'
                for u in unaccept:
                    if u in name:
                        name = name.replace(u, "")
                names.append(name)

                dl_btn = (
                    '//*[@id="primary"]/div[2]/div[2]/div[2]/div/div[1]/div[3]/div/div'
                )
                webwait.until(clickable((By.XPATH, dl_btn)))
                driver.find_element(By.XPATH, dl_btn).click()
                time.sleep(2)

                link = driver.find_element(By.XPATH, f'//*[@id="{quality}p"]')
                links.append(link.get_attribute("href"))

                break

            except:
                pass

    driver.close()

    for link, name in zip(links, name):
        download_req_tqdm_resumable(link, f"{dirpath}/{name}.mp4")


def youtube_subtitle(video_url, filepath):
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_url.split("v=")[1])
    with open(filepath.replace(".mp4", ".srt"), "w") as f:
        for counter, (o, tr) in enumerate(
            zip(transcript_list[0].fetch(), transcript_list[0].translate("fa").fetch()),
            start=1,
        ):
            start = format_time(o["start"])
            end = format_time(o["start"] + o["duration"])
            f.write(f"{counter}\n{start} --> {end}\n{o['text']}\n{tr['text']}\n\n")


def youtube_video_pytube(video_url, dirpath, index="", subtitle=False):
    while True:
        try:
            video = YouTube(video_url)
            streams = video.streams.filter(progressive=True, file_extension="mp4")
            streams = streams.order_by("resolution").desc()

            for stream in streams:
                if stream.filesize < (video.length * 6 * 1024 * 1024):
                    filename = f"{index:02}_{video.title}.mp4"
                    filepath = f"{dirpath}/{filename}"
                    return [filepath, stream.url]
                break

        except Exception as err:
            print(video.title, video.watch_url, err)


def youtube_playlist_pytube(
    playlist_url, dirpath, txtlinks="./adm.txt", txtnames="./names.txt"
):
    playlist = Playlist(playlist_url)
    names, links = [], []
    for index, video_url in enumerate(playlist.url_generator(), start=1):
        yt = youtube_video_pytube(video_url, dirpath, index)
        names.append(yt[0])
        links.append(yt[1])
        print(yt[0], yt[1])

    with open(txtlinks, "w") as l, open(txtnames, "w") as n:
        l.write("\n".join(links))
        n.write("\n".join(names))


def youtube_playlist_ytdlp(playlist_url, dirpath, txtpath="./adm.txt"):
    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "outtmpl": f"{dirpath}/%(playlist_index)s_%(title)s.%(ext)s",
        "noplaylist": False,
        "quiet": True,
        "simulate": True,
        "forceurl": True,
    }
    links = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url)
        for video in info["entries"]:
            while True:
                try:
                    filename = f"{video['index']:02}_{video['title']}.mp4"
                    filepath = f"{dirpath}/{filename}"
                    print(video["index"], video["title"])
                    download_req_tqdm(video["url"], filepath)
                    links.append(video["url"])
                    break

                except Exception as err:
                    print(err, video)

    with open(txtpath, "w") as f:
        f.write("\n".join(links))
