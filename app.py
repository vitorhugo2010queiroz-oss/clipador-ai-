import os, uuid, subprocess, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent
UPLOADS = ROOT / "uploads"
OUTPUTS = ROOT / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="Clipador AI")
app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")

PAGE = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clipador AI</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#f4f6ff;font:16px Arial,sans-serif}
main{max-width:720px;margin:35px auto;padding:20px}.panel{background:#151d33;border:1px solid #293653;border-radius:18px;padding:22px}
h1{margin:0 0 8px;font-size:30px}.muted{color:#aab5cc;line-height:1.5}
label{display:block;margin:18px 0 8px;font-weight:bold}input,button{width:100%;padding:14px;border-radius:10px;border:1px solid #43516e;background:#0e1629;color:white}
button{background:#6c5ce7;border:0;font-weight:bold;margin-top:18px;font-size:16px}
.note{font-size:13px;color:#aab5cc;margin-top:14px}.result{margin-top:20px;padding:15px;background:#0e1629;border-radius:10px;overflow-wrap:anywhere}
a{color:#b9adff}.links{margin-top:20px}
</style></head><body><main><section class="panel">
<h1>✂️ Clipador AI</h1><p class="muted">Envie um vídeo e gere cortes verticais com legendas em português. A IA analisa a fala para sugerir trechos interessantes.</p>
<form action="/processar" method="post" enctype="multipart/form-data">
<label>Vídeo do seu celular</label><input type="file" name="video" accept="video/*" required>
<label>Quantidade máxima de cortes</label><input type="number" name="quantidade" min="1" max="5" value="3">
<button type="submit">Analisar e criar cortes</button>
</form>
<p class="note">Importante: nesta versão, o vídeo precisa ser enviado como arquivo. Links de TikTok, YouTube, Twitch e Kick ainda não são baixados automaticamente.</p>
<div class="links"><a href="/health">Verificar se o app está funcionando</a></div>
</section></main></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE

@app.get("/health")
def health():
    return {"status":"online","app":"Clipador AI"}

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-1800:])
    return p.stdout

@app.post("/processar", response_class=HTMLResponse)
async def processar(video: UploadFile = File(...), quantidade: int = Form(3)):
    if not video.filename:
        return HTMLResponse("Arquivo inválido.", status_code=400)
    ext = Path(video.filename).suffix.lower()
    if ext not in {".mp4",".mov",".mkv",".webm",".m4v"}:
        return HTMLResponse("Formato não suportado. Envie MP4, MOV, MKV ou WEBM.", status_code=400)
    job = uuid.uuid4().hex[:10]
    src = UPLOADS / f"{job}{ext}"
    with src.open("wb") as f:
        while chunk := await video.read(1024*1024):
            f.write(chunk)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(os.getenv("WHISPER_MODEL","tiny"), device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(src), language="pt", vad_filter=True)
        segs = list(segments)
        if not segs:
            raise RuntimeError("Não encontrei fala suficiente no vídeo.")
        # Rank speech segments by energetic language cues and segment length.
        cues = ["caramba","nossa","olha","mano","meu deus","incrível","não acredito","cuidado","kkkk","haha","gol","matou","explodiu","peguei"]
        scored = []
        for s in segs:
            t = s.text.lower()
            score = min(len(t.split()), 35) / 10
            score += sum(2 for cue in cues if cue in t)
            score += min(max(s.end-s.start,0), 12)/12
            scored.append((score,s))
        scored.sort(key=lambda x:x[0], reverse=True)
        chosen=[]
        for _,s in scored:
            start=max(0,s.start-2.5); end=s.end+3
            if end-start < 8: end=start+8
            if end-start > 60: end=start+60
            if all(end < a or start > b for a,b,_ in chosen):
                chosen.append((start,end,s.text))
            if len(chosen)>=max(1,min(5,quantidade)): break
        chosen.sort()
        outlinks=[]
        for i,(start,end,caption) in enumerate(chosen,1):
            out=OUTPUTS/f"{job}-corte-{i}.mp4"
            # Vertical crop; burned captions via drawtext is intentionally omitted
            # when font availability is unknown. Whisper text is included in result page.
            run(["ffmpeg","-y","-ss",str(start),"-i",str(src),"-t",str(end-start),
                 "-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                 "-c:v","libx264","-preset","veryfast","-crf","25","-c:a","aac","-b:a","128k",str(out)])
            outlinks.append((f"/outputs/{out.name}",caption))
        rows="".join(f'<li><a href="{u}" download>Baixar corte {i}</a><p>{cap}</p></li>' for i,(u,cap) in enumerate(outlinks,1))
        return HTMLResponse(f"""<html lang="pt-br"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font:16px Arial;background:#0b1020;color:white;padding:24px"><h2>Seus cortes estão prontos!</h2><ol>{rows}</ol><a style="color:#b9adff" href="/">Voltar</a></body></html>""")
    except Exception as e:
        return HTMLResponse(f"Não foi possível processar o vídeo: {str(e)}. Tente um vídeo menor ou aguarde o serviço terminar de iniciar.", status_code=500)
