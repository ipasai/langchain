# LangChain Web (Next.js + Tailwind)

此資料夾為從 Streamlit 轉換出的純前端 scaffold，包含基本的 Chat、DB 代理與英文學習 UI 範例。

快速開始：

```bash
cd web
npm install
# 若後端仍在 Python，設定 BACKEND_URL
export BACKEND_URL=http://localhost:8000
npm run dev
```

測試

此專案使用 `vitest` 做輕量測試。執行：

```bash
cd web
npm install
npm test
```

範例測試包含：
- `tests/llm.test.js`：測試 `get_recommendation` 與預設模型清單回應
- `tests/db.test.js`：測試 `db` API 的 `test` action

E2E 測試

專案也包含 Playwright E2E 測試（`tests/e2e.spec.js`）。CI workflow 會在 build 後啟動應用並執行 E2E。若要在本機執行：

```bash
cd web
npm install
npx playwright install --with-deps
npm run build
npm run start &
npx playwright test
```

備註：目前 `pages/api/*` 為 proxy 路由，會把請求轉發到 `BACKEND_URL`。接下來會把後端邏輯移植成 Next.js API routes 或 Node.js microservices。

部署與 Docker

此專案包含 `Dockerfile` 與 `docker-compose.yml`（repo 根目錄）。透過 Docker 可在 production 模式下執行 web 服務：

```bash
# 在 repo 根目錄
docker-compose build
docker-compose up -d
```

或使用 GitHub Actions 自動建置並推到 GitHub Container Registry（GHCR），參考 workflow `/.github/workflows/deploy-docker.yml`（需要設定 repository secrets，通常透過 `GITHUB_TOKEN` 即可上傳至 GHCR）。

OpenAPI 規格

在 `web/openapi.yaml` 中有簡易的 OpenAPI 3.0 規格，描述了 `/api/llm` 與 `/api/db` 的主要 action，方便生成文件或用於 API client。可使用 Swagger UI 或 Redoc 檢視。

Swagger / Redoc

我已在應用中加入一個簡易的 API Docs 頁面：

- [http://localhost:3000/docs](http://localhost:3000/docs) （開發模式）會載入 `/openapi.yaml` 並以 Redoc 呈現。

Vercel 部署

若要部署到 Vercel：

1. 在 Vercel 建立新專案，選擇 GitHub repo 並設定 root 為 `web`。
2. 在 Vercel 專案的 Environment Variables 裡加入 `OPENAI_API_KEY`, `OLLAMA_BASE_URL`, `GOOGLE_API_KEY` 等變數。
3. 建置命令：`npm run build`，啟動命令：`npm start`。

Docker Hub

已新增 GitHub Actions workflow `/.github/workflows/deploy-docker-hub.yml` 用來將 `web` 建置後推到 Docker Hub。請在 repo secrets 中設定 `DOCKERHUB_USERNAME` 與 `DOCKERHUB_TOKEN`。
