// ── Estado ──
let conversaId = typeof CONV_ATUAL_ID !== 'undefined' ? CONV_ATUAL_ID : null;
let arquivoSelecionado = null;
let ttsAtivo = false;
let reconhecendo = false;
let reconhecimento = null;
let ctxId = null, ctxFixada = false;

// ── INIT ──
window.onload = () => {
  const msgs = document.getElementById('chatMsgs');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
  initVoz();
  autoResize();
};

function autoResize() {
  const ta = document.getElementById('msgInput');
  if (!ta) return;
  ta.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  });
}

// ── CHAT ──
function handleEnter(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviarMensagem(); }
}

function usarSug(btn) {
  document.getElementById('msgInput').value = btn.textContent.replace(/^[^\w]+/, '');
  enviarMensagem();
}

function abrirConv(id) { window.location.href = '/chat/' + id; }

async function novaConversa() {
  conversaId = null;
  document.getElementById('chatTitulo').textContent = 'Nova conversa';
  document.getElementById('chatMsgs').innerHTML = `
    <div class="chat-welcome">
      <div class="welcome-icon">🧠</div>
      <h2>Nova conversa</h2>
      <p>O que voce quer perguntar?</p>
    </div>`;
  document.querySelectorAll('.hist-item').forEach(i => i.classList.remove('ativo'));
  document.getElementById('msgInput').focus();
  cancelarArquivo();
}

async function enviarMensagem() {
  const input = document.getElementById('msgInput');
  const texto = input.value.trim();
  if (!texto && !arquivoSelecionado) return;
  input.value = ''; input.style.height = 'auto';

  const msgs = document.getElementById('chatMsgs');
  document.getElementById('welcome')?.remove();
  document.querySelector('.chat-welcome')?.remove();

  const textoMostrar = arquivoSelecionado ? `${texto || 'Analise este arquivo'}` : texto;
  const tipoMostrar = arquivoSelecionado?.tipo || 'texto';
  adicionarMsg(textoMostrar, 'user', tipoMostrar, arquivoSelecionado?.nome);
  const typing = adicionarTyping();
  document.getElementById('btnEnviar').disabled = true;

  const fd = new FormData();
  if (texto) fd.append('texto', texto);
  if (conversaId) fd.append('conversa_id', conversaId);
  if (arquivoSelecionado) fd.append('arquivo', arquivoSelecionado.file);
  cancelarArquivo();

  try {
    const resp = await fetch('/api/enviar', { method: 'POST', body: fd });
    const data = await resp.json();
    typing.remove();
    if (resp.status === 429) {
      adicionarMsg('⚠️ ' + data.erro, 'ia');
    } else if (data.erro) {
      adicionarMsg('❌ ' + data.erro, 'ia');
    } else {
      const respTxt = data.arquivo_gerado ? 
        `${data.resposta}<br><br><a href="/api/download/${data.arquivo_gerado}" class="btn-download" target="_blank">📥 Baixar Arquivo Gerado</a>` : 
        data.resposta;
      
      adicionarMsg(respTxt, 'ia', 'texto', null, true);
      conversaId = data.conversa_id;
      document.getElementById('chatTitulo').textContent = data.titulo;
      atualizarHistItem(data.conversa_id, data.titulo, data.resposta);
      if (data.restantes !== null) {
        const el = document.getElementById('limiteTexto');
        if (el) el.textContent = data.restantes + ' restantes';
      }
      if (ttsAtivo) falarTextoStr(data.resposta);
    }
  } catch (e) {
    typing.remove();
    adicionarMsg('Erro de conexao. Verifique se o servidor esta rodando.', 'ia');
  }
  document.getElementById('btnEnviar').disabled = false;
  input.focus();
}

