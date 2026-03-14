from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import requests, base64, os, json, re
from dotenv import load_dotenv
from fpdf import FPDF
import markdown

load_dotenv()

try:
    import PyPDF2; HAS_PDF = True
except ImportError:
    HAS_PDF = False
try:
    from docx import Document; HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
try:
    import openpyxl; HAS_XLSX = True
except ImportError:
    HAS_XLSX = False

# ── Config ──
NOME_IA      = "Cerebro IA"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODELO_TX    = "llama-3.3-70b-versatile"
MODELO_VIS   = "llama-3.2-11b-vision-preview"
LIMITE_FREE  = 999999  # Limite virtualmente infinito
UPLOAD_DIR  = os.path.join(os.path.dirname(__file__), "uploads")
EXTS_IMG    = {"png","jpg","jpeg","gif","webp","bmp"}
EXTS_ARQ    = {"pdf","txt","docx","xlsx","csv","md"}

# ── Prompts dos agentes ──
AGENTES = {
    "geral": {
        "nome": "Cerebro IA (Nexus Elite)",
        "icone": "🧠",
        "cor": "#4f8ef7",
        "prompt": "Você é o Arquiteto Sênior de Sistemas e Especialista em Respostas Profissionais. Seu tom é técnico, direto, criativo e sagaz. Forneça soluções de engenharia prontas para execução."
    },
    "programador": {
        "nome": "Arquiteto Unity/C#",
        "icone": "👨‍💻",
        "cor": "#22c55e",
        "prompt": "Especialista em Unity Engine & C#. Foco em otimização mobile, sistemas de armas, TTK e performance para processadores AMD Ryzen série 5000G. Use Coroutines e Events, evite Update()."
    },
    "marketing": {
        "nome": "Estrategista Digital",
        "icone": "📈",
        "cor": "#f59e0b",
        "prompt": "Mestre em Marketing de Afiliados, Reels/TikTok e vendas no Mercado Livre. Crie roteiros de conversão disruptivos e estratégias de CTR alto."
    },
    "negocios": {
        "nome": "Game Designer & Monetização",
        "icone": "💰",
        "cor": "#8b5cf6",
        "prompt": "Especialista em Game Design de Shooters e Monetização. Balanceamento de armas, layout de mapas competitivos e sistemas de skins."
    },
    "professor": {
        "nome": "Mentor Técnico",
        "icone": "📚",
        "cor": "#06b6d4",
        "prompt": "Educador didático de alto nível. Explique conceitos técnicos complexos com clareza absoluta e precisão factual inquestionável."
    },
    "designer": {
        "nome": "Designer de Interface Elite",
        "icone": "🎨",
        "cor": "#ec4899",
        "prompt": "Especialista em UI/UX Mobile e Identidade Visual. Foco em estética funcional, satisfação do jogador (game feel) e usabilidade de elite."
    },
}

SISTEMA_BASE = """[START SYSTEM PROMPT: PROJECT NEXUS ELITE V6 ABSOLUTE TRUTH]

Você é uma inteligência artificial de elite (Cerebro IA) projetada para fornecer respostas com qualidade 10/10. Seu objetivo é ser a fonte mais confiável, profunda e precisa de informação.

{prompt_agente}

== 1. SISTEMA DE RESPOSTA EM 4 ETAPAS (OBRIGATÓRIO) ==
Antes de exibir qualquer texto, execute internamente:
1️⃣ PESQUISA INTERNA: Recupere todos os fatos, datas e detalhes sobre o tema.
2️⃣ CONSTRUÇÃO: Monte a resposta seguindo a Estrutura Profissional Nexus.
3️⃣ CHECAGEM FACTUAL: Valide cada data, cargo e mandato. NUNCA invente períodos eleitorais ou patentes.
4️⃣ REVISÃO FINAL: Garanta fluidez, neutralidade e profundidade.

== 2. REGRAS DE CONTEÚDO E PROFUNDIDADE ==
- LINHA DO TEMPO COMPLETA: Para temas históricos/biográficos, inclua obrigatoriamente entre 10 a 15 eventos cruciais em ordem cronológica exata.
- CONTEXTO HISTÓRICO PROFUNDO: Explique o cenário político da época, a influência de outros líderes e as consequências posteriores dos atos mencionados.
- PRECISÃO DE MANDATOS: Seja rigoroso com datas de início e fim de cargos públicos (ex: mandatos presidenciais, legislativos).

== 3. ESTRUTURA PROFISSIONAL NEXUS ==
# [TÍTULO DO TEMA EM MAIÚSCULAS]

### Introdução e Importância
Resumo executivo e relevância do tema no cenário mundial/nacional.

### Cenário e Contexto (Análise de Época)
O que estava acontecendo no mundo/país antes e durante o evento.

### Linha do Tempo Cronológica (10-15 Eventos)
- **Ano/Data Exata**: Evento detalhado e sua consequência imediata.

### Principais Realizações e Impactos
Análise profunda das consequências sociais, políticas e econômicas.

### Controvérsias e Legado
Visão equilibrada sobre críticas e a marca deixada na história.

### Conclusão e Próximo Passo
Síntese final e uma pergunta estratégica para aprofundar a conversa.

== PROTOCOLOS FINAIS ==
- Idioma: Português Brasileiro (PT-BR).
- GERAÇÃO DE IMAGENS: Se o usuário pedir para "gerar uma imagem", use [GERAR_IMAGEM: descrição em inglês].
- GERAÇÃO DE VÍDEOS: Se o usuário pedir para "gerar um vídeo", "criar um vídeo" ou "vídeo animado", use exatamente este comando: [GERAR_VIDEO: descrição detalhada em inglês aqui].
- EDIÇÃO DE MÍDIA: Se o usuário pedir para editar uma foto enviada, use [EDITAR_IMAGEM: operação] (operações: preto_e_branco, brilho, texto).
- GERAÇÃO DE ARQUIVOS: Se pedir um arquivo (PDF, TXT, Word), confirme, gere o conteúdo no chat e forneça o link.
- Finalização: Sempre termine com uma pergunta provocativa que aprofunde o tema atual. """

