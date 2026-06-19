(function () {
  const fab = document.getElementById('chat-fab');
  const panel = document.getElementById('chat-panel');
  const closeBtn = document.getElementById('chat-close');
  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-text');
  const suggestions = document.getElementById('chat-suggestions');
  const heroBtn = document.getElementById('open-chat-hero');

  let greeted = false;

  function openChat() {
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    fab.classList.add('hidden');
    if (!greeted) {
      greeted = true;
      setTimeout(() => {
        addMessage(`Hi! 👋 Welcome to ${SHOP_NAME}. Ask me about shipping, delivery times, returns, or any product — I'm here to help.`, 'bot');
      }, 300);
    }
    setTimeout(() => input.focus(), 250);
  }

  function closeChat() {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    fab.classList.remove('hidden');
  }

  fab.addEventListener('click', openChat);
  closeBtn.addEventListener('click', closeChat);
  if (heroBtn) heroBtn.addEventListener('click', openChat);

  // Escape closes the panel
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && panel.classList.contains('open')) closeChat();
  });

  // Convert URLs and phone handoffs into clickable links, safely escaped.
  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function linkify(text) {
    let safe = escapeHtml(text);
    safe = safe.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    return safe;
  }

  function addMessage(text, who) {
    const div = document.createElement('div');
    div.className = 'msg ' + who;
    div.innerHTML = linkify(text);
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'msg bot typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  // If the bot couldn't answer, offer a WhatsApp handoff button.
  function maybeOfferHandoff(reply) {
    if (/not sure|connect you|whatsapp/i.test(reply)) {
      const wrap = document.createElement('div');
      wrap.className = 'msg bot';
      wrap.style.background = 'transparent';
      wrap.style.border = 'none';
      wrap.style.padding = '0';
      wrap.innerHTML = `<a class="btn btn-solid btn-sm" href="https://wa.me/${SHOP_WA}" target="_blank" rel="noopener" style="text-decoration:none;color:#fff;">Chat with us on WhatsApp</a>`;
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
    }
  }

  async function sendMessage(text) {
    addMessage(text, 'user');
    if (suggestions) suggestions.style.display = 'none';
    const typing = showTyping();
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      typing.remove();
      const reply = data.reply || "Sorry, something went wrong. Please try again.";
      addMessage(reply, 'bot');
      maybeOfferHandoff(reply);
    } catch (err) {
      typing.remove();
      addMessage("I couldn't reach the server. Please check your connection and try again.", 'bot');
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    sendMessage(text);
  });

  if (suggestions) {
    suggestions.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', () => sendMessage(btn.textContent));
    });
  }
})();
