# models — fișierele modelelor (NU intră în git)

**Cine lucrează aici:** AI

| Model | Unde rulează | De unde |
|---|---|---|
| `Qwen3.5-4B-Q4_K_M.gguf` (≈2,7 GB) — medicul AI | pe Colab (`colab/shadow_llm.ipynb` îl descarcă singur) sau local, cu `llama-server` | https://huggingface.co/unsloth/Qwen3.5-4B-GGUF |
| alternativă: `gemma-4-E4B_q4_0-it.gguf` (≈5,2 GB) | la fel | https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf |
| `BAAI/bge-small-en-v1.5` (≈65 MB) — vectorii pentru căutare | pe laptop, în serviciul AI | se descarcă singur în `models/embeddings/` la primul `uv run python -m rag.ingest` |

De ce 4B: încape pe un calculator de bord modest (≈3 GB de memorie), iar pe placa din Colab răspunde în 1–2 secunde.
Pe un laptop fără placă video (i3, 2 nuclee) citirea promptului ar dura zeci de secunde, peste limita de 20 s.