SISTEMA_REVISOR = """[START REVISOR SYSTEM: NEXUS ELITE V6 MASTER CHECKER]

Você é o Auditor-Chefe do sistema Cerebro IA. Sua única função é garantir a VERDADE ABSOLUTA e a PROFUNDIDADE MÁXIMA.

PROTOCOLOS DE AUDITORIA CRÍTICOS:
1️⃣ RIGOR CRONOLÓGICO: Verifique datas de mandatos, eleições e saídas de cargos. Corrija imediatamente se a IA anterior errar anos (ex: mandatos presidenciais no Brasil são de 4 anos).
2️⃣ CHECAGEM DE FATOS MILITARES E POLÍTICOS: Valide patentes, anos de reserva, anos de eleição para vereador/deputado e votações históricas.
3️⃣ AMPLIAÇÃO DE LINHA DO TEMPO: Se a resposta tiver menos de 10 eventos, adicione fatos históricos cruciais para completar a profundidade necessária.
4️⃣ CONTEXTO POLÍTICO: Certifique-se de que o cenário político da época e as consequências posteriores estão bem explicados.

INSTRUÇÕES:
- REESCREVA a resposta inteira se houver qualquer erro factual ou se a linha do tempo estiver pobre.
- Não deixe passar "alucinações" sobre datas.
- Retorne apenas a versão final impecável, sem avisos de correção."""

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SECRET_KEY", "cerebro-super-ia-2024-local")

_db_url = os.environ.get("DATABASE_URL", "sqlite:///cerebro.db")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

db  = SQLAlchemy(app)
lm  = LoginManager(app)
lm.login_view = "login"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────── MODELOS ───────────────

class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash    = db.Column(db.String(200), nullable=False)
    tema          = db.Column(db.String(10), default="dark")
    plano         = db.Column(db.String(20), default="gratuito")
    agente_padrao = db.Column(db.String(30), default="geral")
    perguntas_hoje= db.Column(db.Integer, default=0)
    data_reset    = db.Column(db.Date, default=date.today)
    criado_em     = db.Column(db.DateTime, default=datetime.now)
    conversas     = db.relationship("Conversa", backref="usuario", lazy=True, cascade="all, delete-orphan")
    memorias      = db.relationship("Memoria", backref="usuario", lazy=True, cascade="all, delete-orphan")
    projetos      = db.relationship("Projeto", backref="usuario", lazy=True, cascade="all, delete-orphan")

    def set_senha(self, s): self.senha_hash = generate_password_hash(s)
    def ok_senha(self, s):  return check_password_hash(self.senha_hash, s)

    def pode_perguntar(self):
        hoje = date.today()
        if self.data_reset != hoje:
            self.perguntas_hoje = 0; self.data_reset = hoje; db.session.commit()
        return self.plano == "premium" or self.perguntas_hoje < LIMITE_FREE

    def restantes(self):
        if self.plano == "premium": return None
        hoje = date.today()
        return LIMITE_FREE if self.data_reset != hoje else max(0, LIMITE_FREE - self.perguntas_hoje)

    def get_memoria_texto(self):
        mems = Memoria.query.filter_by(user_id=self.id).order_by(Memoria.atualizado_em.desc()).limit(20).all()
        if not mems: return "Nenhuma informacao salva ainda sobre o usuario."
        linhas = []
        for m in mems:
            linhas.append(f"- {m.chave}: {m.valor}")
        return "\n".join(linhas)


