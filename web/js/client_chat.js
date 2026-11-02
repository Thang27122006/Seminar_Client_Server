/**
 * ClientChat - Xử lý Logic Phòng Chat Web Client.
 * Giao tiếp qua WebSocket theo đúng chuẩn giao thức Seminar:
 * JOIN, WELCOME, MSG, PRIVATE, ONLINE_LIST, SYSTEM, ERROR, QUIT.
 */

class ChatClientController {
  constructor() {
    this.ws = null;
    this.isConnected = false;
    this.clientId = null;
    this.username = '';
    this.userAvatar = '👨‍💻';
    this.activeTarget = 'ALL'; // 'ALL' hoặc tên người dùng cụ thể (Whisper)
    this.onlineUsers = [];
    this.unreadCount = 0;
    this.pingStartTime = 0;
    this.pingInterval = null;

    // Danh sách avatar mẫu
    this.presetAvatars = ['👨‍💻', '🚀', '⚡', '🐱', '🦊', '👾', '🤖', '🛡️'];

    // Danh sách emoji nhanh
    this.presetEmojis = [
      '😀', '😂', '🔥', '❤️', '🚀', '👍', 
      '🎉', '💡', '🔒', '💻', '🌐', '⚡',
      '😎', '👏', '✨', '👋', '👀', '💯'
    ];

    // Đọc mã phòng từ URL query string
    const urlParams = new URLSearchParams(window.location.search);
    this.roomCode = urlParams.get('code') || urlParams.get('room') || 'seminar-network-lab';

    this.initDOM();
    this.renderAvatarPicker();
    this.renderEmojiPicker();
    this.initRoomInfo();
  }

  initRoomInfo() {
    const displayEl = document.getElementById('displayRoomCode');
    if (displayEl) displayEl.textContent = this.roomCode;

    const linkHost = document.getElementById('linkHostStudio');
    if (linkHost) linkHost.href = `/admin?room=${encodeURIComponent(this.roomCode)}`;

    document.getElementById('btnCopyRoomCode')?.addEventListener('click', () => {
      navigator.clipboard.writeText(this.roomCode);
      window.app?.showToast(`Đã sao chép mã phòng: ${this.roomCode}`, 'success');
    });

    // Điền sẵn nickname từ tài khoản đã đăng nhập
    const user = window.authManager?.getUser();
    if (user && this.inputUsername) {
      this.inputUsername.value = user.fullname || user.username;
    }
  }

  initDOM() {
    // Màn hình Đăng Nhập
    this.loginOverlay = document.getElementById('chatLoginOverlay');
    this.formJoin = document.getElementById('formJoinChat');
    this.inputServerUrl = document.getElementById('inputServerUrl');
    this.inputUsername = document.getElementById('inputUsername');
    this.avatarPickerGrid = document.getElementById('avatarPickerGrid');
    this.btnRandomName = document.getElementById('btnRandomName');
    this.loginFeedback = document.getElementById('loginFeedback');
    this.btnJoinSubmit = document.getElementById('btnJoinSubmit');

    // Header badges
    this.headerUserBadge = document.getElementById('headerUserBadge');
    this.headerAvatar = document.getElementById('headerAvatar');
    this.headerUserName = document.getElementById('headerUserName');
    this.headerUserId = document.getElementById('headerUserId');
    this.btnHeaderDisconnect = document.getElementById('btnHeaderDisconnect');
    this.pingValueEl = document.getElementById('pingValue');
    this.statusPulseDot = document.getElementById('statusPulseDot');
    this.connectionStatusLabel = document.getElementById('connectionStatusLabel');

    // Sidebar & Channels
    this.channelPublic = document.getElementById('channelPublic');
    this.onlineTotalBadge = document.getElementById('onlineTotalBadge');
    this.dmConversationsBox = document.getElementById('dmConversationsBox');
    this.dmList = document.getElementById('dmList');
    this.userCountSpan = document.getElementById('userCountSpan');
    this.inputSearchUser = document.getElementById('inputSearchUser');
    this.onlineUsersContainer = document.getElementById('onlineUsersContainer');

    // Active Convo Header
    this.activeConvoAvatar = document.getElementById('activeConvoAvatar');
    this.activeConvoTitle = document.getElementById('activeConvoTitle');
    this.activeConvoSub = document.getElementById('activeConvoSub');
    this.btnClearMessages = document.getElementById('btnClearMessages');

    // Message list
    this.chatMessagesScroll = document.getElementById('chatMessagesScroll');
    this.messagesListWrapper = document.getElementById('messagesListWrapper');
    this.chatWelcomeBanner = document.getElementById('chatWelcomeBanner');
    this.typingIndicatorBar = document.getElementById('typingIndicatorBar');

    // Composer
    this.recipientNameText = document.getElementById('recipientNameText');
    this.btnClearTarget = document.getElementById('btnClearTarget');
    this.inputChatMessage = document.getElementById('inputChatMessage');
    this.btnSendMessage = document.getElementById('btnSendMessage');
    this.btnOpenEmoji = document.getElementById('btnOpenEmoji');
    this.emojiPopupPanel = document.getElementById('emojiPopupPanel');

    // Điền sẵn địa chỉ WebSocket mặc định
    if (this.inputServerUrl) {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.inputServerUrl.value = `${proto}//${location.host}/ws`;
    }

    this.bindEvents();
  }

