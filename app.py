# app.py
# Streamlit – Nivelamento A–Z (Fountas & Pinnell) sem chave de API
# - Upload múltiplo de PDFs/EPUBs (nomeados por ISBN)
# - Upload da rubrica (aba: "A-Z Fountas&Pinnel": Nível, Frase e Estrutura, Vocabulário, Imagens)
# - Extração de texto local (PyPDF2 / ebooklib)
# - Classificação heurística (regras transparentes) + justificativa alinhada à rubrica
# - Download dos resultados em CSV/XLSX
#
# Como rodar localmente:
#   1) python -m venv .venv && source .venv/bin/activate  (no Windows: .venv\Scripts\activate)
#   2) pip install -r requirements.txt
#   3) streamlit run app.py
#
# Como rodar no Streamlit Cloud:
#   - Suba app.py e requirements.txt num repositório (GitHub) e conecte no share.streamlit.io

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    from ebooklib import epub
    from bs4 import BeautifulSoup
except Exception:
    epub = None
    BeautifulSoup = None

st.set_page_config(page_title="Nivelamento A–Z (Fountas & Pinnell)", layout="wide")
st.title("📚 Nivelamento A–Z (Fountas & Pinnell) – sem API Key")
st.caption("Faça upload da rubrica e de múltiplos PDFs/EPUBs (nomeados por ISBN). O app extrai amostras, aplica heurísticas e gera nível + justificativa baseada na rubrica.")

with st.expander("ℹ️ Como funciona (resumo)", expanded=False):
    st.markdown("""
- **Sem chaves**: análise local, heurísticas transparentes.
- **Amostra**: até **50.000 caracteres** por livro.
- **Heurísticas**: comprimento médio de frase, conectivos/subordinação, variedade lexical, palavras longas.
- **Justificativa**: cita critérios da sua **rubrica A–Z**.
    """)

MAX_CHARS = 50_000
SENT_SPLIT = r"[.!?]+[\s\n]"
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")

def is_isbn_name(name: str) -> bool:
    base = re.sub(r"\.[^.]+$", "", name)
    only = re.sub(r"[^0-9Xx]", "", base)
    return bool(re.fullmatch(r"(?:\d{10}|\d{13}|\d{9}[0-9Xx])", only))

def extract_isbn(name: str) -> str:
    base = re.sub(r"\.[^.]+$", "", name)
    only = re.sub(r"[^0-9Xx]", "", base)
    return only or base

def safe_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:MAX_CHARS]

def read_pdf(file) -> str:
    if PyPDF2 is None:
        st.error("PyPDF2 não está instalado. Adicione 'PyPDF2' ao requirements.txt.")
        return ""
    try:
        reader = PyPDF2.PdfReader(file)
        text = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            text.append(t)
            if sum(len(x) for x in text) > MAX_CHARS:
                break
        return safe_text(" ".join(text))
    except Exception as e:
        st.warning(f"Falha ao ler PDF: {e}")
        return ""

def read_epub(file) -> str:
    if epub is None or BeautifulSoup is None:
        st.error("ebooklib e bs4 não estão instalados. Adicione 'ebooklib' e 'beautifulsoup4' ao requirements.txt.")
        return ""
    try:
        book = epub.read_epub(file)
        text = []
        for item in book.get_items():
            if item.get_type() == 9:  # DOCUMENT
                try:
                    soup = BeautifulSoup(item.get_body_content(), "html.parser")
                    t = soup.get_text(" ", strip=True)
                except Exception:
                    t = ""
                if t:
                    text.append(t)
                if sum(len(x) for x in text) > MAX_CHARS:
                    break
        return safe_text(" ".join(text))
    except Exception as e:
        st.warning(f"Falha ao ler EPUB: {e}")
        return ""

def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return read_pdf(uploaded_file)
    if name.endswith(".epub"):
        return read_epub(uploaded_file)
    st.warning("Formato não suportado (use .pdf ou .epub).")
    return ""

def split_sentences(text: str):
    parts = re.split(SENT_SPLIT, text)
    return [p.strip() for p in parts if p.strip()]

