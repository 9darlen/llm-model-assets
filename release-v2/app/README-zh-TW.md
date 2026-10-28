# Windows 單機 RAG 部署包 — models-v2

此版本打包 Streamlit RAG 程式、BGE embedding 模型、Qwen GGUF 與 llama.cpp Windows CPU x64。無須 Docker、Kubernetes 或 GPU。

## 安裝及啟動

1. 安裝官方 Python 3.11 x64，包含 Python Launcher (`py`)。建議 Windows 10/11 x64；ARM64 不在此包的驗證範圍。
2. 將 `rag-windows-x64-models-v2.zip` 解壓縮到可寫入的目錄，例如 `C:\rag-app`。請勿直接在 ZIP 內執行。
3. 若要離線安裝，將 `python-wheels-win-x64-py311.zip` 解壓縮到同一目錄，使 `wheelhouse` 與 `install.cmd` 位於同一層。Python 本身需預先安裝；此附件不含 Python 安裝程式。
4. 執行 `install.cmd`。有 wheelhouse 時使用離線套件，否則連線至 PyPI 安裝。所有完整版本記錄在 `requirements-lock.txt`。
5. 執行 `start-llm.cmd`，等待模型載入完成，保持視窗開啟。
6. 執行 `start-app.cmd`，瀏覽器開啟 http://127.0.0.1:8501 。
7. 選擇「Demo 範例」，提問「申請 VPN 權限的流程是什麼？」。首次提問會以程式內的五份虛構文件建立 Demo ChromaDB。

若企業政策封鎖 CMD 或 EXE，需由 IT 允許對應程式；此包不會更改系統政策。CPU 推論速度依硬體而異，請在目標電腦驗收。

## 使用既有 ChromaDB

此公開部署包只含虛構 Demo 文本，不包含使用者本機的資料庫、文件、密碼或對話紀錄。

停止原電腦的資料庫讀寫後，將完整持久化目錄複製到部署根目錄的 `chroma_db`，包含 `chroma.sqlite3` 和向量索引子目錄。程式預期 collection 名稱為 `wiki_chunks`，原文存於 documents，向量來自相同 BGE 模型、512 維且正規化。metadata 可包含 title、source_url、version。

先備份原資料庫，並確認來源 ChromaDB 版本與本包一致；開啟 PersistentClient 可能涉及儲存格式初始化或遷移，並非檔案系統層級的唯讀模式。完成後在介面選擇「既有 ChromaDB」。正式資料應透過適當存取控制的管道另外搬移。

## 設定與限制

- LLM：Qwen3.5-2B-Q4_K_M；CPU llama.cpp b11787；本機 8080 埠；context 4096；parallel 1；reasoning off。
- BGE：bge-small-zh-v1.5，輸入最大 512 tokens。
- RAG：Top-K 3；每段原文最多 950 字元；證據總計最多 3200 字元；回答上限 1024 tokens。
- 此版沿用原程式。長問題及多輪歷史仍可能超出 context token 預算，遇到 context 錯誤可先清除對話、縮短問題；完整的 token 預算控制尚未實作。
- 本包沒有文件上傳／切塊匯入介面，也沒有登入驗證與文件權限隔離，服務僅綁定 localhost。
- 首次安裝後，模型載入與推論不需要下載模型；執行時可離線使用。

## 來源、驗證及授權

模型與 llama.cpp 沿用 models-v1 的相同資產，建置時依固定 SHA256 驗證。`SOURCES-models-v1.json` 保存來源紀錄；上游授權適用：Qwen Apache-2.0、BGE MIT、llama.cpp MIT。Python 套件各自的授權保留於 wheel 內。

Release 的 `SHA256SUMS` 記錄附件雜湊，可使用 PowerShell `Get-FileHash -Algorithm SHA256 <檔案路徑>` 比對。`BUILD-INFO.json` 記錄建置環境與完整套件版本；`VALIDATION.json` 記錄 Windows runner 的實際測試。

本包不包含可跨電腦直接複製的 `.venv`；每台電腦以 install.cmd 建立自己的環境。若要更新現有安裝，先解壓到新的目錄，驗證後再搬移已備份的資料庫。
