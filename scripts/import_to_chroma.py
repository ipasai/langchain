#!/usr/bin/env python3
"""把現有 data/doc_index.json 的檔案匯入本機 Chroma server 的簡易腳本

用法：
  CHROMA_SERVER_URL=http://127.0.0.1:8001 python scripts/import_to_chroma.py
"""
import os
import sys
import json
import base64
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_INDEX = os.path.join(ROOT, "data", "doc_index.json")
CHROMA_URL = os.environ.get("CHROMA_SERVER_URL", "http://127.0.0.1:8001")


def load_index():
    if not os.path.exists(DATA_INDEX):
        print("no doc_index.json found at", DATA_INDEX)
        return []
    with open(DATA_INDEX, "r", encoding="utf-8") as f:
        return json.load(f)


def post_index_item(item):
    path = item.get("path") or item.get("local_path") or item.get("filepath")
    if not path or not os.path.exists(path):
        print("skipping", item.get("id"), "no file at", path)
        return False
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")
    payload = {"id": item.get("id"), "filename": item.get("filename", os.path.basename(path)), "content_base64": b64}
    url = CHROMA_URL.rstrip("/") + "/index"
    try:
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        print("indexed", item.get("id"), "->", r.json())
        return True
    except Exception as e:
        print("failed to index", item.get("id"), e)
        return False


def main():
    idx = load_index()
    if not idx:
        print("no entries to import")
        return
    ok = 0
    for item in idx:
        try:
            res = post_index_item(item)
            if res:
                ok += 1
        except KeyboardInterrupt:
            break
    print(f"done: {ok}/{len(idx)} imported")


if __name__ == "__main__":
    main()
