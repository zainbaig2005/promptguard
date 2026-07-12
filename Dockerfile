FROM python:3.12-slim
WORKDIR /app
RUN useradd -m promptguard
COPY pyproject.toml README.md ./
COPY promptguard ./promptguard
COPY data ./data
RUN pip install --no-cache-dir .
USER promptguard
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"
CMD ["streamlit", "run", "promptguard/dashboard/app.py", "--server.address=0.0.0.0"]
