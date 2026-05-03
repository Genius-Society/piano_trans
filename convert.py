import os
import sys
import fitz
import shutil
import subprocess
from PIL import Image
from music21 import converter

EN_US = os.getenv("LANG") != "zh_CN.UTF-8"
TMP_DIR = "./__pycache__"

if EN_US:
    import huggingface_hub

    MODEL_DIR = huggingface_hub.snapshot_download(
        "Genius-Society/piano_trans",
        cache_dir=TMP_DIR,
    )

else:
    import modelscope

    MODEL_DIR = modelscope.snapshot_download(
        "Genius-Society/piano_trans",
        cache_dir=TMP_DIR,
    )


if sys.platform.startswith("linux"):
    apkname = "MuseScore.AppImage"
    shutil.move(os.path.realpath(f"{MODEL_DIR}/{apkname}"), f"./{apkname}")
    extra_dir = "squashfs-root"
    if not os.path.exists(extra_dir):
        subprocess.run(["chmod", "+x", f"./{apkname}"])
        subprocess.run([f"./{apkname}", "--appimage-extract"])

    MSCORE = f"./{extra_dir}/AppRun"
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

else:
    MSCORE = os.getenv("mscore")


def add_title_to_xml(xml_path: str, title: str, artist=None):
    midi_data = converter.parse(xml_path)
    # 将标题添加到 MIDI 文件中
    midi_data.metadata.movementName = title
    midi_data.metadata.composer = artist if artist else "Transcripted by AI"
    # 保存修改后的 MIDI 文件
    midi_data.write("musicxml", fp=xml_path)


def xml2abc(xml_path: str):
    result = subprocess.run(
        ["python", "xml2abc.py", xml_path], stdout=subprocess.PIPE, text=True
    )
    if result.returncode == 0:
        return result.stdout

    return ""


def xml2mxl(xml_path: str):
    mxl_file = xml_path.replace(".musicxml", ".mxl")
    command = [MSCORE, "-o", mxl_file, xml_path]
    result = subprocess.run(command)
    print(result)
    return mxl_file


def midi2xml(mid_file: str, title: str, artist=None):
    xml_file = mid_file.replace(".mid", ".musicxml")
    command = [MSCORE, "-o", xml_file, mid_file]
    result = subprocess.run(command)
    add_title_to_xml(xml_file, title, artist)
    print(result)
    return xml_file


def xml2midi(xml_file: str):
    midi_file = xml_file.replace(".musicxml", ".mid")
    command = [MSCORE, "-o", midi_file, xml_file]
    result = subprocess.run(command)
    print(result)
    return midi_file


def pdf2img(pdf_path: str):
    output_path = pdf_path.replace(".pdf", ".jpg")
    doc = fitz.open(pdf_path)
    # 创建一个图像列表
    images = []
    for page_number in range(doc.page_count):
        page = doc[page_number]
        # 将页面渲染为图像
        image = page.get_pixmap()
        # 将图像添加到列表
        images.append(
            Image.frombytes("RGB", [image.width, image.height], image.samples)
        )
    # 竖向合并图像
    merged_image = Image.new(
        "RGB", (images[0].width, sum(image.height for image in images))
    )
    y_offset = 0
    for image in images:
        merged_image.paste(image, (0, y_offset))
        y_offset += image.height
    # 保存合并后的图像为JPG
    merged_image.save(output_path, "JPEG")
    # 关闭PDF文档
    doc.close()
    return output_path


def xml2jpg(xml_file: str):
    pdf_score = xml_file.replace(".musicxml", ".pdf")
    command = [MSCORE, "-o", pdf_score, xml_file]
    result = subprocess.run(command)
    print(result)
    return pdf_score, pdf2img(pdf_score)
