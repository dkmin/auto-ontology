"""KURE-v3 로컬 임베딩 서버 (OpenAI /v1/embeddings 호환).

auto-ontology는 요청 body에 input_type(passage|query)을 보낸다.
KURE-v3는 문서에 "passage: ", 질의에 "query: " 접두사를 붙여야 하므로
sentence-transformers의 prompt_name(document|query)으로 바꿔 인코딩한다.
"""

from __future__ import annotations

import base64
import os
import threading
from typing import Any

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MODEL_ID = os.environ.get("KURE_MODEL", "nlpai-lab/KURE-v3")
MODEL_REV = os.environ.get("KURE_REVISION", "73d5e710bc0b1f324a60746922cbad6d38f480d4")
BATCH = int(os.environ.get("KURE_BATCH", "8"))
# 컬럼 목록이 긴 Table 문서가 있어 상한을 둔다 (기본값은 262,144 토큰).
MAX_SEQ = int(os.environ.get("KURE_MAX_SEQ", "1024"))

device = "mps" if torch.backends.mps.is_available() else "cpu"
model = SentenceTransformer(
    MODEL_ID, revision=MODEL_REV, device=device, model_kwargs={"torch_dtype": torch.bfloat16}
)
model.max_seq_length = MAX_SEQ
# 클라이언트가 동시에 수십 개 요청을 보내므로 모델 호출은 한 번에 하나만 한다.
_lock = threading.Lock()
app = FastAPI()


class EmbedRequest(BaseModel):
    input: str | list[str]
    model: str | None = None
    input_type: str | None = None
    encoding_format: str | None = None
    dimensions: int | None = None
    model_config = {"extra": "allow"}


def _prompt_name(input_type: str | None) -> str:
    if input_type in (None, "passage", "document"):
        return "document"
    if input_type == "query":
        return "query"
    raise HTTPException(400, f"unknown input_type: {input_type}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_ID, "revision": MODEL_REV, "device": device}


@app.post("/v1/embeddings")
def embeddings(req: EmbedRequest) -> dict[str, Any]:
    texts = [req.input] if isinstance(req.input, str) else list(req.input)
    with _lock:
        vecs = model.encode(
            texts,
            prompt_name=_prompt_name(req.input_type),
            batch_size=BATCH,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32)
        if device == "mps":
            torch.mps.empty_cache()
    if req.dimensions:
        vecs = vecs[:, : req.dimensions]
        vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    data = []
    for i, v in enumerate(vecs):
        emb: Any = (
            base64.b64encode(v.tobytes()).decode()
            if req.encoding_format == "base64"
            else v.tolist()
        )
        data.append({"object": "embedding", "index": i, "embedding": emb})
    return {
        "object": "list",
        "data": data,
        "model": req.model or MODEL_ID,
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }
