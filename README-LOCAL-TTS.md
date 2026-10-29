# 本機 Markdown 轉 MP3（Piper）

本機模式不需要 OpenAI API key。Ollama 本身是文字 LLM，不能把文字直接合成音訊；可以先用 Ollama 整理/改寫文字，再由本機 Piper 語音模型合成，最後透過 ffmpeg 轉成 MP3。

網站的 Edge TTS 可選繁體中文（台灣）或簡體中文（中國），不需要 OpenAI API key，但合成時需要網路。台灣語音包含曉臻、曉雨、雲哲；中國語音包含曉曉、曉伊、雲希、雲揚。真正離線的「本機 Piper」仍使用你安裝的 Piper 模型；範例 `zh_CN-huayan-medium` 是中國大陸普通話，不是台灣口音。

## macOS 安裝步驟

以下步驟以專案根目錄 `/Users/autoclaw/Documents/langchain` 和已建立的 `.venv` 為例。先前若已安裝 `requirements-local-tts.txt`，可跳過第 1 步。

### 1. 安裝 Python TTS 服務套件

```bash
cd /Users/autoclaw/Documents/langchain
source .venv/bin/activate
pip install -r requirements-local-tts.txt
pip install piper-tts
```

`requirements-local-tts.txt` 安裝 FastAPI、Uvicorn 與 Edge TTS；`piper-tts` 提供完全離線語音合成程式及模型下載工具。

### 2. 安裝 ffmpeg

確認 Homebrew 已安裝，再安裝 ffmpeg：

```bash
brew install ffmpeg
ffmpeg -version
```

若 `brew` 指令不存在，請先從 Homebrew 官方網站安裝 Homebrew，再重新開啟終端機執行上述命令。

### 3. 下載 Piper 中文語音模型（僅 Piper 離線模式需要）

建立模型目錄，並在該目錄下載 Piper 中文語音模型：

```bash
mkdir -p "$HOME/voices/piper"
cd "$HOME/voices/piper"
/Users/autoclaw/Documents/langchain/.venv/bin/python -m piper.download_voices zh_CN-huayan-medium
```

確認目錄內包含模型 `.onnx` 與設定 `.onnx.json`：

```bash
ls -lh "$HOME/voices/piper"
```

同時確認 Piper CLI 可以啟動：

```bash
/Users/autoclaw/Documents/langchain/.venv/bin/piper --help
```

### 4. 測試產生 WAV 與 MP3

先讓 Piper 產生 WAV，再使用 ffmpeg 轉成 MP3：

```bash
printf '你好，這是本機 Piper 語音測試。' | \
	/Users/autoclaw/Documents/langchain/.venv/bin/piper \
	--model "$HOME/voices/piper/zh_CN-huayan-medium.onnx" \
	--output_file "$HOME/voices/piper/test.wav"

ffmpeg -y -i "$HOME/voices/piper/test.wav" "$HOME/voices/piper/test.mp3"
ls -lh "$HOME/voices/piper/test.mp3"
```

若模型名稱或下載位置不同，請把命令中的 `.onnx` 路徑換成實際檔案路徑。

### 5. 設定並啟動本機 TTS API

在 repo 根目錄啟動服務。這個終端機需保持開啟：

```bash
cd /Users/autoclaw/Documents/langchain
source .venv/bin/activate

export PIPER_MODEL_PATH="$HOME/voices/piper/zh_CN-huayan-medium.onnx"
export PIPER_BIN="/Users/autoclaw/Documents/langchain/.venv/bin/piper"
export FFMPEG_BIN="$(command -v ffmpeg)"

uvicorn local_tts_server:app --host 127.0.0.1 --port 8002
```

另開一個終端機檢查服務狀態：

```bash
curl http://127.0.0.1:8002/health
```

預期回傳內容會包含 `"ok": true`、`"model_configured": true`、`"piper_available": true` 與 `"ffmpeg_available": true`。

### 6. 從網站下載 MP3

確認 Next.js 網站也正在執行，然後：

1. 在網站上方主頁籤選擇「🎧 Markdown 轉 MP3」。
2. 選擇「本機 Piper（離線）」。
3. 貼上 Markdown 內容或上傳 `.md` 檔。
4. 按「產生並下載 MP3」。

本機語音模式不需要 `OPENAI_API_KEY`。網站透過 `LOCAL_TTS_URL` 連線；預設值為 `http://127.0.0.1:8002/synthesize`。若 API 服務位址不同，在 `web/.env.local` 設定：

```env
LOCAL_TTS_URL=http://127.0.0.1:8002/synthesize
```

修改 `.env.local` 後需要重新啟動 Next.js 開發伺服器。

## 必要項目

- Piper executable 可從命令列執行
- 一個 Piper ONNX voice model（中文可選支援中文的 zh_CN voice），以及對應 `.onnx.json` 設定檔
- ffmpeg
- Python FastAPI 依賴

## 其他環境的啟動服務

在 repo 根目錄安裝 Python 服務依賴：

```bash
pip install -r requirements-local-tts.txt
```

設定 Piper voice model 路徑（請改成自己下載的模型位置）：

```bash
export PIPER_MODEL_PATH="$HOME/voices/zh_CN-huayan-medium.onnx"
export PIPER_BIN="piper"
export FFMPEG_BIN="ffmpeg"
uvicorn local_tts_server:app --host 127.0.0.1 --port 8002
```

Next.js 端預設連線到 `http://127.0.0.1:8002/synthesize`。若本機 TTS server 在別處，可在 `web/.env.local` 設定：

```env
LOCAL_TTS_URL=http://127.0.0.1:8002/synthesize
```

兩個服務都啟動後，在網站上方頁籤選「🎧 Markdown 轉 MP3」。

- 繁體中文（台灣）：選 Edge TTS，再選曉臻、曉雨或雲哲。不需 OpenAI key，但合成時需要網路。
- 簡體中文（中國）：選 Edge TTS，再選曉曉、曉伊、雲希或雲揚。不需 OpenAI key，但合成時需要網路。
- 完全離線：選「本機 Piper（離線）」。需完成前述 Piper 模型設定；目前範例的 Huayan 是中國大陸普通話口音。
- OpenAI：選「OpenAI TTS」，需設定伺服器端 `OPENAI_API_KEY`。

## Ollama 的角色

Ollama 可協助整理 Markdown 內容，但 Ollama 的文字生成 endpoint 不會輸出 MP3。本功能的離線音訊由 Piper 完成；不需要將原文送到 OpenAI。網頁端目前把文字直接傳給本機 Piper server。