def tokenize(text: str):
    return WORD_RE.findall(text.lower())

ADV_CONNECTIVES = set("""because although however whereas moreover nevertheless therefore furthermore unless despite since while whenever wherever notwithstanding consequently albeit hence nonetheless whereby""".split())
SUB_CONJ = set("""because although whereas unless since while whenever wherever though even though provided that so that in order that after before until once as long as as if as though""".split())

def compute_features(text: str):
    sents = split_sentences(text)
    tokens = tokenize(text)
    if not tokens or not sents:
        return None

    avg_sent_len = np.mean([len(tokenize(s)) for s in sents])
    ttr = len(set(tokens)) / max(1, len(tokens))
    long_word_ratio = sum(1 for w in tokens if len(w) >= 9) / max(1, len(tokens))
    connectives = sum(1 for w in tokens if w in ADV_CONNECTIVES)
    sub_conj = sum(1 for w in tokens if w in SUB_CONJ)
    commas_per_sent = text.count(",") / max(1, len(sents))

    return {
        "avg_sent_len": float(avg_sent_len),
        "ttr": float(ttr),
        "long_word_ratio": float(long_word_ratio),
        "connectives": int(connectives),
        "sub_conj": int(sub_conj),
        "commas_per_sent": float(commas_per_sent),
        "num_sents": int(len(sents)),
        "num_tokens": int(len(tokens)),
    }

def map_to_band(avg_sent_len: float):
    if avg_sent_len <= 6: return ("A", "D")
    if avg_sent_len <= 10: return ("E", "I")
    if avg_sent_len <= 14: return ("J", "M")
    if avg_sent_len <= 19: return ("N", "S")
    return ("T", "Z")

def refine_letter(band_start: str, band_end: str, feats: dict):
    letters = [chr(c) for c in range(ord(band_start), ord(band_end) + 1)]
    score = 0.0
    score += 0.8 * min(1.0, feats.get("long_word_ratio", 0.0) * 5)
    score += 0.6 * min(1.0, feats.get("ttr", 0.0) * 2)
    score += 0.7 * min(1.0, feats.get("commas_per_sent", 0.0) / 2)
    score += 0.5 * min(1.0, (feats.get("connectives", 0) + feats.get("sub_conj", 0)) / 10)
    idx = int(round(score * (len(letters) - 1)))
    return letters[max(0, min(len(letters) - 1, idx))]

def level_from_features(feats: dict):
    band = map_to_band(feats["avg_sent_len"])
    letter = refine_letter(band[0], band[1], feats)
    return letter, band

def justify(level: str, band: tuple, feats: dict, rubric_df: pd.DataFrame):
    row = None
    if "Nível" in rubric_df.columns:
        r = rubric_df[rubric_df["Nível"].astype(str).str.upper()==level]
        if not r.empty:
            row = r.iloc[0].to_dict()
    parts = []
    parts.append(f"Média de {feats['avg_sent_len']:.1f} palavras por frase; {'alta' if feats['avg_sent_len']>=15 else 'baixa' if feats['avg_sent_len']<=6 else 'moderada'} complexidade frasal.")
    if feats["commas_per_sent"]>0.3 or (feats["connectives"]+feats["sub_conj"])>=2:
        parts.append("Presença de conectivos/subordinação e uso de vírgulas indicando orações compostas.")
    else:
        parts.append("Poucos conectivos/subordinação; frases mais simples e diretas.")
    if feats["long_word_ratio"]>=0.08:
        parts.append("Vocabulário com proporção relevante de palavras longas (≥9 letras).")
    else:
        parts.append("Vocabulário predominantemente de palavras curtas e frequentes.")
    if row:
        parts.append(f"Alinhado à rubrica do nível {level}: {row.get('Frase e Estrutura','')} | {row.get('Vocabulário','')}")
    return " ".join(parts)