  bindEvents() {
    // Form tham gia chat
    if (this.formJoin) {
      this.formJoin.addEventListener('submit', (e) => {
        e.preventDefault();
        this.actionJoin();
      });
    }

    // Tên ngẫu nhiên
    if (this.btnRandomName) {
      this.btnRandomName.addEventListener('click', () => {
        const randomNames = ['NguyenVanA', 'CyberHacker', 'NetMaster', 'ThangDev', 'SocketCoder', 'EchoKnight', 'LanUser', 'ByteWarrior'];
        const chosen = randomNames[Math.floor(Math.random() * randomNames.length)] + '_' + Math.floor(10 + Math.random() * 90);
        if (this.inputUsername) this.inputUsername.value = chosen;
      });
    }

    // Ngắt kết nối từ Header
    if (this.btnHeaderDisconnect) {
      this.btnHeaderDisconnect.addEventListener('click', () => {
        if (confirm('Bạn có chắc muốn rời phòng chat không?')) {
          this.disconnect();
        }
      });
    }

    // Chọn kênh Phòng Chung
    if (this.channelPublic) {
      this.channelPublic.addEventListener('click', () => {
        this.selectTarget('ALL');
      });
    }

    // Nút hủy chat riêng
    if (this.btnClearTarget) {
      this.btnClearTarget.addEventListener('click', () => {
        this.selectTarget('ALL');
      });
    }

    // Nút xóa màn hình chat
    if (this.btnClearMessages) {
      this.btnClearMessages.addEventListener('click', () => {
        if (this.messagesListWrapper) this.messagesListWrapper.innerHTML = '';
      });
    }

    // Tìm kiếm user trong sidebar
    if (this.inputSearchUser) {
      this.inputSearchUser.addEventListener('input', () => {
        this.renderOnlineUsersList();
      });
    }

    // Gửi tin nhắn bằng nút hoặc Enter
    if (this.btnSendMessage) {
      this.btnSendMessage.addEventListener('click', () => this.actionSendMessage());
    }

    if (this.inputChatMessage) {
      this.inputChatMessage.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.actionSendMessage();
        }
      });

      // Tự động giãn nở textarea
      this.inputChatMessage.addEventListener('input', () => {
        this.inputChatMessage.style.height = 'auto';
        this.inputChatMessage.style.height = Math.min(this.inputChatMessage.scrollHeight, 120) + 'px';
      });
    }

    // Popup Emoji
    if (this.btnOpenEmoji) {
      this.btnOpenEmoji.addEventListener('click', (e) => {
        e.stopPropagation();
        this.emojiPopupPanel?.classList.toggle('hidden');
      });
    }

    document.addEventListener('click', (e) => {
      if (this.emojiPopupPanel && !this.emojiPopupPanel.contains(e.target) && e.target !== this.btnOpenEmoji) {
        this.emojiPopupPanel.classList.add('hidden');
      }
    });
  }

  renderAvatarPicker() {
    if (!this.avatarPickerGrid) return;
    this.avatarPickerGrid.innerHTML = this.presetAvatars.map((av, idx) => `
      <div class="avatar-choice ${idx === 0 ? 'active' : ''}" data-avatar="${av}">
        ${av}
      </div>
    `).join('');

    this.avatarPickerGrid.querySelectorAll('.avatar-choice').forEach(el => {
      el.addEventListener('click', (e) => {
        this.avatarPickerGrid.querySelectorAll('.avatar-choice').forEach(a => a.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.userAvatar = e.currentTarget.dataset.avatar || '👨‍💻';
      });
    });
  }

  renderEmojiPicker() {
    const grid = document.getElementById('emojiGrid');
    if (!grid) return;

    grid.innerHTML = this.presetEmojis.map(emo => `
      <button type="button" class="emoji-btn" data-emoji="${emo}">${emo}</button>
    `).join('');

    grid.querySelectorAll('.emoji-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const char = e.currentTarget.dataset.emoji;
        if (this.inputChatMessage) {
          this.inputChatMessage.value += char;
          this.inputChatMessage.focus();
        }
        this.emojiPopupPanel?.classList.add('hidden');
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // KẾT NỐI & XỬ LÝ SOCKET
  // ─────────────────────────────────────────────────────────────────
  actionJoin() {
    const username = (this.inputUsername?.value || '').trim();
    let wsUrl = (this.inputServerUrl?.value || '').trim();

    if (!username) {
      this.showLoginFeedback('Vui lòng nhập tên người dùng (Nickname).');
      return;
    }

    this.hideLoginFeedback();
    this.btnJoinSubmit.disabled = true;
    this.btnJoinSubmit.innerHTML = `<span>Đang kết nối...</span>`;

    this.username = username;
    const token = window.authManager?.getToken() || '';

    // Gắn room code và token vào WebSocket URL
    try {
      const url = new URL(wsUrl.startsWith('ws') ? wsUrl : `ws://${window.location.host}${wsUrl}`);
      url.searchParams.set('room', this.roomCode);
      if (token) url.searchParams.set('token', token);
      wsUrl = url.toString();
    } catch (e) {
      const sep = wsUrl.includes('?') ? '&' : '?';
      wsUrl = `${wsUrl}${sep}room=${encodeURIComponent(this.roomCode)}${token ? `&token=${encodeURIComponent(token)}` : ''}`;
    }

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        // Gửi gói tin JOIN kèm room và token
        const joinPacket = {
          type: 'JOIN',
          data: {
            username: this.username,
            room: this.roomCode,
            token: token
          }
        };
        this.sendJSON(joinPacket);
      };

      this.ws.onmessage = (event) => {
        this.handleSocketMessage(event.data);
      };

      this.ws.onclose = () => {
        this.handleDisconnected();
      };

      this.ws.onerror = () => {
        this.showLoginFeedback('Không thể kết nối tới Server. Hãy chắc chắn Server đang chạy!');
        this.resetJoinBtn();
      };

    } catch (err) {
      this.showLoginFeedback('Lỗi khởi tạo WebSocket: ' + err.message);
      this.resetJoinBtn();
    }
  }

  sendJSON(packetObj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(packetObj));
      // Ghi nhận gói tin gửi đi vào Inspector
      window.protocolManager?.recordPacket('OUT', packetObj);
    }
  }

  handleSocketMessage(rawText) {
    let packet;
    try {
      packet = JSON.parse(rawText);
    } catch (_) {
      return;
    }

    // Ghi nhận gói tin nhận về vào Inspector
    window.protocolManager?.recordPacket('IN', packet);

    const type = packet.type;
    const data = packet.data || {};

    if (type === 'WELCOME') {
      this.clientId = data.client_id;
      this.isConnected = true;
      this.onJoinSuccess();
      window.soundFX?.playJoin();
      window.app?.showToast(data.message, 'success');

      // Bắt đầu chu kỳ ping tính độ trễ
      this.startPingLoop();

    } else if (type === 'ONLINE_LIST') {
      this.onlineUsers = data.users_detail || (data.users || []).map(u => ({ username: u, id: '?', type: 'websocket' }));
      this.renderOnlineUsersList();

    } else if (type === 'MSG') {
      const isSelf = data.username === this.username;
      this.appendMessageRow({
        type: 'MSG',
        isSelf,
        sender: data.username,
        clientId: data.client_id,
        clientType: data.client_type,
        content: data.content,
        timestamp: data.timestamp
      });

      if (isSelf) {
        window.soundFX?.playSent();
      } else {
        window.soundFX?.playReceived();
        this.notifyUnread();
      }

    } else if (type === 'PRIVATE') {
      const isSender = data.is_sender;
      const otherUser = isSender ? data.to : data.from;

      this.appendMessageRow({
        type: 'PRIVATE',
        isSelf: isSender,
        from: data.from,
        to: data.to,
        sender: isSender ? this.username : data.from,
        clientId: data.sender_id,
        content: data.content,
        timestamp: data.timestamp,
        isSender
      });

      // Tạo cuộc trò chuyện riêng trong danh sách DM nếu chưa có
      this.ensureDMConversation(otherUser);

      if (isSender) {
        window.soundFX?.playSent();
      } else {
        window.soundFX?.playWhisper();
        this.notifyUnread();
        window.app?.showToast(`Tin nhắn riêng mới từ ${data.from}!`, 'info');
      }

    } else if (type === 'SYSTEM') {
      this.appendSystemRow(data.message, data.is_admin_announcement);
      if (data.is_admin_announcement) {
        window.soundFX?.playWhisper();
      }

    } else if (type === 'ERROR') {
      if (!this.isConnected) {
        this.showLoginFeedback(data.message);
        this.resetJoinBtn();
      } else {
        this.appendSystemRow(`[LỖI] ${data.message}`, false, true);
        window.app?.showToast(data.message, 'danger');
      }

    } else if (type === 'PONG') {
      if (this.pingStartTime) {
        const rtt = Math.round((performance.now() - this.pingStartTime));
        if (this.pingValueEl) this.pingValueEl.textContent = `${rtt} ms`;
      }
    }
  }

  onJoinSuccess() {
    if (this.loginOverlay) this.loginOverlay.classList.add('hidden');
    if (this.headerUserBadge) this.headerUserBadge.classList.remove('hidden');
    if (this.headerAvatar) this.headerAvatar.textContent = this.userAvatar;
    if (this.headerUserName) this.headerUserName.textContent = this.username;
    if (this.headerUserId) this.headerUserId.textContent = `ID #${this.clientId}`;

    if (this.statusPulseDot) {
      this.statusPulseDot.className = 'pulse-indicator online';
    }
    if (this.connectionStatusLabel) {
      this.connectionStatusLabel.textContent = 'Trực tuyến';
    }

    if (this.inputChatMessage) this.inputChatMessage.focus();
  }

  handleDisconnected() {
    this.isConnected = false;
    clearInterval(this.pingInterval);

    if (this.headerUserBadge) this.headerUserBadge.classList.add('hidden');
    if (this.statusPulseDot) {
      this.statusPulseDot.className = 'pulse-indicator offline';
    }
    if (this.connectionStatusLabel) {
      this.connectionStatusLabel.textContent = 'Mất kết nối';
    }
    if (this.pingValueEl) this.pingValueEl.textContent = '-- ms';

    if (this.loginOverlay) {
      this.loginOverlay.classList.remove('hidden');
      this.showLoginFeedback('Bạn đã ngắt kết nối khỏi máy chủ.');
      this.resetJoinBtn();
    }
  }

  disconnect() {
    if (this.ws) {
      try {
        this.sendJSON({ type: 'QUIT', data: {} });
        this.ws.close();
      } catch (_) {}
    }
    this.handleDisconnected();
  }

  startPingLoop() {
    clearInterval(this.pingInterval);
    this.pingInterval = setInterval(() => {
      if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
        this.pingStartTime = performance.now();
        this.ws.send(JSON.stringify({ type: 'PING', data: {} }));
      }
    }, 10000);
  }

  resetJoinBtn() {
    if (this.btnJoinSubmit) {
      this.btnJoinSubmit.disabled = false;
      this.btnJoinSubmit.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
          <polyline points="10 17 15 12 10 7"></polyline>
          <line x1="15" y1="12" x2="3" y2="12"></line>
        </svg>
        <span>Vào Phòng Trò Chuyện</span>
      `;
    }
  }

  showLoginFeedback(text) {
    if (this.loginFeedback) {
      this.loginFeedback.textContent = text;
      this.loginFeedback.classList.remove('hidden');
    }
  }

  hideLoginFeedback() {
    if (this.loginFeedback) this.loginFeedback.classList.add('hidden');
  }

  // ─────────────────────────────────────────────────────────────────
  // GỬI TIN NHẮN & PHÂN TÍCH LỆNH (SLASH COMMANDS)
  // ─────────────────────────────────────────────────────────────────
  actionSendMessage() {
    if (!this.inputChatMessage) return;
    const text = this.inputChatMessage.value.trim();
    if (!text) return;

    // Reset khung nhập
    this.inputChatMessage.value = '';
    this.inputChatMessage.style.height = 'auto';

    // 1. Phân tích lệnh gõ tắt (Slash Commands)
    if (text.startsWith('/')) {
      const parts = text.slice(1).split(' ');
      const cmd = parts[0].toLowerCase();

      if (cmd === 'w' || cmd === 'pm' || cmd === 'msg') {
        const targetUser = parts[1];
        const content = parts.slice(2).join(' ');
        if (!targetUser || !content) {
          this.appendSystemRow("Cú pháp gửi tin riêng: /w <tên> <nội dung>", false, true);
          return;
        }
        this.sendJSON({
          type: 'PRIVATE',
          data: { to: targetUser, content }
        });
        return;
      } else if (cmd === 'clear') {
        if (this.messagesListWrapper) this.messagesListWrapper.innerHTML = '';
        return;
      } else if (cmd === 'help') {
        this.appendSystemRow("Hỗ trợ lệnh: /w <tên> <nội dung> (Chat riêng), /clear (Xóa màn hình), /help (Trợ giúp).", false);
        return;
      }
    }

    // 2. Gửi tin nhắn thông thường
    if (this.activeTarget === 'ALL') {
      // Gửi phòng chung
      this.sendJSON({
        type: 'MSG',
        data: { content: text }
      });
    } else {
      // Gửi riêng cho activeTarget đang chọn
      this.sendJSON({
        type: 'PRIVATE',
        data: { to: this.activeTarget, content: text }
      });
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // HIỂN THỊ TIN NHẮN (MESSAGE BUBBLES RENDERING)
  // ─────────────────────────────────────────────────────────────────
  appendMessageRow(msg) {
    if (!this.messagesListWrapper) return;

    const row = document.createElement('div');
    const isSelf = msg.isSelf;
    const isPrivate = msg.type === 'PRIVATE';

    row.className = `message-row ${isSelf ? 'self' : 'others'} ${isPrivate ? 'private-whisper' : ''}`;

    const avatarChar = isSelf ? this.userAvatar : (msg.sender?.[0]?.toUpperCase() || 'U');
    const avatarColor = this.generateColorFromString(msg.sender || 'User');

    const platform = msg.clientType === 'tcp' 
      ? '<span class="msg-platform-badge">💻 TCP</span>' 
      : '<span class="msg-platform-badge">🌐 Web</span>';

    const clientIdText = msg.clientId ? `<span class="msg-client-id">#${msg.clientId}</span>` : '';

    let whisperHeader = '';
    if (isPrivate) {
      whisperHeader = `
        <div class="whisper-badge">
          🔒 TIN NHẮN RIÊNG: ${msg.isSender ? `Tới @${msg.to}` : `Từ @${msg.from}`}
        </div>
      `;
    }

    row.innerHTML = `
      <div class="message-avatar" style="background:${avatarColor};">${avatarChar}</div>
      <div class="message-content-box">
        <div class="message-meta-header">
          <span class="msg-sender-name">${this.escapeHTML(msg.sender || 'User')}</span>
          ${clientIdText}
          ${platform}
          <span class="msg-timestamp">${msg.timestamp || ''}</span>
        </div>
        <div class="message-bubble">
          ${whisperHeader}
          <div class="msg-text">${this.escapeHTML(msg.content || '')}</div>
        </div>
      </div>
    `;

    this.messagesListWrapper.appendChild(row);
    this.scrollToBottom();
  }

  appendSystemRow(text, isAdminAnnouncement = false, isError = false) {
    if (!this.messagesListWrapper) return;

    const row = document.createElement('div');
    row.className = 'system-event-row';

    let extraClass = '';
    let icon = '📢';

    if (isAdminAnnouncement) {
      extraClass = 'admin-announcement';
      icon = '🚨';
    } else if (isError) {
      extraClass = 'error-event';
      icon = '❌';
    }

    row.innerHTML = `
      <div class="system-pill ${extraClass}">
        <span>${icon}</span>
        <span>${this.escapeHTML(text)}</span>
      </div>
    `;

    this.messagesListWrapper.appendChild(row);
    this.scrollToBottom();
  }

  scrollToBottom() {
    if (this.chatMessagesScroll) {
      this.chatMessagesScroll.scrollTop = this.chatMessagesScroll.scrollHeight;
    }
  }

  notifyUnread() {
    const activeTab = document.querySelector('.nav-tab-btn.active')?.dataset.tab;
    if (activeTab !== 'chat') {
      this.unreadCount++;
      const pill = document.getElementById('chatUnreadPill');
      if (pill) {
        pill.textContent = this.unreadCount;
        pill.classList.remove('hidden');
      }
    }
  }

  clearUnread() {
    this.unreadCount = 0;
    const pill = document.getElementById('chatUnreadPill');
    if (pill) pill.classList.add('hidden');
  }

  // ─────────────────────────────────────────────────────────────────
  // QUẢN LÝ DANH SÁCH USER & CUỘC TRÒ CHUYỆN (DM / CHANNEL)
  // ─────────────────────────────────────────────────────────────────
  renderOnlineUsersList() {
    if (!this.onlineUsersContainer) return;

    const q = (this.inputSearchUser?.value || '').toLowerCase().trim();
    const filtered = this.onlineUsers.filter(u => !q || u.username.toLowerCase().includes(q));

    const total = this.onlineUsers.length;
    if (this.onlineTotalBadge) this.onlineTotalBadge.textContent = total;
    if (this.userCountSpan) this.userCountSpan.textContent = total;

    this.onlineUsersContainer.innerHTML = filtered.map(u => {
      const isMe = u.username === this.username;
      const avatarChar = isMe ? this.userAvatar : (u.username[0]?.toUpperCase() || 'U');
      const avatarColor = this.generateColorFromString(u.username);
      const isTcp = u.type === 'tcp';
      const platformTag = isTcp
        ? '<span class="user-platform-tag tcp">💻 TCP</span>'
        : '<span class="user-platform-tag web">🌐 Web</span>';

      return `
        <div class="user-card-item ${isMe ? 'is-me' : ''}" data-username="${this.escapeHTML(u.username)}">
          <div class="user-avatar-wrap">
            <div class="user-avatar-circle" style="background:${avatarColor};">${avatarChar}</div>
            <span class="online-dot"></span>
          </div>
          <div class="user-meta-wrap">
            <div class="user-name-line">
              <span class="user-nick">${this.escapeHTML(u.username)}</span>
              ${isMe ? '<span style="font-size:0.68rem; color:var(--primary); font-weight:700;">(Tôi)</span>' : ''}
              <span class="user-client-id">#${u.id || ''}</span>
            </div>
          </div>
          ${platformTag}
        </div>
      `;
    }).join('');

    // Bắt sự kiện double-click hoặc click vào user để bắt đầu chat riêng
    this.onlineUsersContainer.querySelectorAll('.user-card-item').forEach(el => {
      el.addEventListener('dblclick', (e) => {
        const targetName = e.currentTarget.dataset.username;
        if (targetName && targetName !== this.username) {
          this.selectTarget(targetName);
        }
      });
      el.addEventListener('click', (e) => {
        const targetName = e.currentTarget.dataset.username;
        if (targetName && targetName !== this.username) {
          this.selectTarget(targetName);
        }
      });
    });
  }

  selectTarget(target) {
    this.activeTarget = target;

    if (target === 'ALL') {
      if (this.recipientNameText) this.recipientNameText.textContent = 'Tất cả mọi người (Phòng Chung)';
      if (this.btnClearTarget) this.btnClearTarget.classList.add('hidden');
      if (this.activeConvoAvatar) this.activeConvoAvatar.textContent = '🌐';
      if (this.activeConvoTitle) this.activeConvoTitle.textContent = 'Phòng Chung (Public Lounge)';
      if (this.activeConvoSub) this.activeConvoSub.textContent = 'Tin nhắn phát tới tất cả các Client Web & Desktop';
      if (this.channelPublic) this.channelPublic.classList.add('active');
    } else {
      if (this.recipientNameText) this.recipientNameText.textContent = `@${target} (Nhắn Riêng)`;
      if (this.btnClearTarget) this.btnClearTarget.classList.remove('hidden');
      if (this.activeConvoAvatar) this.activeConvoAvatar.textContent = '🔒';
      if (this.activeConvoTitle) this.activeConvoTitle.textContent = `Chat Riêng Với: ${target}`;
      if (this.activeConvoSub) this.activeConvoSub.textContent = 'Chỉ bạn và người nhận có thể đọc tin này';
      if (this.channelPublic) this.channelPublic.classList.remove('active');
    }

    if (this.inputChatMessage) this.inputChatMessage.focus();
  }

  ensureDMConversation(otherUser) {
    if (!otherUser || otherUser === this.username) return;

    if (this.dmConversationsBox) {
      this.dmConversationsBox.classList.remove('hidden');
    }

    // Kiểm tra xem đã có tab DM cho user này chưa
    let item = this.dmList?.querySelector(`[data-dm-user="${otherUser}"]`);
    if (!item && this.dmList) {
      item = document.createElement('div');
      item.className = 'dm-item';
      item.dataset.dmUser = otherUser;
      item.innerHTML = `
        <div class="channel-icon" style="color:var(--purple);">🔒</div>
        <div class="dm-info">
          <div class="dm-name">${this.escapeHTML(otherUser)}</div>
          <div class="dm-sub">Tin nhắn riêng</div>
        </div>
      `;
      item.addEventListener('click', () => {
        this.selectTarget(otherUser);
      });
      this.dmList.appendChild(item);
    }
  }

  generateColorFromString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = Math.abs(hash % 360);
    return `hsl(${h}, 65%, 48%)`;
  }

  escapeHTML(str) {
    return String(str || '').replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

// Khởi tạo instance toàn cục
window.chatClient = new ChatClientController();
