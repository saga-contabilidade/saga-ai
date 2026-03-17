function confirmar(mensagem, callback) {
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,0.5);
    display:flex;align-items:center;justify-content:center;z-index:9999;
  `;

  overlay.innerHTML = `
    <div style="
      background:var(--surface);border:1px solid var(--border);
      border-radius:14px;padding:28px 32px;max-width:360px;width:90%;
      box-shadow:0 8px 32px rgba(0,0,0,0.4);
    ">
      <p style="color:var(--text);font-size:15px;margin-bottom:24px;line-height:1.5;">${mensagem}</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;">
        <button id="modal-cancelar" style="
          padding:8px 18px;border-radius:8px;border:1px solid var(--border);
          background:transparent;color:var(--text-muted);cursor:pointer;
          font-size:14px;font-family:inherit;transition:background .15s;
        ">Cancelar</button>
        <button id="modal-confirmar" style="
          padding:8px 18px;border-radius:8px;border:none;
          background:#C0392B;color:#fff;cursor:pointer;
          font-size:14px;font-weight:500;font-family:inherit;transition:background .15s;
        ">Excluir</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  document.getElementById('modal-cancelar').onclick = () => {
    document.body.removeChild(overlay);
  };
  document.getElementById('modal-confirmar').onclick = () => {
    document.body.removeChild(overlay);
    callback();
  };

  overlay.onclick = (e) => {
    if (e.target === overlay) document.body.removeChild(overlay);
  };
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function fillInput(text) {
  const el = document.getElementById('user-input');
  if (!el) return;
  el.value = text;
  el.focus();
  autoResize(el);
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function scrollBottom() {
  const msgs = document.getElementById('messages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function renderMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^\- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function addBubble(role, html, id) {
  const msgs = document.getElementById('messages');
  const welcome = msgs.querySelector('.welcome');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `msg ${role}`;
  if (id) div.id = id;
  const initial = role === 'user' ? (window.USER_INITIAL || 'U') : 'IR';
  div.innerHTML = `<div class="msg-avatar">${initial}</div><div class="msg-bubble">${html}</div>`;
  msgs.appendChild(div);
  scrollBottom();
  return div;
}

let isSending = false;

async function sendMessage() {
  if (isSending || typeof CONV_ID === 'undefined') return;
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text) return;

  isSending = true;
  document.getElementById('send-btn').disabled = true;
  input.value = '';
  input.style.height = 'auto';

  addBubble('user', escapeHtml(text).replace(/\n/g, '<br>'));

  const typingDiv = addBubble('assistant typing', '<div class="dots"><span></span><span></span><span></span></div>', 'typing-indicator');

  try {
    const res = await fetch(SEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ message: text }),
    });

    if (!res.ok) {
      const err = await res.json();
      typingDiv.remove();
      addBubble('assistant', err.error || 'Erro na requisição.');
      isSending = false;
      document.getElementById('send-btn').disabled = false;
      input.focus();
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let botBubble = null;
    let fullText = '';

    typingDiv.remove();
    botBubble = addBubble('assistant', '');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = JSON.parse(line.slice(6));
        if (data.text) {
          fullText += data.text;
          botBubble.querySelector('.msg-bubble').innerHTML = renderMarkdown(fullText);
          scrollBottom();
        }
        if (data.done && data.title) {
          document.getElementById('chat-title').textContent = data.title;
          const sidebarLink = document.querySelector('.sidebar-item.active .conv-title');
          if (sidebarLink) sidebarLink.textContent = data.title;
        }
        if (data.error) {
          botBubble.querySelector('.msg-bubble').textContent = 'Erro: ' + data.error;
        }
      }
    }
  } catch (err) {
    document.getElementById('typing-indicator')?.remove();
    addBubble('assistant', 'Erro ao conectar. Tente novamente.');
  }

  isSending = false;
  document.getElementById('send-btn').disabled = false;
  input.focus();
}

async function uploadPDF(input) {
  if (!input.files.length || typeof UPLOAD_URL === 'undefined') return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('document', file);

  const btn = document.querySelector('.btn-upload');
  btn.textContent = '⏳ Enviando…';

  try {
    const res = await fetch(UPLOAD_URL, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF },
      body: formData,
    });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }

    const bar = document.getElementById('doc-bar');
    bar.style.display = 'flex';
    const chip = document.createElement('div');
    chip.className = 'doc-chip';
    chip.id = `doc-${data.id}`;
    chip.innerHTML = `<span>📄 ${escapeHtml(data.name)}</span><button onclick="deleteDoc(${data.id})" title="Remover">×</button>`;
    bar.appendChild(chip);
  } catch (e) {
    alert('Erro ao enviar arquivo.');
  } finally {
    btn.innerHTML = '📎 Anexar PDF<input type="file" id="pdf-upload" accept=".pdf" style="display:none" onchange="uploadPDF(this)">';
    input.value = '';
  }
}

async function deleteDoc(id) {
  if (!confirm('Remover documento desta conversa?')) return;
  const res = await fetch(`/documento/${id}/deletar/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF },
  });
  if (res.ok) {
    document.getElementById(`doc-${id}`)?.remove();
    const bar = document.getElementById('doc-bar');
    if (bar && !bar.children.length) bar.style.display = 'none';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  scrollBottom();
  const input = document.getElementById('user-input');
  if (input) input.focus();

  document.querySelectorAll('.msg.assistant .msg-bubble').forEach(el => {
    const raw = el.innerHTML
      .replace(/<br>/gi, '\n')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"');
    el.innerHTML = renderMarkdown(raw);
  });
});