/**
 * 智能点餐助手 — 前端交互逻辑
 *
 * 职责：管理聊天面板的显示/隐藏，发送/接收消息，渲染消息气泡。
 * 原生 JS 实现，无框架依赖。
 */
(function () {
  "use strict";

  // ---- DOM 引用 ----
  var toggleBtn = document.getElementById("assistant-toggle");
  var panel = document.getElementById("assistant-panel");
  var closeBtn = document.getElementById("assistant-close");
  var messagesEl = document.getElementById("assistant-messages");
  var inputEl = document.getElementById("assistant-input");
  var sendBtn = document.getElementById("assistant-send");

  // ---- 状态 ----
  var isLoading = false;

  // ---- 工具函数 ----
  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(text, role) {
    var div = document.createElement("div");
    div.className = "assistant-msg assistant-msg-" + (role === "user" ? "right" : "left");
    var inner = document.createElement("div");
    inner.className = "assistant-msg-content";
    inner.textContent = text;
    div.appendChild(inner);
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  // ---- 加载历史消息 ----
  function loadHistory() {
    fetch("/api/assistant/history")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.messages) {
          messagesEl.innerHTML = "";
          data.messages.forEach(function (m) {
            addMessage(m.content, m.role);
          });
        }
      })
      .catch(function () {
        // 静默失败，保留欢迎语
      });
  }

  // ---- 发送消息 ----
  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || isLoading) return;

    isLoading = true;
    sendBtn.disabled = true;
    sendBtn.textContent = "发送中...";

    addMessage(text, "user");
    inputEl.value = "";

    fetch("/api/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.reply) {
          addMessage(data.reply, "assistant");
        } else if (data.error) {
          addMessage("出错了：" + data.error, "assistant");
        }
      })
      .catch(function () {
        addMessage("网络错误，请稍后重试", "assistant");
      })
      .finally(function () {
        isLoading = false;
        sendBtn.disabled = false;
        sendBtn.textContent = "发送";
        inputEl.focus();
      });
  }

  // ---- 面板切换（记忆状态） ----
  function savePanelState(open) {
    try { sessionStorage.setItem("assistant_open", open ? "1" : "0"); } catch(e) {}
  }

  function togglePanel(show) {
    if (show === undefined) {
      panel.classList.toggle("hidden");
    } else if (show) {
      panel.classList.remove("hidden");
    } else {
      panel.classList.add("hidden");
    }

    var isOpen = !panel.classList.contains("hidden");
    savePanelState(isOpen);

    if (isOpen) {
      loadHistory();
      inputEl.focus();
    }
  }

  // 页面加载时恢复面板状态
  try {
    if (sessionStorage.getItem("assistant_open") === "1") {
      panel.classList.remove("hidden");
      loadHistory();
    }
  } catch(e) {}

  // ---- 事件绑定 ----
  toggleBtn.addEventListener("click", function () {
    togglePanel();
  });

  closeBtn.addEventListener("click", function () {
    togglePanel(false);
  });

  sendBtn.addEventListener("click", sendMessage);

  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // ---- 后厨通知监听 ----
  var tableIdEl = document.getElementById('table-id-data');
  if (tableIdEl) {
    var tableId = tableIdEl.getAttribute('data-table-id');
    if (tableId) {
      var eventSource = new EventSource('/api/kitchen/notifications/stream?table_id=' + tableId);

      // 通用通知处理：如果有 message，弹窗 + 写入聊天
      function handleKitchenEvent(eventType, eventData) {
        var message = eventData.message || (eventData.data && eventData.data.message);
        if (!message) return;

        // 弹窗通知
        showNotification(message);

        // 写入聊天窗口（如果聊天面板存在）
        var messagesEl = document.getElementById('assistant-messages');
        if (messagesEl) {
          var div = document.createElement('div');
          div.className = 'assistant-msg assistant-msg-left';
          var inner = document.createElement('div');
          inner.className = 'assistant-msg-content';
          inner.textContent = '🔔 ' + message;
          div.appendChild(inner);
          messagesEl.appendChild(div);
          messagesEl.scrollTop = messagesEl.scrollHeight;
        }
      }

      // 监听所有 kitchen 事件
      eventSource.addEventListener('items_done', function(e) {
        try { handleKitchenEvent('items_done', JSON.parse(e.data)); } catch(err) {}
      });
      eventSource.addEventListener('item_updated', function(e) {
        try { handleKitchenEvent('item_updated', JSON.parse(e.data)); } catch(err) {}
      });
      eventSource.addEventListener('item_voided', function(e) {
        try { handleKitchenEvent('item_voided', JSON.parse(e.data)); } catch(err) {}
      });
      // 兼容旧事件名
      eventSource.addEventListener('dish-ready', function(e) {
        try { handleKitchenEvent('dish-ready', JSON.parse(e.data)); } catch(err) {}
      });

      function showNotification(text) {
        var el = document.createElement('div');
        el.className = 'dish-notification';
        el.innerHTML = '<span>' + text + '</span><button onclick="this.parentElement.remove()" style="background:none;border:none;color:#fff;font-size:20px;margin-left:12px;cursor:pointer">&times;</button>';
        document.body.appendChild(el);
        el.addEventListener('click', function() { this.remove(); });
      }
    }
  }
})();
