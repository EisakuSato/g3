FROM python:3.12-slim

# TeX Live packages needed for the `scienceplots` styles (science, ieee, ...),
# which render text via LaTeX (text.usetex). This is the biggest chunk of the
# image (~1GB) -- if you don't need those styles, use the GUI's "Use
# scienceplots" toggle to turn LaTeX rendering off (manual font/spine/tick
# settings instead), or strip this apt-get layer out of your own build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-extra \
    texlive-fonts-recommended \
    cm-super \
    dvipng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py chart_types.py config_io.py plotting.py ./

EXPOSE 8501

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