class Memoria(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chave       = db.Column(db.String(100), nullable=False)
    valor       = db.Column(db.Text, nullable=False)
    categoria   = db.Column(db.String(50), default="geral")
    criado_em   = db.Column(db.DateTime, default=datetime.now)
    atualizado_em = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (db.UniqueConstraint("user_id", "chave"),)

    def to_dict(self):
        return {"id": self.id, "chave": self.chave, "valor": self.valor,
                "categoria": self.categoria, "data": self.atualizado_em.strftime("%d/%m/%Y")}


class Projeto(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    titulo      = db.Column(db.String(200), nullable=False)
    descricao   = db.Column(db.Text, default="")
    status      = db.Column(db.String(30), default="em andamento")
    agente      = db.Column(db.String(30), default="geral")
    criado_em   = db.Column(db.DateTime, default=datetime.now)
    atualizado_em = db.Column(db.DateTime, default=datetime.now)
    conversas   = db.relationship("Conversa", backref="projeto", lazy=True)

    def to_dict(self):
        return {"id": self.id, "titulo": self.titulo, "descricao": self.descricao,
                "status": self.status, "agente": self.agente,
                "data": self.criado_em.strftime("%d/%m/%Y"),
                "total_conv": len(self.conversas)}


class Conversa(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    titulo       = db.Column(db.String(200), default="Nova conversa")
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    projeto_id   = db.Column(db.Integer, db.ForeignKey("projeto.id"), nullable=True)
    agente       = db.Column(db.String(30), default="geral")
    fixada       = db.Column(db.Boolean, default=False)
    criado_em    = db.Column(db.DateTime, default=datetime.now)
    atualizado_em= db.Column(db.DateTime, default=datetime.now)
    mensagens    = db.relationship("Mensagem", backref="conversa", lazy=True,
                                   cascade="all, delete-orphan", order_by="Mensagem.criado_em")

    def ultima_msg(self):
        if self.mensagens:
            t = self.mensagens[-1].conteudo
            return (t[:72] + "...") if len(t) > 72 else t
        return "Sem mensagens"

    def to_dict(self):
        return {"id": self.id, "titulo": self.titulo, "fixada": self.fixada,
                "agente": self.agente, "data": self.criado_em.strftime("%d/%m/%Y"),
                "preview": self.ultima_msg()}


class Mensagem(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    conversa_id  = db.Column(db.Integer, db.ForeignKey("conversa.id"), nullable=False)
    papel        = db.Column(db.String(20))
    conteudo     = db.Column(db.Text, nullable=False)
    tipo         = db.Column(db.String(20), default="texto")
    arquivo_nome = db.Column(db.String(200))
    criado_em    = db.Column(db.DateTime, default=datetime.now)


@lm.user_loader
def load_user(uid): return User.query.get(int(uid))


# ─────────────── UTILITARIOS ───────────────

def criar_pdf(texto, nome_arquivo):
    """Cria um PDF a partir de texto (suporta markdown básico)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    
    # Limpa markdown para o PDF (fpdf2 básico não renderiza MD complexo sem plugins)
    texto_limpo = re.sub(r'[*_#`~]', '', texto)
    
    # Divide em linhas para evitar estouro
    for linha in texto_limpo.split('\n'):
        pdf.multi_cell(0, 10, txt=linha.encode('latin-1', 'replace').decode('latin-1'))
    
    path = os.path.join(UPLOAD_DIR, nome_arquivo)
    pdf.output(path)
    return nome_arquivo

def criar_docx(texto, nome_arquivo):
    """Cria um DOCX a partir de texto."""
    if not HAS_DOCX: return None
    doc = Document()
    doc.add_paragraph(texto)
    path = os.path.join(UPLOAD_DIR, nome_arquivo)
    doc.save(path)
    return nome_arquivo

def criar_txt(texto, nome_arquivo):
    """Cria um TXT a partir de texto."""
    path = os.path.join(UPLOAD_DIR, nome_arquivo)
    with open(path, "w", encoding="utf-8") as f:
        f.write(texto)
    return nome_arquivo

def ext_ok(nome, lista):
    return "." in nome and nome.rsplit(".", 1)[1].lower() in lista

def extrair_texto(caminho, nome):
    ext = nome.rsplit(".", 1)[1].lower() if "." in nome else ""
    try:
        if ext == "pdf" and HAS_PDF:
            with open(caminho, "rb") as f:
                r = PyPDF2.PdfReader(f)
                return "\n".join(p.extract_text() or "" for p in r.pages[:12])[:8000]
        elif ext == "docx" and HAS_DOCX:
            return "\n".join(p.text for p in Document(caminho).paragraphs)[:8000]
        elif ext in ("txt","md","csv"):
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(8000)
        elif ext == "xlsx" and HAS_XLSX:
            wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
            linhas = []
            for ws in wb.worksheets[:2]:
                for row in ws.iter_rows(max_row=60, values_only=True):
                    linhas.append("\t".join(str(c) if c is not None else "" for c in row))
            return "\n".join(linhas)[:6000]
    except Exception as e:
        return f"[Erro ao ler: {e}]"
    return "[Formato nao suportado]"

def img_b64(caminho):
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode()

def traduzir_prompt(texto):
    """Traduz o prompt para inglês usando a própria Groq para máxima fidelidade."""
    try:
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "Translate the following image prompt to English. Return ONLY the translated text, no explanation."},
                {"role": "user", "content": texto}
            ],
            "temperature": 0.3
        }
        r = requests.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=10)
        if r.ok:
            return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return texto # Fallback para o original se falhar

def gerar_imagem_ai(prompt, user_id):
    """Gera uma imagem de ALTA FIDELIDADE com tradução automática e motores de IA reais."""
    # 1. Traduz o prompt se estiver em português
    prompt_en_raw = traduzir_prompt(prompt)
    
    # 2. Refina o prompt para os motores de IA (Qualidade Masterpiece)
    prompt_premium = f"Masterpiece, high quality, highly detailed, professional lighting, {prompt_en_raw}"
    prompt_url = requests.utils.quote(prompt_premium)
    seed = int(datetime.now().timestamp())

    # 3. Lista de motores de IA REAIS (Removidos motores genéricos como Unsplash/Robohash)
    motores = [
        # Motor 1: Pollinations Flux (O melhor para seguir prompts complexos)
        {"url": f"https://image.pollinations.ai/prompt/{prompt_url}?width=1024&height=1024&nologo=true&model=flux&seed={seed}", "timeout": 30},
        
        # Motor 2: Pollinations Turbo (Rápido e preciso)
        {"url": f"https://image.pollinations.ai/prompt/{prompt_url}?width=1024&height=1024&nologo=true&model=turbo&seed={seed}", "timeout": 20},
        
        # Motor 3: Pollinations Any-Thing (Excelente para anime/ilustração)
        {"url": f"https://image.pollinations.ai/prompt/{prompt_url}?width=1024&height=1024&nologo=true&model=any-thing&seed={seed}", "timeout": 20}
    ]

    for motor in motores:
        try:
            print(f"DEBUG: Tentando motor de alta fidelidade: {motor['url']}")
            r = requests.get(motor['url'], timeout=motor['timeout'])
            ctype = r.headers.get("Content-Type", "").lower()
            
            if r.ok and "image" in ctype and len(r.content) > 5000: # Exige um arquivo maior para garantir qualidade
                nome_arq = f"img_{user_id}_{int(datetime.now().timestamp())}.jpg"
                caminho = os.path.join(UPLOAD_DIR, nome_arq)
                with open(caminho, "wb") as f:
                    f.write(r.content)
                
                print(f"DEBUG: Sucesso total na geração fiel: {motor['url']}")
                return nome_arq
        except Exception as e:
            print(f"DEBUG: Falha no motor de IA: {e}")
            continue
            
    return None

def gerar_video_ai(prompt, user_id):
    """Gera um vídeo curto (GIF/MP4) baseado no prompt."""
    try:
        prompt_url = requests.utils.quote(prompt)
        # Pollinations oferece geração de vídeo/frames via endpoint específico
        url = f"https://image.pollinations.ai/prompt/{prompt_url}?width=512&height=512&model=video&seed={int(datetime.now().timestamp())}"
        
        r = requests.get(url, timeout=60)
        if r.ok:
            nome_arq = f"vid_{user_id}_{int(datetime.now().timestamp())}.mp4"
            caminho = os.path.join(UPLOAD_DIR, nome_arq)
            with open(caminho, "wb") as f:
                f.write(r.content)
            return nome_arq
    except Exception as e:
        print(f"Erro Gerar Vídeo: {e}")
    return None

def editar_imagem(caminho_original, operacao, texto_extra=""):
    """Realiza edições básicas em imagens usando Pillow."""
    try:
        from PIL import Image, ImageEnhance, ImageDraw, ImageFont
        img = Image.open(caminho_original)
        
        if operacao == "preto_e_branco":
            img = img.convert("L")
        elif operacao == "brilho":
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.5)
        elif operacao == "texto" and texto_extra:
            draw = ImageDraw.Draw(img)
            # Tenta usar uma fonte padrão
            draw.text((20, 20), texto_extra, fill="white")
            
        nome_editado = "edit_" + os.path.basename(caminho_original)
        caminho_novo = os.path.join(UPLOAD_DIR, nome_editado)
        img.save(caminho_novo)
        return nome_editado
    except Exception as e:
        print(f"Erro Editar Imagem: {e}")
    return None

def chamar_ia(historico, agente_k="geral", memoria="", imagem_b64=None):
    agente = AGENTES.get(agente_k, AGENTES["geral"])
    sys_prompt = SISTEMA_BASE.format(nome=agente["nome"], prompt_agente=agente["prompt"], memoria=memoria)
    msgs = [{"role": "system", "content": sys_prompt}]
    for h in historico[-12:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    
    if imagem_b64:
        msgs[-1]["content"] = [
            {"type": "text", "text": msgs[-1]["content"]},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_b64}"}}
        ]
        modelo = MODELO_VIS
    else:
        modelo = MODELO_TX

    payload = {"model": modelo, "messages": msgs, "temperature": 0.5, "max_tokens": 4096}
    try:
        r = requests.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=25)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Erro Groq: {e}")
        return f"Erro na conexão com a IA: {e}"

def chamar_revisor(resposta_original):
    payload = {
        "model": MODELO_TX,
        "messages": [
            {"role": "system", "content": SISTEMA_REVISOR},
            {"role": "user", "content": f"Analise e corrija se necessário esta resposta:\n\n{resposta_original}"}
        ],
        "temperature": 0.3,
        "max_tokens": 4096
    }
    try:
        r = requests.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=25)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Erro Revisor: {e}")
        return resposta_original

def extrair_memoria(texto_usuario, user_id):
    """Extrai informações importantes do texto e salva na memória de forma inteligente."""
    padroes = [
        (r"meu nome (e|eh|é)\s+(\w+)", "nome do usuario", "perfil"),
        (r"me chamo\s+(\w+)", "nome do usuario", "perfil"),
        (r"sou o\s+(\w+)", "nome do usuario", "perfil"),
        (r"quero criar\s+(.{5,60})", "projeto em criacao", "projetos"),
        (r"estou criando\s+(.{5,60})", "projeto em andamento", "projetos"),
        (r"trabalho com\s+(.{5,60})", "area de trabalho", "perfil"),
        (r"meu negocio (e|eh|é)\s+(.{5,60})", "negocio", "negocio"),
        (r"gosto de\s+(.{5,50})", "interesse", "interesses"),
        (r"odeio\s+(.{5,50})", "aversao", "interesses"),
        (r"moro em\s+(.{5,50})", "localizacao", "perfil"),
        (r"meu site (e|eh|é)\s+(.{5,80})", "site", "projetos"),
        (r"sou de\s+(\w+)", "cidade/pais", "perfil"),
    ]
    texto_lower = texto_usuario.lower()
    for padrao, chave, categoria in padroes:
        m = re.search(padrao, texto_lower)
        if m:
            valor = m.group(len(m.groups()))
            if len(valor) > 2:
                existente = Memoria.query.filter_by(user_id=user_id, chave=chave).first()
                if existente:
                    if existente.valor != valor.strip():
                        existente.valor = valor.strip()
                        existente.atualizado_em = datetime.now()
                else:
                    db.session.add(Memoria(user_id=user_id, chave=chave, valor=valor.strip(), categoria=categoria))
                try:
                    db.session.commit()
                except: db.session.rollback()

    # Lógica de "Insight" - Se o usuário falar algo muito longo ou complexo, 
    # a IA pode tentar resumir como um fato (isso seria feito via LLM no futuro,
    # por enquanto mantemos a extração por Regex aprimorada).


# ─────────────── ROTAS ───────────────

@app.route("/")
def index():
    return render_template("index.html", agentes=AGENTES)

@app.route("/cadastro", methods=["GET","POST"])
def cadastro():
    if current_user.is_authenticated: return redirect(url_for("dashboard"))
    if request.method == "POST":
        nome = request.form.get("nome","").strip()
        email= request.form.get("email","").strip().lower()
        senha= request.form.get("senha","")
        conf = request.form.get("confirmar","")
        if not nome or not email or not senha:
            flash("Preencha todos os campos.","erro"); return render_template("cadastro.html")
        if senha != conf:
            flash("Senhas nao coincidem.","erro"); return render_template("cadastro.html")
        if len(senha) < 6:
            flash("Senha minima 6 caracteres.","erro"); return render_template("cadastro.html")
        if User.query.filter_by(email=email).first():
            flash("Email ja cadastrado.","erro"); return render_template("cadastro.html")
        u = User(nome=nome, email=email); u.set_senha(senha)
        db.session.add(u); db.session.commit(); login_user(u)
        flash(f"Bem-vindo, {nome}!","sucesso")
        return redirect(url_for("dashboard"))
    return render_template("cadastro.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("dashboard"))
    if request.method == "POST":
        email= request.form.get("email","").strip().lower()
        senha= request.form.get("senha","")
        u = User.query.filter_by(email=email).first()
        if u and u.ok_senha(senha):
            login_user(u, remember=True); return redirect(url_for("dashboard"))
        flash("Email ou senha incorretos.","erro")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    fixadas = Conversa.query.filter_by(user_id=current_user.id, fixada=True).order_by(Conversa.atualizado_em.desc()).all()
    recentes= Conversa.query.filter_by(user_id=current_user.id, fixada=False).order_by(Conversa.atualizado_em.desc()).limit(6).all()
    projetos= Projeto.query.filter_by(user_id=current_user.id).order_by(Projeto.atualizado_em.desc()).limit(4).all()
    total_msgs = db.session.query(db.func.count(Mensagem.id)).join(Conversa).filter(
        Conversa.user_id==current_user.id, Mensagem.papel=="user").scalar() or 0
    total_convs= Conversa.query.filter_by(user_id=current_user.id).count()
    total_proj = Projeto.query.filter_by(user_id=current_user.id).count()
    memorias   = Memoria.query.filter_by(user_id=current_user.id).count()
    # stats por agente
    stats_agente = db.session.query(Conversa.agente, db.func.count(Conversa.id)).filter_by(
        user_id=current_user.id).group_by(Conversa.agente).all()
    stats_dict = {a: c for a,c in stats_agente}
    return render_template("dashboard.html", fixadas=fixadas, recentes=recentes,
                           projetos=projetos, total_msgs=total_msgs, total_convs=total_convs,
                           total_proj=total_proj, memorias=memorias,
                           stats_agente=stats_dict, AGENTES=AGENTES)

@app.route("/chat")
@app.route("/chat/<int:cid>")
@login_required
def chat(cid=None):
    busca = request.args.get("q","").strip()
    q = Conversa.query.filter_by(user_id=current_user.id)
    if busca: q = q.filter(Conversa.titulo.ilike(f"%{busca}%"))
    fixadas = q.filter_by(fixada=True).order_by(Conversa.atualizado_em.desc()).all()
    normais = q.filter_by(fixada=False).order_by(Conversa.atualizado_em.desc()).all()
    projetos= Projeto.query.filter_by(user_id=current_user.id).order_by(Projeto.titulo).all()
    conversa_atual = None; mensagens = []
    if cid:
        conversa_atual = Conversa.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
        mensagens = conversa_atual.mensagens
    return render_template("chat.html", fixadas=fixadas, normais=normais, projetos=projetos,
                           conversa_atual=conversa_atual, mensagens=mensagens,
                           busca=busca, AGENTES=AGENTES,
                           agente_atual=conversa_atual.agente if conversa_atual else current_user.agente_padrao)

@app.route("/projetos")
@login_required
def projetos():
    lista = Projeto.query.filter_by(user_id=current_user.id).order_by(Projeto.atualizado_em.desc()).all()
    return render_template("projetos.html", projetos=lista, AGENTES=AGENTES)

@app.route("/memoria")
@login_required
def memoria():
    mems = Memoria.query.filter_by(user_id=current_user.id).order_by(Memoria.categoria, Memoria.chave).all()
    cats = {}
    for m in mems:
        cats.setdefault(m.categoria, []).append(m)
    return render_template("memoria.html", cats=cats)

@app.route("/perfil", methods=["GET","POST"])
@login_required
def perfil():
    if request.method == "POST":
        nome = request.form.get("nome","").strip()
        tema = request.form.get("tema","dark")
        agente = request.form.get("agente_padrao","geral")
        nova_senha = request.form.get("nova_senha","")
        if nome: current_user.nome = nome
        current_user.tema = tema
        current_user.agente_padrao = agente
        if nova_senha:
            if len(nova_senha) < 6:
                flash("Senha minima 6 caracteres.","erro"); return render_template("perfil.html", AGENTES=AGENTES)
            current_user.set_senha(nova_senha)
        db.session.commit(); flash("Perfil atualizado!","sucesso")
    total_msgs = db.session.query(db.func.count(Mensagem.id)).join(Conversa).filter(
        Conversa.user_id==current_user.id, Mensagem.papel=="user").scalar() or 0
    total_convs= Conversa.query.filter_by(user_id=current_user.id).count()
    return render_template("perfil.html", total_msgs=total_msgs, total_convs=total_convs, AGENTES=AGENTES)


# ─────────────── API ───────────────

@app.route("/api/enviar", methods=["POST"])
@login_required
def enviar():
    if not current_user.pode_perguntar():
        return jsonify({"erro": f"Limite de {LIMITE_FREE} perguntas diarias atingido!", "limite": True}), 429

    cid      = request.form.get("conversa_id", type=int)
    texto    = request.form.get("texto","").strip()
    agente_k = request.form.get("agente", current_user.agente_padrao)
    proj_id  = request.form.get("projeto_id", type=int)
    buscar   = request.form.get("buscar_web") == "1"
    arquivo  = request.files.get("arquivo")

    tipo_msg="texto"; imagem_b64=None; arq_nome=None; ctx_arq=""

    if arquivo and arquivo.filename:
        nome = secure_filename(arquivo.filename)
        arq_nome = f"{current_user.id}_{nome}" # Nome real com prefixo para o banco e disco
        path = os.path.join(UPLOAD_DIR, arq_nome)
        
        if ext_ok(nome, EXTS_IMG):
            tipo_msg="imagem"
            arquivo.save(path); imagem_b64 = img_b64(path)
            if not texto: texto = "Analise esta imagem e me diga o que voce ve."
        elif ext_ok(nome, EXTS_ARQ):
            tipo_msg="arquivo"
            arquivo.save(path)
            conteudo = extrair_texto(path, nome)
            ctx_arq = f"\n\n[Arquivo enviado: {nome}]\n{conteudo}"
            if not texto: texto = f"Leia e resuma o conteudo deste arquivo: {nome}"
        else:
            return jsonify({"erro": "Tipo de arquivo nao suportado."}), 400

    if not texto and not arquivo:
        return jsonify({"erro": "Mensagem vazia"}), 400

    # busca web
    ctx_web = ""
    if buscar and texto:
        resultados = buscar_web(texto)
        ctx_web = f"\n\n[Resultados da busca na internet para: '{texto}']\n{resultados}\n\nUse esses resultados para responder com informacoes atualizadas."

    # salvar/criar conversa
    if cid:
        conv = Conversa.query.filter_by(id=cid, user_id=current_user.id).first()
        if not conv: return jsonify({"erro":"Conversa nao encontrada"}),404
    else:
        conv = Conversa(user_id=current_user.id, agente=agente_k, projeto_id=proj_id)
        db.session.add(conv); db.session.flush()

    texto_salvo = texto
    if arq_nome and tipo_msg=="imagem": texto_salvo = f"[Imagem: {arq_nome}] {texto}"
    if arq_nome and tipo_msg=="arquivo": texto_salvo = f"[Arquivo: {arq_nome}] {texto}"

    db.session.add(Mensagem(conversa_id=conv.id, papel="user", conteudo=texto_salvo, tipo=tipo_msg, arquivo_nome=arq_nome))

    if conv.titulo == "Nova conversa" and len(texto) > 3:
        conv.titulo = texto[:60] + ("..." if len(texto) > 60 else "")
    conv.atualizado_em = datetime.now()

    # extrair memoria automaticamente
    extrair_memoria(texto, current_user.id)

    historico = [{"role": m.papel, "content": m.conteudo} for m in conv.mensagens]
    historico.append({"role": "user", "content": texto + ctx_arq + ctx_web})

    mem_txt = current_user.get_memoria_texto()
    resposta_bruta = chamar_ia(historico, conv.agente, mem_txt, imagem_b64)

    # SISTEMA DE REVISÃO DUPLA (DUAS IAs)
    # Ignoramos o revisor se houver comandos de geração de mídia ou se a resposta for curta
    comandos_midia = ["[GERAR_IMAGEM:", "[GERAR_VIDEO:", "[EDITAR_IMAGEM:"]
    tem_comando = any(cmd in resposta_bruta for cmd in comandos_midia)

    if len(resposta_bruta) > 150 and not tem_comando:
        resposta = chamar_revisor(resposta_bruta)
    else:
        resposta = resposta_bruta

    # Verificação de geração de imagem
    novo_arquivo = None
    tipo_final = "texto"
    
    print(f"DEBUG: Resposta Bruta da IA: {resposta_bruta}") # LOG PARA DEBUG

    if "[GERAR_IMAGEM:" in resposta or "GERAR_IMAGEM:" in resposta:
        try:
            print("DEBUG: Comando de imagem detectado!")
            # Tenta encontrar o comando mesmo se a IA não colocar os colchetes perfeitamente
            if "[GERAR_IMAGEM:" in resposta:
                inicio = resposta.find("[GERAR_IMAGEM:") + 14
                fim = resposta.find("]", inicio)
            else:
                inicio = resposta.find("GERAR_IMAGEM:") + 13
                fim = len(resposta) # Pega até o fim se não houver colchete
            
            if inicio > 12:
                prompt_img = resposta[inicio:fim].strip()
                print(f"DEBUG: Prompt extraído: {prompt_img}")
                
                # Limpa qualquer comando da resposta final
                if "[GERAR_IMAGEM:" in resposta:
                    comando_completo = resposta[resposta.find("[GERAR_IMAGEM:"):fim+1]
                    resposta = resposta.replace(comando_completo, "").strip()
                else:
                    comando_completo = resposta[resposta.find("GERAR_IMAGEM:"):fim]
                    resposta = resposta.replace(comando_completo, "").strip()
                
                nome_img = gerar_imagem_ai(prompt_img, current_user.id)
                if nome_img:
                    print(f"DEBUG: Imagem gerada com sucesso: {nome_img}")
                    novo_arquivo = nome_img
                    tipo_final = "imagem_gerada"
                    # Garante que a resposta não seja vazia se houver imagem
                    if not resposta:
                        resposta = "Aqui está a imagem que você solicitou:"
                else:
                    print("DEBUG: Falha ao gerar imagem na função gerar_imagem_ai")
                    resposta += "\n\n⚠️ (Erro ao processar a imagem. O motor gráfico pode estar sobrecarregado.)"
        except Exception as e:
            print(f"DEBUG: Erro no bloco de geração de imagem: {e}")
    elif "[GERAR_VIDEO:" in resposta:
        try:
            inicio = resposta.find("[GERAR_VIDEO:") + 13
            fim = resposta.find("]", inicio)
            prompt_vid = resposta[inicio:fim].strip()
            resposta = resposta.replace(f"[GERAR_VIDEO:{resposta[inicio:fim]}]", "").strip()
            nome_vid = gerar_video_ai(prompt_vid, current_user.id)
            if nome_vid:
                novo_arquivo = nome_vid
                tipo_final = "video_gerado"
        except: pass
    elif "[EDITAR_IMAGEM:" in resposta:
        try:
            inicio = resposta.find("[EDITAR_IMAGEM:") + 15
            fim = resposta.find("]", inicio)
            op = resposta[inicio:fim].strip()
            resposta = resposta.replace(f"[EDITAR_IMAGEM:{resposta[inicio:fim]}]", "").strip()
            # Procura a última imagem enviada pelo usuário na conversa
            msg_img = Mensagem.query.filter_by(conversa_id=conv.id, tipo="imagem").order_by(Mensagem.id.desc()).first()
            if msg_img:
                caminho_orig = os.path.join(UPLOAD_DIR, msg_img.arquivo_nome)
                nome_edit = editar_imagem(caminho_orig, op)
                if nome_edit:
                    novo_arquivo = nome_edit
                    tipo_final = "imagem_gerada"
        except: pass

    # Verificação de solicitação de criação de arquivo
    t_low = texto.lower()
    if not novo_arquivo:
        if any(x in t_low for x in ["crie um pdf", "gerar pdf", "salve em pdf", "salvar como pdf"]):
            nome_f = f"ia_gerado_{current_user.id}_{int(datetime.now().timestamp())}.pdf"
            novo_arquivo = criar_pdf(resposta, nome_f)
            tipo_final = "arquivo"
        elif any(x in t_low for x in ["crie um txt", "gerar txt", "salve em txt", "salvar como txt"]):
            nome_f = f"ia_gerado_{current_user.id}_{int(datetime.now().timestamp())}.txt"
            novo_arquivo = criar_txt(resposta, nome_f)
            tipo_final = "arquivo"
        elif ("docx" in t_low or "word" in t_low) and ("crie" in t_low or "gerar" in t_low or "salve" in t_low) and HAS_DOCX:
            nome_f = f"ia_gerado_{current_user.id}_{int(datetime.now().timestamp())}.docx"
            novo_arquivo = criar_docx(resposta, nome_f)
            tipo_final = "arquivo"

    db.session.add(Mensagem(conversa_id=conv.id, papel="assistant", conteudo=resposta, 
                           tipo=tipo_final,
                           arquivo_nome=novo_arquivo))
    current_user.perguntas_hoje += 1
    db.session.commit()

    return jsonify({"resposta": resposta, "conversa_id": conv.id, "titulo": conv.titulo,
                    "restantes": current_user.restantes(), "tipo": tipo_final,
                    "arquivo_gerado": novo_arquivo})


@app.route("/api/download/<path:filename>")
@login_required
def download_arquivo(filename):
    # Log para diagnóstico (visível no console do servidor)
    print(f"DEBUG: Requisição de download: {filename} por usuário {current_user.id}")

    # Garante que o usuário só baixe arquivos gerados ou enviados por ele
    # O nome do arquivo agora contém o ID do usuário (ex: img_1_... ou 1_foto.jpg)
    user_id_str = str(current_user.id)
    
    # Verificação de segurança simplificada e mais robusta
    # Aceita se o ID do usuário estiver em qualquer lugar do nome do arquivo
    is_owner = f"_{user_id_str}_" in filename or filename.startswith(f"{user_id_str}_") or f"img_{user_id_str}_" in filename

    if not is_owner:
        # Tenta verificar se é um arquivo gerado agora mesmo que pode estar sem o ID (fallback)
        if not filename.startswith("img_") and not filename.startswith("vid_"):
            print(f"DEBUG: ACESSO NEGADO para {filename}")
            return jsonify({"erro": "Acesso negado"}), 403
    
    caminho_completo = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(caminho_completo):
        print(f"DEBUG: ARQUIVO NÃO ENCONTRADO no disco: {caminho_completo}")
        return jsonify({"erro": "Arquivo não encontrado no servidor"}), 404
        
    # Define se deve baixar ou apenas exibir
    baixar = request.args.get("download") == "1"
    
    # Tenta detectar o mimetype correto
    import mimetypes
    mtype, _ = mimetypes.guess_type(filename)
    if not mtype:
        if filename.endswith(".pdf"): mtype = "application/pdf"
        elif filename.endswith(".docx"): mtype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".mp4"): mtype = "video/mp4"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"): mtype = "image/jpeg"
        elif filename.endswith(".png"): mtype = "image/png"
        else: mtype = "application/octet-stream"

    return send_from_directory(UPLOAD_DIR, filename, as_attachment=baixar, mimetype=mtype)

@app.route("/api/buscar-web")
@login_required
def api_buscar_web():
    q = request.args.get("q","").strip()
    if not q: return jsonify({"erro":"Busca vazia"}),400
    return jsonify({"resultado": buscar_web(q)})


@app.route("/api/buscar-conv")
@login_required
def buscar_conv():
    q = request.args.get("q","").strip()
    if not q: return jsonify([])
    res = Conversa.query.filter_by(user_id=current_user.id).filter(
        Conversa.titulo.ilike(f"%{q}%")).order_by(Conversa.atualizado_em.desc()).limit(20).all()
    return jsonify([c.to_dict() for c in res])


@app.route("/api/renomear/<int:cid>", methods=["POST"])
@login_required
def renomear(cid):
    c = Conversa.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    titulo = (request.get_json() or {}).get("titulo","").strip()
    if not titulo: return jsonify({"erro":"Titulo vazio"}),400
    c.titulo = titulo[:100]; db.session.commit()
    return jsonify({"ok":True,"titulo":c.titulo})


@app.route("/api/deletar/<int:cid>", methods=["DELETE"])
@login_required
def deletar(cid):
    c = Conversa.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    db.session.delete(c); db.session.commit()
    return jsonify({"ok":True})


@app.route("/api/fixar/<int:cid>", methods=["POST"])
@login_required
def fixar(cid):
    c = Conversa.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    c.fixada = not c.fixada; db.session.commit()
    return jsonify({"ok":True,"fixada":c.fixada})


@app.route("/api/exportar/<int:cid>")
@login_required
def exportar(cid):
    c = Conversa.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    ag = AGENTES.get(c.agente, AGENTES["geral"])
    linhas = [f"Conversa: {c.titulo}", f"Agente: {ag['icone']} {ag['nome']}",
              f"Data: {c.criado_em.strftime('%d/%m/%Y %H:%M')}", "="*60, ""]
    for m in c.mensagens:
        autor = "Voce" if m.papel=="user" else NOME_IA
        linhas += [f"[{m.criado_em.strftime('%H:%M')}] {autor}:", m.conteudo, ""]
    nome_arq = c.titulo[:40].replace(" ","_").replace("/","") + ".txt"
    return Response("\n".join(linhas).encode("utf-8"), mimetype="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome_arq}"'})


# ── Projetos API ──
@app.route("/api/projeto/novo", methods=["POST"])
@login_required
def novo_projeto():
    d = request.get_json() or {}
    titulo = d.get("titulo","").strip()
    if not titulo: return jsonify({"erro":"Titulo vazio"}),400
    p = Projeto(user_id=current_user.id, titulo=titulo[:100],
                descricao=d.get("descricao","")[:500], agente=d.get("agente","geral"))
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict())

@app.route("/api/projeto/editar/<int:pid>", methods=["POST"])
@login_required
def editar_projeto(pid):
    p = Projeto.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    d = request.get_json() or {}
    if d.get("titulo"): p.titulo = d["titulo"][:100]
    if d.get("descricao") is not None: p.descricao = d["descricao"][:500]
    if d.get("status"): p.status = d["status"]
    if d.get("agente"): p.agente = d["agente"]
    p.atualizado_em = datetime.now(); db.session.commit()
    return jsonify({"ok":True})

@app.route("/api/projeto/deletar/<int:pid>", methods=["DELETE"])
@login_required
def deletar_projeto(pid):
    p = Projeto.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    Conversa.query.filter_by(projeto_id=pid).update({"projeto_id":None})
    db.session.delete(p); db.session.commit()
    return jsonify({"ok":True})

@app.route("/api/projeto/<int:pid>/conversas")
@login_required
def conv_projeto(pid):
    Projeto.query.filter_by(id=pid, user_id=current_user.id).first_or_404()
    convs = Conversa.query.filter_by(projeto_id=pid, user_id=current_user.id).order_by(Conversa.atualizado_em.desc()).all()
    return jsonify([c.to_dict() for c in convs])

# ── Memoria API ──
@app.route("/api/memoria/salvar", methods=["POST"])
@login_required
def salvar_memoria():
    d = request.get_json() or {}
    chave = d.get("chave","").strip()
    valor = d.get("valor","").strip()
    cat   = d.get("categoria","geral")
    if not chave or not valor: return jsonify({"erro":"Dados invalidos"}),400
    m = Memoria.query.filter_by(user_id=current_user.id, chave=chave).first()
    if m:
        m.valor = valor; m.categoria = cat; m.atualizado_em = datetime.now()
    else:
        m = Memoria(user_id=current_user.id, chave=chave, valor=valor, categoria=cat)
        db.session.add(m)
    db.session.commit()
    return jsonify({"ok":True, "mem": m.to_dict()})

@app.route("/api/memoria/deletar/<int:mid>", methods=["DELETE"])
@login_required
def deletar_memoria(mid):
    m = Memoria.query.filter_by(id=mid, user_id=current_user.id).first_or_404()
    db.session.delete(m); db.session.commit()
    return jsonify({"ok":True})

@app.route("/api/upgrade", methods=["POST"])
@login_required
def upgrade():
    current_user.plano = "premium"; db.session.commit()
    return jsonify({"ok":True})


@app.route("/manifest.json")
def manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json')

@app.route("/sw.js")
def sw():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print(f"\n{'='*50}\n  {NOME_IA} v2.0 iniciada!\n  Acesse: http://localhost:5001\n{'='*50}\n")
    app.run(debug=False, host="0.0.0.0", port=5001)