st.header("1) Upload da Rubrica (Aba “A-Z Fountas&Pinnel”)")
rubrica_file = st.file_uploader("Envie sua planilha XLSX da rubrica", type=["xlsx","xls"], accept_multiple_files=False)
rubrica_df = None
if rubrica_file is not None:
    try:
        xl = pd.ExcelFile(rubrica_file)
        sheet_name = next((s for s in xl.sheet_names if "fountas" in s.lower()), xl.sheet_names[0])
        rubrica_df = pd.read_excel(xl, sheet_name=sheet_name)
        ren = {}
        for col in rubrica_df.columns:
            lc = col.strip().lower()
            if "nível" in lc or "nivel" in lc: ren[col] = "Nível"
            elif "frase" in lc or "estrutura" in lc: ren[col] = "Frase e Estrutura"
            elif "vocab" in lc: ren[col] = "Vocabulário"
            elif "imagem" in lc: ren[col] = "Imagens"
        rubrica_df = rubrica_df.rename(columns=ren)
        expected = ["Nível", "Frase e Estrutura", "Vocabulário", "Imagens"]
        missing = [c for c in expected if c not in rubrica_df.columns]
        if missing:
            st.error(f"A rubrica precisa ter as colunas: {expected}. Ausentes: {missing}")
            rubrica_df = None
        else:
            st.success(f"Rubrica carregada: {len(rubrica_df)} linhas (aba: {sheet_name}).")
            st.dataframe(rubrica_df.head(10), use_container_width=True)
    except Exception as e:
        st.error(f"Falha ao ler rubrica: {e}")

st.header("2) Upload dos Livros (PDF/EPUB) – nomeados pelo ISBN")
books = st.file_uploader("Envie seus arquivos", type=["pdf","epub"], accept_multiple_files=True)
if books:
    st.info("Dica: o nome do arquivo deve ser o ISBN (ex.: 9788535914849.pdf).")
    st.write(pd.DataFrame({
        "Arquivo": [b.name for b in books],
        "ISBN (detectado)": [extract_isbn(b.name) for b in books],
        "Nome parece ISBN?": ["Sim" if is_isbn_name(b.name) else "Não" for b in books]
    }))

st.header("3) Classificar")
run = st.button("▶️ Executar nivelamento", disabled=(rubrica_df is None or not books))

if run and rubrica_df is not None and books:
    results = []
    prog = st.progress(0)
    for i, b in enumerate(books):
        isbn = extract_isbn(b.name)
        with st.spinner(f"Lendo {b.name}..."):
            text = extract_text(b)
        if not text:
            results.append({"ISBN": isbn, "Arquivo": b.name, "Nível": "?", "Justificativa": "Falha ao extrair texto", "Evidências": ""})
            prog.progress((i+1)/len(books))
            continue
        feats = compute_features(text)
        if not feats:
            results.append({"ISBN": isbn, "Arquivo": b.name, "Nível": "?", "Justificativa": "Texto insuficiente para análise", "Evidências": ""})
            prog.progress((i+1)/len(books))
            continue
        level, band = level_from_features(feats)
        just = justify(level, band, feats, rubrica_df)
        evid = [
            f"avg_sent_len={feats['avg_sent_len']:.1f}",
            f"commas_per_sent={feats['commas_per_sent']:.2f}",
            f"long_word_ratio={feats['long_word_ratio']:.2f}",
            f"connectives={feats['connectives']}, sub_conj={feats['sub_conj']}",
        ]
        results.append({
            "ISBN": isbn, "Arquivo": b.name, "Nível": level,
            "Justificativa": just, "Evidências": " | ".join(evid)
        })
        prog.progress((i+1)/len(books))

    st.subheader("Resultados")
    df_out = pd.DataFrame(results)
    st.dataframe(df_out, use_container_width=True)

    csv_bytes = df_out.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV", data=csv_bytes, file_name="nivelamento_az.csv", mime="text/csv")

    xlsx_buf = BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="xlsxwriter") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Nivelamento")
    st.download_button("⬇️ Baixar XLSX", data=xlsx_buf.getvalue(), file_name="nivelamento_az.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()
st.caption("Heurística aproximada baseada em traços linguísticos; use como triagem inicial. Ajuste limiares conforme sua realidade pedagógica.")
