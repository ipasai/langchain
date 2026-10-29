import os
import shutil
import subprocess
import tempfile
import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="Local Markdown TTS")
MAX_CHARS = 12000
PIPER_MODEL = os.environ.get("PIPER_MODEL_PATH", "")
PIPER_BIN = os.environ.get("PIPER_BIN", "piper")
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    voice: str = ""
    instructions: str = ""
    provider: str = "piper"


@app.get("/health")
def health():
    return {
        "ok": True,
        "model_configured": bool(PIPER_MODEL),
        "piper_available": shutil.which(PIPER_BIN) is not None,
        "ffmpeg_available": shutil.which(FFMPEG_BIN) is not None,
    }


@app.post("/synthesize")
async def synthesize(body: SpeechRequest):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="請提供要朗讀的文字")

    if body.provider == "edge":
        allowed_edge_voices = {
            "zh-TW-HsiaoChenNeural",
            "zh-TW-HsiaoYuNeural",
            "zh-TW-YunJheNeural",
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-XiaoyiNeural",
            "zh-CN-YunxiNeural",
            "zh-CN-YunyangNeural",
        }
        selected_voice = body.voice if body.voice in allowed_edge_voices else "zh-TW-HsiaoChenNeural"
        try:
            import edge_tts
        except ImportError as error:
            raise HTTPException(status_code=503, detail="缺少 edge-tts，請安裝 requirements-local-tts.txt") from error

        with tempfile.TemporaryDirectory(prefix="local-edge-tts-") as temp_dir:
            mp3_path = Path(temp_dir) / "speech.mp3"
            try:
                communicate = edge_tts.Communicate(text, selected_voice)
                await communicate.save(str(mp3_path))
            except Exception as error:
                raise HTTPException(status_code=502, detail=f"Edge TTS 語音合成失敗：{error}") from error
            if not mp3_path.is_file() or mp3_path.stat().st_size == 0:
                raise HTTPException(status_code=502, detail="Edge TTS 沒有回傳 MP3 音訊")
            return Response(
                content=mp3_path.read_bytes(),
                media_type="audio/mpeg",
                headers={"Content-Disposition": 'attachment; filename="speech.mp3"'},
            )

    if not PIPER_MODEL or not Path(PIPER_MODEL).is_file():
        raise HTTPException(status_code=503, detail="請設定有效的 PIPER_MODEL_PATH (.onnx) 語音模型")
    if not shutil.which(PIPER_BIN):
        raise HTTPException(status_code=503, detail="找不到 Piper executable，請安裝 Piper 並設定 PIPER_BIN")
    if not shutil.which(FFMPEG_BIN):
        raise HTTPException(status_code=503, detail="找不到 ffmpeg；本機 MP3 匯出需要 ffmpeg")

    with tempfile.TemporaryDirectory(prefix="local-tts-") as temp_dir:
        wav_path = Path(temp_dir) / "speech.wav"
        mp3_path = Path(temp_dir) / "speech.mp3"
        try:
            subprocess.run(
                [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", str(wav_path)],
                input=text,
                text=True,
                check=True,
                capture_output=True,
                timeout=180,
            )
            subprocess.run(
                [FFMPEG_BIN, "-nostdin", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "3", str(mp3_path)],
                check=True,
                capture_output=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired as error:
            raise HTTPException(status_code=504, detail="本機語音產生逾時") from error
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or b"").decode("utf-8", errors="replace")[-1200:]
            raise HTTPException(status_code=500, detail=f"本機語音產生失敗：{detail}") from error
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"無法啟動本機語音工具：{error}") from error

        return Response(
            content=mp3_path.read_bytes(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'attachment; filename="speech.mp3"'},
        )
