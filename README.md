# Nivelamento A–Z (Fountas & Pinnell) — Streamlit (Repo B: PDF + EPUB)

App web (Streamlit) para nivelamento **A–Z** usando heurísticas transparentes baseadas na sua **rubrica**. 
- ✅ Upload da **rubrica** (XLSX, aba “A-Z Fountas&Pinnel”: `Nível`, `Frase e Estrutura`, `Vocabulário`, `Imagens`)
- ✅ Upload de **múltiplos livros** em **PDF** e **EPUB** (nomeados pelo **ISBN**)
- ✅ Extração de texto local (PyPDF2 / ebooklib+bs4)
- ✅ Nivel sugerido + **justificativa** alinhada à rubrica
- ✅ **Download** dos resultados em **CSV** e **XLSX**
- 🚫 **Sem API externa** (roda 100% local/Cloud)

---

## ⚡ Deploy no Streamlit Community Cloud
1. Crie um repositório no GitHub com estes 3 arquivos: `app.py`, `requirements.txt`, `README.md`.
2. Acesse: https://share.streamlit.io (ou “Deploy an app” no site do Streamlit).
3. Conecte seu repositório e clique em **Deploy**.
4. Aguarde a instalação das dependências (~3–8 min). Se travar em “Processing dependencies...”:
   - Clique **Manage app → Reboot** (reinicia o build).
   - Faça um **commit** simples (ex.: edite este README) e redeploy.
   - Confira **Logs** em *Manage app → Logs* (erros de PyPI são intermitentes).

> Dica: Se você não precisa de EPUB, troque o `requirements.txt` pelo do Repo A (PDF-only) para build mais rápido.

---

## 🖥️ Rodar localmente
1. **Instale Python 3.11+** e abra o Terminal (Prompt de Comando no Windows).
2. Dentro de uma pasta vazia, crie um ambiente e instale dependências:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Rode o app:
   ```bash
   streamlit run app.py
   ```
4. Abra o link `http://localhost:8501` no navegador.

---

## 🧭 Como usar
1. **Upload da rubrica** (XLSX). A aba deve ser “A-Z Fountas&Pinnel” (ou similar) e conter as colunas esperadas.
2. **Upload dos livros** (PDF/EPUB) **nomeados pelo ISBN** (ex.: `9788535914849.pdf`).
3. Clique em **“Executar nivelamento”**.
4. Veja `ISBN`, `Arquivo`, `Nível`, `Justificativa`, `Evidências`.
5. Baixe **CSV** e **XLSX** pelos botões.

---

## 🧪 Como a heurística decide o nível
- **Comprimento médio das frases** (palavras por frase) → define a **faixa**: A–D, E–I, J–M, N–S, T–Z.
- **Variedade lexical** (TTR), **palavras longas**, **vírgulas por frase** e **conectivos/subordinações** → refinam a **letra** dentro da faixa.
- A **justificativa** inclui trechos da sua **rubrica** do nível estimado.

> É uma **triagem inicial**. Ajuste os limiares no código conforme sua realidade pedagógica.

---

## ❗Problemas comuns no Streamlit Cloud
- **Travado em “Processing dependencies…”**: Reboot + novo commit; confira *Logs*.
- **Erro ao ler EPUB**: alguns arquivos têm proteção/estrutura incomum; prefira PDF.
- **Memória**: muitos livros grandes de uma vez podem esgotar recursos; suba em lotes.

---

## 📂 Estrutura
```
.
├── app.py
├── requirements.txt
└── README.md
```
