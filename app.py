import os
import torch
import shutil
import gradio as gr
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from piano_transcription_inference import PianoTranscription, load_audio, sample_rate
from convert import midi2xml, xml2abc, xml2mxl, xml2jpg

EN_US = os.getenv("LANG") != "zh_CN.UTF-8"
TMP_DIR = "./__pycache__"

if EN_US:
    import huggingface_hub

    MODEL_PATH = huggingface_hub.snapshot_download(
        "Genius-Society/piano_trans",
        cache_dir=TMP_DIR,
    )

else:
    import modelscope

    MODEL_PATH = modelscope.snapshot_download(
        "Genius-Society/piano_trans",
        cache_dir=TMP_DIR,
    )


ZH2EN = {
    "五线谱": "Staff",
    "状态栏": "Status",
    "下载 MXL": "Download MXL",
    "ABC 记谱": "ABC notation",
    "上传音频": "Upload an audio",
    "下载 MIDI": "Download MIDI",
    "下载 PDF 乐谱": "Download PDF score",
    "下载 MusicXML": "Download MusicXML",
    "钢琴转谱工具": "Piano Transcription Tool",
    "请上传音频 100% 后再点提交": "Please make sure the audio is completely uploaded before clicking Submit",
}


def _L(zh_txt: str):
    return ZH2EN[zh_txt] if EN_US else zh_txt


def clean_cache(cache_dir):
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

    os.mkdir(cache_dir)


def extract_meta(audio_path: str):
    if not audio_path:
        raise ValueError("文件路径为空!")

    artist = None
    name, ext = os.path.splitext(os.path.basename(audio_path))
    ext == ext.lower()
    if ext == ".mp3":
        audio = MP3(audio_path)
        title = audio.get("TIT2")
        artist = audio.get("TPE1")
        if title:
            title = title.text[0]
        if artist:
            artist = artist.text[0]

    elif ext == ".flac":
        audio = FLAC(audio_path)
        title = audio.get("TITLE")
        artist = audio.get("ARTIST")
        if title:
            title = title[0]
        if artist:
            artist = artist[0]

    if not title:
        title = name.strip().capitalize()

    return title, artist


def audio2midi(audio_path: str, cache_dir: str):
    title, artist = extract_meta(audio_path)
    audio, _ = load_audio(audio_path, sr=sample_rate, mono=True)
    transcriptor = PianoTranscription(
        device="cuda" if torch.cuda.is_available() else "cpu",
        checkpoint_path=f"{MODEL_PATH}/CRNN_note_F1=0.9677_pedal_F1=0.9186.pth",
    )
    midi_path = f"{cache_dir}/output.mid"
    transcriptor.transcribe(audio, midi_path)
    return midi_path, title, artist


def upl_infer(audio_path: str, cache_dir=f"{TMP_DIR}/cache"):
    status = "Success"
    midi = pdf = xml = mxl = abc = jpg = None
    try:
        clean_cache(cache_dir)
        midi, title, artist = audio2midi(audio_path, cache_dir)
        xml = midi2xml(midi, title, artist)
        abc = xml2abc(xml)
        mxl = xml2mxl(xml)
        pdf, jpg = xml2jpg(xml)

    except Exception as e:
        status = f"{e}"

    return status, midi, pdf, xml, mxl, abc, jpg


def find_audio_files(folder_path=f"{MODEL_PATH}/examples"):
    wav_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".wav") or file.endswith(".mp3"):
                file_path = os.path.join(root, file)
                wav_files.append(file_path)

    return wav_files


if __name__ == "__main__":
    gr.Interface(
        fn=upl_infer,
        inputs=gr.Audio(label=_L("上传音频"), type="filepath"),
        outputs=[
            gr.Textbox(label=_L("状态栏"), buttons=["copy"]),
            gr.File(label=_L("下载 MIDI")),
            gr.File(label=_L("下载 PDF 乐谱")),
            gr.File(label=_L("下载 MusicXML")),
            gr.File(label=_L("下载 MXL")),
            gr.TextArea(label=_L("ABC 记谱"), buttons=["fullscreen", "copy"]),
            gr.Image(
                label=_L("五线谱"),
                type="filepath",
                buttons=["download", "fullscreen"],
            ),
        ],
        title=_L("钢琴转谱工具"),
        description=_L("请上传音频 100% 后再点提交"),
        flagging_mode="never",
        cache_examples=False,
        examples=find_audio_files(),
    ).launch(css="#gradio-share-link-button-0 { display: none; }")