function adicionarMsg(texto, tipo, subtipo = 'texto', arquivoNome = null, comBtnFalar = false) {
  const msgs = document.getElementById('chatMsgs');
  const div = document.createElement('div');
  div.className = 'msg-wrap ' + tipo;
  const av = tipo === 'ia' ? '<div class="msg-av">🧠</div>' : '';
  const uav = tipo === 'user' ? `<div class="msg-av user-av">${USER_INICIAL}</div>` : '';
  let prefixo = '';
  if (subtipo === 'imagem') prefixo = '📷 ';
  else if (subtipo === 'arquivo') prefixo = '📁 ';
  const btnFalar = (comBtnFalar && tipo === 'ia') ?
    `<button class="btn-falar" onclick="falarTexto(this)" data-texto="${texto.replace(/"/g,'&quot;')}" title="Ouvir">🔊</button>` : '';
  div.innerHTML = av + `<div class="msg-balao">${prefixo}${texto.replace(/\n/g, '<br>')}${btnFalar}</div>` + uav;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function adicionarTyping() {
  const msgs = document.getElementById('chatMsgs');
  const div = document.createElement('div');
  div.className = 'msg-wrap ia';
  div.innerHTML = '<div class="msg-av">🧠</div><div class="msg-balao typing-dots"><span></span><span></span><span></span></div>';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function atualizarHistItem(id, titulo, preview) {
  let item = document.querySelector(`.hist-item[data-id="${id}"]`);
  if (item) {
    item.querySelector('.hi-titulo').textContent = titulo.substring(0, 38);
    item.querySelector('.hi-preview').textContent = preview.substring(0, 45);
  } else {
    const label = document.querySelector('.hist-label:last-of-type');
    if (!label) return;
    const div = document.createElement('div');
    div.className = 'hist-item ativo';
    div.setAttribute('data-id', id);
    div.onclick = () => abrirConv(id);
    const tituloSafe = titulo.replace(/'/g, "\\'").replace(/"/g, '\\"');
    div.innerHTML = `<div class="hi-main">
      <div class="hi-titulo">${titulo.substring(0,38)}</div>
      <div class="hi-preview">${preview.substring(0,45)}</div>
      <div class="hi-meta"><span>hoje</span></div>
    </div>
    <button class="hi-menu" onclick="abrirMenu(event,${id},'${tituloSafe}',false)">⋮</button>`;
    label.after(div);
    document.querySelectorAll('.hist-item').forEach(i => { if (parseInt(i.dataset.id) !== id) i.classList.remove('ativo'); });
  }
}

// ── ARQUIVO ──
function selecionarArquivo(input) {
  const file = input.files[0];
  if (!file) return;
  const nome = file.name;
  const ext = nome.split('.').pop().toLowerCase();
  const imagens = ['png','jpg','jpeg','gif','webp','bmp'];
  const tipo = imagens.includes(ext) ? 'imagem' : 'arquivo';
  arquivoSelecionado = { file, nome, tipo };
  const preview = document.getElementById('previewArquivo');
  const conteudo = document.getElementById('previewConteudo');
  if (tipo === 'imagem') {
    const reader = new FileReader();
    reader.onload = e => { conteudo.innerHTML = `<img src="${e.target.result}" style="max-height:120px;border-radius:8px"> <span>${nome}</span>`; };
    reader.readAsDataURL(file);
  } else {
    conteudo.innerHTML = `📁 <strong>${nome}</strong> <span style="color:var(--text2);font-size:12px">(${(file.size/1024).toFixed(0)} KB)</span>`;
  }
  preview.style.display = 'flex';
  input.value = '';
}

function cancelarArquivo() {
  arquivoSelecionado = null;
  document.getElementById('previewArquivo').style.display = 'none';
  document.getElementById('previewConteudo').innerHTML = '';
}

// ── BUSCA ──
let buscaTimer;
async function buscarConversas(q) {
  clearTimeout(buscaTimer);
  const btn = document.getElementById('btnLimpar');
  if (btn) btn.style.display = q ? 'flex' : 'none';
  const wrap = document.getElementById('buscaResultados');
  const lista = document.getElementById('listaBusca');
  if (!q) { wrap.style.display = 'none'; return; }
  buscaTimer = setTimeout(async () => {
    const r = await fetch('/api/buscar?q=' + encodeURIComponent(q));
    const data = await r.json();
    wrap.style.display = 'block';
    if (!data.length) { lista.innerHTML = '<div class="hist-vazio">Nenhum resultado.</div>'; return; }
    lista.innerHTML = data.map(c => `
      <div class="hist-item" onclick="abrirConv(${c.id})">
        <div class="hi-main">
          <div class="hi-titulo">${c.titulo.substring(0,38)}</div>
          <div class="hi-preview">${c.preview}</div>
          <div class="hi-meta"><span>${c.data}</span></div>
        </div>
      </div>`).join('');
  }, 300);
}

function limparBusca() {
  document.getElementById('buscaInput').value = '';
  buscarConversas('');
}

// ── MENU CONVERSA ──
function abrirMenu(e, id, titulo, fixada) {
  e.stopPropagation(); e.preventDefault();
  ctxId = id; ctxFixada = fixada;
  document.getElementById('ctxFixarLabel').textContent = fixada ? 'Desafixar' : 'Fixar';
  const menu = document.getElementById('ctxMenu');
  menu.style.display = 'block';
  menu.style.left = e.pageX + 'px';
  menu.style.top = e.pageY + 'px';
  setTimeout(() => document.addEventListener('click', () => { menu.style.display = 'none'; }, { once: true }), 10);
}

function ctxRenomear() {
  document.getElementById('ctxMenu').style.display = 'none';
  const el = document.querySelector(`.hist-item[data-id="${ctxId}"] .hi-titulo`);
  document.getElementById('renomearInput').value = el ? el.textContent : '';
  document.getElementById('modalRenomear').style.display = 'flex';
  document.getElementById('renomearInput').focus();
}

async function confirmarRenomear() {
  const titulo = document.getElementById('renomearInput').value.trim();
  if (!titulo) return;
  const r = await fetch(`/api/renomear/${ctxId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ titulo }) });
  const data = await r.json();
  document.querySelectorAll(`.hist-item[data-id="${ctxId}"] .hi-titulo`).forEach(el => el.textContent = data.titulo);
  if (conversaId == ctxId) document.getElementById('chatTitulo').textContent = data.titulo;
  fecharModal();
}

async function ctxFixar() {
  document.getElementById('ctxMenu').style.display = 'none';
  await fetch(`/api/fixar/${ctxId}`, { method: 'POST' });
  location.reload();
}

function ctxExportar() {
  document.getElementById('ctxMenu').style.display = 'none';
  window.location.href = `/api/exportar/${ctxId}`;
}

async function ctxDeletar() {
  document.getElementById('ctxMenu').style.display = 'none';
  if (!confirm('Excluir esta conversa?')) return;
  await fetch(`/api/deletar/${ctxId}`, { method: 'DELETE' });
  document.querySelectorAll(`.hist-item[data-id="${ctxId}"]`).forEach(el => el.remove());
  if (conversaId == ctxId) novaConversa();
}

function fecharModal() {
  document.getElementById('modalRenomear').style.display = 'none';
}
document.addEventListener('DOMContentLoaded', () => {
  const ri = document.getElementById('renomearInput');
  if (ri) ri.addEventListener('keydown', e => { if (e.key === 'Enter') confirmarRenomear(); });
});

// ── VOZ (STT - Speech to Text) ──
function initVoz() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;
  reconhecimento = new SpeechRecognition();
  reconhecimento.lang = 'pt-BR';
  reconhecimento.continuous = false;
  reconhecimento.interimResults = true;
  reconhecimento.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    document.getElementById('msgInput').value = transcript;
    document.getElementById('msgInput').style.height = 'auto';
    document.getElementById('msgInput').style.height = Math.min(document.getElementById('msgInput').scrollHeight, 150) + 'px';
  };
  reconhecimento.onend = () => {
    reconhecendo = false;
    const btn = document.getElementById('btnVoz');
    if (btn) { btn.classList.remove('gravando'); btn.title = 'Falar mensagem'; }
    const texto = document.getElementById('msgInput').value.trim();
    if (texto) setTimeout(() => enviarMensagem(), 300);
  };
  reconhecimento.onerror = (e) => {
    reconhecendo = false;
    const btn = document.getElementById('btnVoz');
    if (btn) btn.classList.remove('gravando');
    if (e.error !== 'no-speech') alert('Erro no microfone: ' + e.error);
  };
}

function toggleVoz() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('Seu navegador nao suporta reconhecimento de voz. Use Chrome ou Edge.');
    return;
  }
  const btn = document.getElementById('btnVoz');
  if (reconhecendo) {
    reconhecimento.stop();
    reconhecendo = false;
    btn.classList.remove('gravando');
  } else {
    reconhecimento.start();
    reconhecendo = true;
    btn.classList.add('gravando');
    btn.title = 'Gravando... clique para parar';
  }
}

// ── TTS (Text to Speech) ──
function toggleTTS() {
  ttsAtivo = !ttsAtivo;
  const btn = document.getElementById('btnTTS');
  if (btn) {
    btn.style.background = ttsAtivo ? 'rgba(79,142,247,0.2)' : '';
    btn.style.borderColor = ttsAtivo ? 'var(--accent)' : '';
    btn.title = ttsAtivo ? 'Voz ativada (clique para desativar)' : 'Ativar voz';
  }
  if (!ttsAtivo && window.speechSynthesis) window.speechSynthesis.cancel();
}

function falarTexto(btn) {
  const texto = btn.getAttribute('data-texto');
  falarTextoStr(texto);
}

function falarTextoStr(texto) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const texto_limpo = texto.replace(/[#*`_\[\]()]/g, ' ').substring(0, 2000);
  const utterance = new SpeechSynthesisUtterance(texto_limpo);
  utterance.lang = 'pt-BR';
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  const vozes = window.speechSynthesis.getVoices();
  const vozPT = vozes.find(v => v.lang.startsWith('pt'));
  if (vozPT) utterance.voice = vozPT;
  window.speechSynthesis.speak(utterance);
}

// Flash auto-hide
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(f => {
    f.style.transition = 'opacity .5s';
    f.style.opacity = '0';
    setTimeout(() => f.remove(), 500);
  });
}, 3500);
