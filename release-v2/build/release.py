"""Build explicit public deployment assets; never copy a developer database."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'staging' / 'rag-app'
DIST = ROOT / 'dist'
ASSETS = {
    'bge-small-zh-v1.5.zip': '7be20df545ec3ef10ce632936cc9762bf741dd3562b17376795d1729125dda29',
    'llama-b11787-bin-win-cpu-x64.zip': '3f60b8c13f73acee3de80fd26d1649604867278821694c5f10e76a59b87498bb',
    'Qwen3.5-2B-Q4_K_M.gguf': 'aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223',
    'SOURCES.json': 'b7d20c305599cdfc1da11175582d07ddf51bd956e3bb37a6c88c5868e5c84fcd',
}


def run(*args):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def extract(src, dest):
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        if z.testzip():
            raise RuntimeError(f'Invalid archive: {src}')
        for name in z.namelist():
            target = (dest / name).resolve()
            if not target.is_relative_to(dest.resolve()):
                raise RuntimeError(f'Unsafe ZIP path: {name}')
        z.extractall(dest)


def archive(src, dst):
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for p in sorted(src.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(src).as_posix())
    with zipfile.ZipFile(dst) as z:
        if z.testzip():
            raise RuntimeError(f'Archive verification failed: {dst}')
    if dst.stat().st_size >= 2 * 1024**3:
        raise RuntimeError(f'Release asset exceeds 2 GiB: {dst}')


def prepare():
    downloads = ROOT / 'downloads'
    downloads.mkdir(exist_ok=True)
    for name, expected in ASSETS.items():
        run('gh', 'release', 'download', 'models-v1', '--repo', os.environ['GH_REPO'],
            '--pattern', name, '--dir', downloads)
        if sha(downloads / name) != expected:
            raise RuntimeError(f'Upstream SHA256 mismatch: {name}')
    shutil.copytree(ROOT / 'app', APP)
    (APP / 'models').mkdir()
    extract(downloads / 'bge-small-zh-v1.5.zip', APP / 'models')
    shutil.copy2(downloads / 'Qwen3.5-2B-Q4_K_M.gguf', APP / 'models')
    runtime = ROOT / 'staging' / 'runtime-extract'
    extract(downloads / 'llama-b11787-bin-win-cpu-x64.zip', runtime)
    servers = list(runtime.rglob('llama-server.exe'))
    if len(servers) != 1:
        raise RuntimeError('Expected exactly one llama-server.exe')
    shutil.copytree(servers[0].parent, APP / 'tools' / 'llama-b11787-bin-win-cpu-x64')
    shutil.copy2(downloads / 'SOURCES.json', APP / 'SOURCES-models-v1.json')
    lock = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    if any(' @ ' in line or line.startswith('-e') for line in lock.splitlines()):
        raise RuntimeError('Nonportable package source in lock')
    (APP / 'requirements-lock.txt').write_text(lock, encoding='utf-8')
    run(sys.executable, '-m', 'pip', 'download', '--only-binary=:all:',
        '-r', APP / 'requirements-lock.txt', '-d', ROOT / 'offline' / 'wheelhouse')
    info = {'tag': 'models-v2', 'commit': os.environ['GITHUB_SHA'],
            'python': sys.version, 'platform': platform.platform(),
            'model_asset_sha256': ASSETS, 'packages': lock.splitlines()}
    (APP / 'BUILD-INFO.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')


def package():
    validation = json.loads((ROOT / 'VALIDATION.json').read_text(encoding='utf-8'))
    if not all(validation['checks'].values()):
        raise RuntimeError('Validation did not pass')
    shutil.copy2(ROOT / 'VALIDATION.json', APP)
    # The release contains code and model files only, not build/test databases or caches.
    for p in APP.rglob('*'):
        if p.name in {'__pycache__', '.chroma_demo_models_v1', 'chroma_db', '.venv'}:
            raise RuntimeError(f'Unexpected generated content in app: {p}')
    DIST.mkdir(exist_ok=True)
    archive(APP, DIST / 'rag-windows-x64-models-v2.zip')
    archive(ROOT / 'offline', DIST / 'python-wheels-win-x64-py311.zip')
    for name in ['README-zh-TW.md', 'BUILD-INFO.json', 'VALIDATION.json']:
        shutil.copy2(APP / name, DIST)
    (DIST / 'SHA256SUMS').write_text(''.join(
        f'{sha(p)}  {p.name}\n' for p in sorted(DIST.iterdir()) if p.is_file()), encoding='utf-8')
    (ROOT / 'release-notes.md').write_text('''# Windows RAG deployment — models-v2

在 Windows x64 上執行本機 RAG，不需要 Docker、Kubernetes 或 GPU。

- **rag-windows-x64-models-v2.zip**：目前 Streamlit RAG 程式、完整 BGE、Qwen3.5-2B-Q4_K_M、llama.cpp b11787、安裝及啟動 CMD、完整套件版本鎖定。
- **python-wheels-win-x64-py311.zip**：Python 3.11 x64 離線套件；解壓到部署目錄後會出現 wheelhouse。
- **README-zh-TW.md**：繁體中文安裝說明與既有 ChromaDB 搬移方式。
- **BUILD-INFO.json / VALIDATION.json / SHA256SUMS**：來源、實測紀錄與附件校驗碼。

## 開始使用
1. 預先安裝 Python 3.11 x64（含 py launcher）。
2. 解壓部署包；離線安裝時也解壓 wheel 附件到相同目錄。
3. 執行 install.cmd，再依序執行 start-llm.cmd、start-app.cmd。
4. 開啟 http://127.0.0.1:8501 ，選 Demo 範例，詢問 VPN 申請流程。

模型版本與 models-v1 相同，建置時比對固定 SHA256。僅包含五份虛構 Demo 文件，由程式首次執行時建立資料庫；正式 ChromaDB 與文件需另外搬移。

Windows CI 已驗證離線套件安裝、pip check、BGE 512 維與正規化、Chroma 持久化及檢索、llama.cpp 載入／生成與 RAG 引用、Streamlit 頁面載入。詳見 VALIDATION.json。目標電腦的硬體與公司執行政策仍需實機驗收。

已知限制：沿用原程式的字元預算，長問題／多輪對話可能超出 4096 token context；尚無文件匯入介面、登入或文件權限控制；只綁定 localhost。Python 安裝程式不含在附件中。

上游授權適用：Qwen Apache-2.0、BGE MIT、llama.cpp MIT，Python 套件依各自授權。
''', encoding='utf-8')


if __name__ == '__main__':
    {'prepare': prepare, 'package': package}[sys.argv[1]]()
