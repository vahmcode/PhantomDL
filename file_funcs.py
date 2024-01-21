import os, subprocess, shutil, math
import numpy as np
import qrcode

from PIL import Image, ImageDraw, ImageFont
from pyzbar.pyzbar import decode


def rename_files(dirpath, prefix, rename=True):
    files = sorted(
        [entry for entry in os.scandir(dirpath) if entry.is_file()],
        key=lambda f: f.name,
    )
    digit_len = math.ceil(math.log10(len(files) + 1))

    for n, file in enumerate(files, start=1):
        _, ext = os.path.splitext(file.name)
        new_filename = f"{prefix}{n:0{digit_len}}{ext}"
        if rename:
            file.rename(os.path.join(dirpath, new_filename))

        print(f"{file.name} {'*' * 10} {new_filename}")


def ffmpeg_commands(command, ipath, opath, *args):
    """
    - For "cut_mp3", the first argument is the start time in hh:mm:ss format, and the second argument is the duration in hh:mm:ss format.
    - For "convert_video", the first argument is the desired video codec or format (e.g. "libx264", "mp4", etc.).
    - For "convert_audio", the first argument is the desired audio codec or format (e.g. "aac", "mp3", etc.).
    - For "remux", the first argument is the desired container format (e.g. "mkv", "mov", etc.).
    """
    commands = {
        "cut_mp3": ["-ss", *args, "-c", "copy"],
        "convert_video": ["-c:v", *args, "-c:a", "copy"],
        "convert_audio": ["-vn", "-c:a", *args],
        "extract_audio": ["-vn", "-c:a", "copy"],
        "extract_video": ["-an", "-c:v", "copy"],
        "remux": ["-c", "copy", "-f", *args],
    }
    try:
        subprocess.run(["ffmpeg", "-i", ipath, *commands[command], opath], check=True)
        print("command executed.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")


def images_to_pdf(dirpath, pdfname, extensions=(".jpg", ".png", ".jpeg")):
    image_list = [
        Image.open(os.path.join(dirpath, file)).convert("RGB")
        for file in sorted(os.listdir(dirpath))
        if file.endswith(extensions)
    ]
    image_list[0].save(
        os.path.join(dirpath, pdfname), save_all=True, append_images=image_list[1:]
    )


def random_crop_image(filename, cropname):
    image = np.array(Image.open(filename))
    crop_height, crop_width = image.shape[0] // 4, image.shape[1] // 4
    x, y = np.random.randint(image.shape[1] - crop_width), np.random.randint(
        image.shape[0] - crop_height
    )
    Image.fromarray(image[y : y + crop_height, x : x + crop_width]).convert("RGB").save(
        cropname
    )


def files_of_nested_dir(src_dir, dest_dir=None, categ="videos"):
    extensions = {
        "videos": [".mp4", ".mkv", ".wmv", ".mov", ".avi", ".flv"],
        "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
        "audios": [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"],
        "texts": [".txt", ".pdf", ".doc", ".docx", ".odt", ".rtf"],
    }
    for src_path in (
        os.path.join(dirpath, filename)
        for dirpath, _, filenames in os.walk(src_dir)
        for filename in filenames
        if any(filename.endswith(ext) for ext in extensions[categ])
    ):
        print(src_path)
        if dest_dir != None:
            shutil.copy2(src_path, os.path.join(dest_dir, os.path.basename(src_path)))


def read_qr(qr_file):
    return decode(Image.open(qr_file))[0].data.decode()


def create_qr(text, save_path):
    qrcode.make(text).save(save_path + text + ".jpg")


def txtfile_to_imagefile(
    txtpath,
    imagepath="output.png",
    fontpath=os.path.join(
        os.path.sep, "usr", "share", "fonts", "TTF", "DejaVuSans.ttf"
    ),
):
    with open(txtpath, "r") as f:
        lines = f.readlines()

    font = ImageFont.truetype(fontpath, 14)
    margin = 10
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1), "white"))
    width = max([draw.textsize(line, font)[0] for line in lines]) + 2 * margin
    height = len(lines) * draw.textsize(" ", font)[1] + 2 * margin

    with Image.new("RGB", (width, height), "white") as image:
        draw = ImageDraw.Draw(image)
        draw.multiline_text((margin, margin), "\n".join(lines), "black", font)
        image.save(imagepath)
