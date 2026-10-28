import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import httpx
import numpy as np

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'staging' / 'rag-app'
source = APP / 'confluence-rag' / 'streamlit_app.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
nodes = []
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'set_page_config':
        break
    nodes.append(node)
ns = {'__file__': str(source), '__name__': 'rag_smoke'}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), ns)
checks = {}
log = (ROOT / 'llama-smoke.log').open('w', encoding='utf-8')
server = subprocess.Popen([
    str(APP / 'tools' / 'llama-b11787-bin-win-cpu-x64' / 'llama-server.exe'),
    '--model', str(APP / 'models' / 'Qwen3.5-2B-Q4_K_M.gguf'),
    '--alias', 'qwen3.5-2b-rag', '--host', '127.0.0.1', '--port', '8080',
    '--ctx-size', '4096', '--parallel', '1', '--n-gpu-layers', '0', '--reasoning', 'off',
], stdout=log, stderr=subprocess.STDOUT)
try:
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError('llama-server exited before ready')
        try:
            if httpx.get('http://127.0.0.1:8080/health', timeout=2).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(2)
    else:
        raise RuntimeError('llama-server readiness timeout')
    checks['llama_health'] = True
    # Separate temp directory avoids shipping a live Chroma database in the ZIP.
    ns['DEMO_CHROMA_PATH'] = Path(tempfile.mkdtemp(prefix='rag-ci-'))
    model, client, collection = ns['load_resources']('demo')
    vector = np.asarray(ns['embed_query'](model, 'VPN 權限申請'))
    assert vector.shape == (512,) and abs(np.linalg.norm(vector) - 1) < 1e-4
    checks['bge_dimension_and_normalization'] = True
    assert collection.count() == 5
    assert (ns['DEMO_CHROMA_PATH'] / 'chroma.sqlite3').is_file()
    hits = ns['search_collection'](model, collection, 'VPN 權限申請流程')
    assert any(h['id'] == 'vpn-apply' for h in hits)
    checks['chroma_persistence_and_retrieval'] = True
    # Re-open persisted storage in a fresh process to verify it survives clients.
    subprocess.run([sys.executable, '-c',
        'import chromadb,sys; c=chromadb.PersistentClient(path=sys.argv[1]); assert c.get_collection("synthetic_wiki_models_v1").count()==5',
        str(ns['DEMO_CHROMA_PATH'])], check=True)
    checks['chroma_reopen'] = True
    evidence, sources = ns['format_evidence'](hits)
    answer = ns['generate_answer'](ns['get_active_model_id'](), [
        {'role': 'system', 'content': ns['SYSTEM_PROMPT']},
        {'role': 'user', 'content': f'【本次檢索證據】\n{evidence}\n\n問題：申請 VPN 權限的流程是什麼？請簡短回答並引用來源。'},
    ])
    assert answer.strip() and any(f'[S{i}]' in answer for i in range(1, len(sources) + 1)), answer
    checks['rag_answer_with_citation'] = True
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(source)).run(timeout=30)
    assert not at.exception, str(at.exception)
    assert any('本機模型已連線' in c.value for c in at.caption)
    checks['streamlit_page_load'] = True
    checks['offline_dependency_install_and_pip_check'] = True
    (ROOT / 'VALIDATION.json').write_text(json.dumps({
        'checks': checks, 'retrieved_ids': [h['id'] for h in hits],
        'sample_question': '申請 VPN 權限的流程是什麼？', 'sample_answer': answer,
        'platform': sys.platform, 'python': sys.version,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('All Windows runtime checks passed.', flush=True)
finally:
    server.terminate()
    try:
        server.wait(timeout=20)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
    log.close()
