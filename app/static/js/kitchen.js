// kitchen.js - 后厨助手前端交互
(function() {
  'use strict';

  var toggleBtn = document.getElementById('kitchen-toggle');
  var panel = document.getElementById('kitchen-panel');
  var closeBtn = document.getElementById('kitchen-close');
  var messagesEl = document.getElementById('kitchen-messages');
  var inputEl = document.getElementById('kitchen-input');
  var sendBtn = document.getElementById('kitchen-send');

  var isLoading = false;

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(text, role) {
    var div = document.createElement('div');
    div.className = 'kitchen-msg kitchen-msg-' + (role === 'user' ? 'right' : 'left');
    var inner = document.createElement('div');
    inner.className = 'kitchen-msg-content';
    inner.textContent = text;
    div.appendChild(inner);
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function loadHistory() {
    fetch('/api/kitchen/history')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.messages) {
          messagesEl.innerHTML = '';
          data.messages.forEach(function(m) {
            addMessage(m.content, m.role);
          });
        }
      })
      .catch(function() {});
  }

  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || isLoading) return;

    isLoading = true;
    sendBtn.disabled = true;
    sendBtn.textContent = '发送中...';

    addMessage(text, 'user');
    inputEl.value = '';

    fetch('/api/kitchen/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.reply) {
          addMessage(data.reply, 'assistant');
        } else if (data.error) {
          if (data.error === '请先登录') {
            window.location.href = '/admin/login';
            return;
          }
          addMessage('出错了：' + data.error, 'assistant');
        }
      })
      .catch(function() {
        addMessage('网络错误，请稍后重试', 'assistant');
      })
      .finally(function() {
        isLoading = false;
        sendBtn.disabled = false;
        sendBtn.textContent = '发送';
        inputEl.focus();
      });
  }

  toggleBtn.addEventListener('click', function() {
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
      loadHistory();
      inputEl.focus();
    }
  });

  closeBtn.addEventListener('click', function() {
    panel.classList.add('hidden');
  });

  sendBtn.addEventListener('click', sendMessage);

  inputEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  if (messagesEl.children.length === 0) {
    addMessage('你好！我是后厨助手"小厨"，可以帮你管理订单、更新菜品进度。试试说"查看概览"或"待做菜品"。', 'assistant');
  }
})();
