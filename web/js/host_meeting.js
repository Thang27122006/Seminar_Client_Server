/**
 * HostMeeting - Bộ Điều Khiển Trung Tâm Phòng Họp & Giám Sát Mạng
 * Theo phong cách Google Meet Host Controls & Zoom Meeting Studio.
 */

class MeetingHostController {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.clients = [];
    this.logs = [];
    this.stats = {};
    this.selectedClientId = null;
    this.activeTag = 'ALL';
    this.searchQuery = '';
    this.participantQuery = '';

    const urlParams = new URLSearchParams(window.location.search);
    this.roomCode = urlParams.get('room') || urlParams.get('code') || 'seminar-network-lab';

    this.initDOM();
    this.applyTheme();
    this.applySound();
    this.connectWS();
  }

  initDOM() {
    // Room Code Display
    const roomCodeEl = document.querySelector('.meet-room-code strong');
    if (roomCodeEl) roomCodeEl.textContent = this.roomCode;
    // Topbar elements
    this.meetingUptimeEl = document.getElementById('hostMeetingUptime');
    this.roomLockIcon = document.getElementById('roomLockStatusIcon');
    this.roomLockText = document.getElementById('roomLockStatusText');
    this.roomSecurityPill = document.getElementById('roomSecurityPill');
    this.btnCopyLink = document.getElementById('btnCopyMeetingLink');
    this.btnToggleSound = document.getElementById('btnAdminToggleSound');
    this.btnToggleTheme = document.getElementById('btnAdminToggleTheme');

    // Ribbon KPI elements
    this.ribbonOnlineTotal = document.getElementById('ribbonOnlineTotal');
    this.ribbonClientsBreakdown = document.getElementById('ribbonClientsBreakdown');
    this.ribbonTotalMessages = document.getElementById('ribbonTotalMessages');
    this.ribbonTrafficBytes = document.getElementById('ribbonTrafficBytes');
    this.ribbonTotalSessions = document.getElementById('ribbonTotalSessions');
    this.ribbonPermissionsText = document.getElementById('ribbonPermissionsText');
    this.ribbonPermissionsSub = document.getElementById('ribbonPermissionsSub');

    // Stage Tiles container
    this.tilesContainer = document.getElementById('participantTilesContainer');
    this.emptyRoomState = document.getElementById('emptyRoomState');

    // Sidepanel & Navigation
    this.sidePanel = document.getElementById('meetSidePanel');
    this.panelTabBtns = document.querySelectorAll('.panel-tab-btn');
    this.panelViews = {
      participants: document.getElementById('panelParticipants'),
      security: document.getElementById('panelSecurity'),
      chat: document.getElementById('panelChat'),
      terminal: document.getElementById('panelTerminal')
    };
    this.panelUserCounter = document.getElementById('panelUserCounter');
    this.bottomUserBadge = document.getElementById('bottomUserBadge');

    // Panel 1: Participants List
    this.inputSearchParticipant = document.getElementById('inputSearchParticipant');
    this.participantsScrollList = document.getElementById('participantsScrollList');
    this.btnHostMuteAll = document.getElementById('btnHostMuteAll');

    // Panel 2: Host Controls / Security
    this.chkLockRoom = document.getElementById('chkLockRoom');
    this.badgeLockState = document.getElementById('badgeLockState');
    this.chkPublicChat = document.getElementById('chkPublicChat');
    this.badgePublicChatState = document.getElementById('badgePublicChatState');
    this.chkPrivateChat = document.getElementById('chkPrivateChat');
    this.badgePrivateChatState = document.getElementById('badgePrivateChatState');
    this.formBroadcast = document.getElementById('formHostBroadcast');
    this.inputBroadcastText = document.getElementById('inputHostBroadcastText');

    // Panel 3: Live Chat Monitor
    this.chatMessagesContainer = document.getElementById('hostChatMessages');
    this.inputHostChatDirect = document.getElementById('inputHostChatDirect');
    this.btnHostSendChat = document.getElementById('btnHostSendChat');
    this.btnClearHostChat = document.getElementById('btnClearHostChat');

    // Panel 4: Server Terminal Console
    this.hostTerminalLines = document.getElementById('hostTerminalLines');
    this.hostTerminalScroll = document.getElementById('hostTerminalScroll');
    this.inputSearchTerminal = document.getElementById('inputSearchTerminal');
    this.chkAutoScroll = document.getElementById('chkAutoScrollHost');
    this.btnClearTerminal = document.getElementById('btnClearTerminal');
    this.btnExportTerminal = document.getElementById('btnExportTerminal');

    // Bottombar Control buttons
    this.btnBottomLockRoom = document.getElementById('btnBottomLockRoom');
    this.bottomLockIcon = document.getElementById('bottomLockIcon');
    this.btnBottomMuteAll = document.getElementById('btnBottomMuteAll');
    this.btnBottomBroadcast = document.getElementById('btnBottomBroadcast');
    this.btnBottomTogglePeople = document.getElementById('btnBottomTogglePeople');
    this.btnBottomToggleChat = document.getElementById('btnBottomToggleChat');
    this.btnBottomToggleSecurity = document.getElementById('btnBottomToggleSecurity');
    this.btnBottomToggleTerminal = document.getElementById('btnBottomToggleTerminal');
    this.btnEndHostSession = document.getElementById('btnEndHostSession');

    // Modals
    this.modalKick = document.getElementById('modalHostKick');
    this.kickTargetName = document.getElementById('hostKickTargetName');
    this.inputKickReason = document.getElementById('inputHostKickReason');
    this.btnConfirmKick = document.getElementById('btnHostConfirmKick');

    this.modalDm = document.getElementById('modalHostDm');
    this.dmTargetName = document.getElementById('hostDmTargetName');
    this.inputDmMsg = document.getElementById('inputHostDmMsg');
    this.btnConfirmDm = document.getElementById('btnHostConfirmDm');

    this.toastContainer = document.getElementById('toastContainer');

    this.bindEvents();
  }

  bindEvents() {
    // Copy meeting link
    if (this.btnCopyLink) {
      this.btnCopyLink.addEventListener('click', () => {
        const link = `${window.location.origin}/room?code=${encodeURIComponent(this.roomCode)}`;
        navigator.clipboard?.writeText(link).then(() => {
          this.showToast(`Đã sao chép link phòng: ${link}`, 'success');
        }).catch(() => {
          this.showToast(`Link phòng: ${link}`, 'info');
        });
      });
    }

    // Toggle Theme
    if (this.btnToggleTheme) {
      this.btnToggleTheme.addEventListener('click', () => this.toggleTheme());
    }

    // Toggle Sound
    if (this.btnToggleSound) {
      this.btnToggleSound.addEventListener('click', () => {
        const isMuted = window.soundFX?.toggleMute();
        this.updateSoundIcons(isMuted);
        this.showToast(isMuted ? 'Đã tắt âm thanh' : 'Đã bật âm thanh', 'info');
      });
    }

    // Sidepanel tabs
    this.panelTabBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const panelKey = e.currentTarget.dataset.panel;
        this.switchSidePanel(panelKey);
      });
    });

    // Bottombar shortcuts
    if (this.btnBottomTogglePeople) {
      this.btnBottomTogglePeople.addEventListener('click', () => this.switchSidePanel('participants'));
    }
    if (this.btnBottomToggleSecurity) {
      this.btnBottomToggleSecurity.addEventListener('click', () => this.switchSidePanel('security'));
    }
    if (this.btnBottomToggleChat) {
      this.btnBottomToggleChat.addEventListener('click', () => this.switchSidePanel('chat'));
    }
    if (this.btnBottomToggleTerminal) {
      this.btnBottomToggleTerminal.addEventListener('click', () => this.switchSidePanel('terminal'));
    }

    // Bottom quick actions
    if (this.btnBottomLockRoom) {
      this.btnBottomLockRoom.addEventListener('click', () => {
        this.sendCommand('ADMIN_TOGGLE_LOCK', {});
      });
    }
    if (this.btnBottomMuteAll || this.btnHostMuteAll) {
      const handleMuteAll = () => {
        if (confirm('Bạn có chắc muốn tắt quyền gửi tin nhắn của TẤT CẢ người tham gia?')) {
          this.sendCommand('ADMIN_MUTE_ALL', {});
        }
      };
      if (this.btnBottomMuteAll) this.btnBottomMuteAll.addEventListener('click', handleMuteAll);
      if (this.btnHostMuteAll) this.btnHostMuteAll.addEventListener('click', handleMuteAll);
    }
    if (this.btnBottomBroadcast) {
      this.btnBottomBroadcast.addEventListener('click', () => {
        this.switchSidePanel('security');
        this.inputBroadcastText?.focus();
      });
    }

    // End Host session
    if (this.btnEndHostSession) {
      this.btnEndHostSession.addEventListener('click', () => {
        if (confirm('Rời khỏi phiên điều khiển của Host và quay lại phòng chat client?')) {
          window.location.href = '/';
        }
      });
    }

    // Security switches
    if (this.chkLockRoom) {
      this.chkLockRoom.addEventListener('change', () => {
        this.sendCommand('ADMIN_TOGGLE_LOCK', {});
      });
    }
    if (this.chkPublicChat) {
      this.chkPublicChat.addEventListener('change', () => {
        this.sendCommand('ADMIN_TOGGLE_PUBLIC_CHAT', {});
      });
    }
    if (this.chkPrivateChat) {
      this.chkPrivateChat.addEventListener('change', () => {
        this.sendCommand('ADMIN_TOGGLE_PRIVATE_CHAT', {});
      });
    }

    // Host Broadcast form
    if (this.formBroadcast) {
      this.formBroadcast.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = (this.inputBroadcastText?.value || '').trim();
        if (!text) return;
        this.sendCommand('ADMIN_BROADCAST', { message: text });
        this.inputBroadcastText.value = '';
        this.showToast('Đã phát thông báo khẩn từ Host!', 'success');
      });
    }

    // Direct Host chat
    if (this.btnHostSendChat && this.inputHostChatDirect) {
      const sendDirect = () => {
        const text = this.inputHostChatDirect.value.trim();
        if (!text) return;
        this.sendCommand('ADMIN_BROADCAST', { message: `[👑 HOST]: ${text}` });
        this.inputHostChatDirect.value = '';
      };
      this.btnHostSendChat.addEventListener('click', sendDirect);
      this.inputHostChatDirect.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendDirect();
      });
    }

    if (this.btnClearHostChat) {
      this.btnClearHostChat.addEventListener('click', () => {
        if (this.chatMessagesContainer) {
          this.chatMessagesContainer.innerHTML = '<div class="empty-chat-hint">Đã xóa màn hình giám sát.</div>';
        }
      });
    }

    // Search participants
    if (this.inputSearchParticipant) {
      this.inputSearchParticipant.addEventListener('input', (e) => {
        this.participantQuery = e.target.value.toLowerCase().trim();
        this.renderParticipants();
      });
    }

    // Terminal Tag chips
    document.querySelectorAll('.btn-tag-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        document.querySelectorAll('.btn-tag-chip').forEach(c => c.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.activeTag = e.currentTarget.dataset.tag || 'ALL';
        this.renderTerminalLogs();
      });
    });

    if (this.inputSearchTerminal) {
      this.inputSearchTerminal.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.renderTerminalLogs();
      });
    }

    if (this.btnClearTerminal) {
      this.btnClearTerminal.addEventListener('click', () => {
        this.logs = [];
        this.renderTerminalLogs();
        this.sendCommand('ADMIN_CLEAR_LOGS', {});
      });
    }

    if (this.btnExportTerminal) {
      this.btnExportTerminal.addEventListener('click', () => this.exportLogsToFile());
    }

    // Modals confirm buttons
    if (this.btnConfirmKick) {
      this.btnConfirmKick.addEventListener('click', () => {
        if (!this.selectedClientId) return;
        const reason = this.inputKickReason?.value.trim() || 'Host đã mời bạn ra khỏi phòng.';
        this.sendCommand('ADMIN_KICK', { client_id: this.selectedClientId, reason });
        this.closeModal(this.modalKick);
        this.showToast(`Đã mời Client #${this.selectedClientId} ra khỏi cuộc họp!`, 'warning');
      });
    }

    if (this.btnConfirmDm) {
      this.btnConfirmDm.addEventListener('click', () => {
        if (!this.selectedClientId) return;
        const msg = (this.inputDmMsg?.value || '').trim();
        if (!msg) return;
        this.sendCommand('ADMIN_DM', { client_id: this.selectedClientId, message: msg });
        this.inputDmMsg.value = '';
        this.closeModal(this.modalDm);
        this.showToast(`Đã gửi tin nhắn tới Client #${this.selectedClientId}!`, 'success');
      });
    }

    // Close modals
    document.querySelectorAll('[data-close-modal]').forEach(b => {
      b.addEventListener('click', (e) => {
        const id = e.currentTarget.dataset.closeModal;
        const modal = document.getElementById(id);
        if (modal) this.closeModal(modal);
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // WEBSOCKET & DATA SYNC
  // ─────────────────────────────────────────────────────────────────
  connectWS() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${location.host}/ws/admin?room=${encodeURIComponent(this.roomCode)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.showToast('Đã kết nối máy chủ quản trị Host', 'success');
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleHostEvent(payload.event, payload.data);
        } catch (_) {}
      };

      this.ws.onclose = () => {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => this.connectWS(), 2500);
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch (_) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.connectWS(), 3000);
    }
  }

  sendCommand(type, data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }

  handleHostEvent(event, data) {
    if (event === 'INIT') {
      this.updateStats(data.stats);
      this.updateClients(data.clients);
      if (Array.isArray(data.logs)) {
        this.logs = data.logs;
        this.renderTerminalLogs();
      }
    } else if (event === 'STATS_UPDATE') {
      this.updateStats(data);
    } else if (event === 'CLIENTS_UPDATE') {
      this.updateClients(data);
    } else if (event === 'CLIENT_CONNECT' || event === 'CLIENT_JOIN' || event === 'CLIENT_LEAVE') {
      this.fetchClientsViaHTTP();
    } else if (event === 'MESSAGE') {
      this.appendLiveChatMessage(data);
    } else if (event === 'LOG') {
      this.logs.push(data);
      if (this.logs.length > 500) this.logs.shift();
      this.appendTerminalLogEntry(data);
    } else if (event === 'LOGS_CLEARED') {
      this.logs = [];
      this.renderTerminalLogs();
    } else if (event === 'ACTION_RESULT') {
      if (data.message) {
        this.showToast(data.message, data.ok ? 'success' : 'warning');
      }
    }
  }

  async fetchClientsViaHTTP() {
    try {
      const res = await fetch('/api/clients');
      if (res.ok) {
        const clients = await res.json();
        this.updateClients(clients);
      }
      const statsRes = await fetch('/api/stats');
      if (statsRes.ok) {
        const stats = await statsRes.json();
        this.updateStats(stats);
      }
    } catch (_) {}
  }

  updateStats(stats) {
    if (!stats) return;
    this.stats = stats;

    if (this.meetingUptimeEl) this.meetingUptimeEl.textContent = stats.uptime_str || '00:00:00';
    if (this.ribbonOnlineTotal) this.ribbonOnlineTotal.textContent = stats.online_total || 0;
    if (this.ribbonTotalMessages) this.ribbonTotalMessages.textContent = stats.total_messages || 0;
    if (this.ribbonTotalSessions) this.ribbonTotalSessions.textContent = `Tổng kết nối: ${stats.total_connections || 0}`;

    if (this.ribbonClientsBreakdown) {
      this.ribbonClientsBreakdown.textContent = `Web: ${stats.online_ws || 0} • TCP: ${stats.online_tcp || 0}`;
    }

    if (this.ribbonTrafficBytes) {
      const b = stats.bytes_transferred || 0;
      if (b < 1024) this.ribbonTrafficBytes.textContent = b + ' B';
      else if (b < 1024 * 1024) this.ribbonTrafficBytes.textContent = (b / 1024).toFixed(1) + ' KB';
      else this.ribbonTrafficBytes.textContent = (b / (1024 * 1024)).toFixed(2) + ' MB';
    }

    // Room Lock Status
    const isLocked = !!stats.is_room_locked;
    if (this.roomSecurityPill) {
      if (isLocked) {
        this.roomSecurityPill.className = 'room-security-pill locked';
        if (this.roomLockIcon) this.roomLockIcon.textContent = '🔒';
        if (this.roomLockText) this.roomLockText.textContent = 'Phòng ĐÃ KHÓA';
        if (this.bottomLockIcon) this.bottomLockIcon.textContent = '🔓';
      } else {
        this.roomSecurityPill.className = 'room-security-pill';
        if (this.roomLockIcon) this.roomLockIcon.textContent = '🔓';
        if (this.roomLockText) this.roomLockText.textContent = 'Phòng Đang Mở';
        if (this.bottomLockIcon) this.bottomLockIcon.textContent = '🔒';
      }
    }

    if (this.chkLockRoom) this.chkLockRoom.checked = isLocked;
    if (this.badgeLockState) this.badgeLockState.textContent = isLocked ? 'Đã khóa' : 'Đang mở';

    // Public Chat
    const allowPublic = stats.allow_public_chat !== false;
    if (this.chkPublicChat) this.chkPublicChat.checked = allowPublic;
    if (this.badgePublicChatState) this.badgePublicChatState.textContent = allowPublic ? 'Bật' : 'Tắt';

    // Private Chat
    const allowPrivate = stats.allow_private_chat !== false;
    if (this.chkPrivateChat) this.chkPrivateChat.checked = allowPrivate;
    if (this.badgePrivateChatState) this.badgePrivateChatState.textContent = allowPrivate ? 'Bật' : 'Tắt';

    // Permissions summary text
    if (this.ribbonPermissionsText) {
      this.ribbonPermissionsText.textContent = isLocked ? 'Đang Khóa' : 'Bình thường';
      this.ribbonPermissionsText.className = isLocked ? 'ribbon-val text-amber' : 'ribbon-val text-success';
    }
    if (this.ribbonPermissionsSub) {
      this.ribbonPermissionsSub.textContent = `Chat chung: ${allowPublic ? 'BẬT' : 'TẮT'} • Riêng: ${allowPrivate ? 'BẬT' : 'TẮT'}`;
    }
  }

  updateClients(clients) {
    if (!Array.isArray(clients)) return;
    this.clients = clients;

    const count = clients.filter(c => c.is_active && c.username).length;
    if (this.panelUserCounter) this.panelUserCounter.textContent = count;
    if (this.bottomUserBadge) this.bottomUserBadge.textContent = count;

    this.renderStageTiles();
    this.renderParticipants();
  }

  // ─────────────────────────────────────────────────────────────────
  // RENDER STAGE TILES (GOOGLE MEET PARTICIPANT TILES)
  // ─────────────────────────────────────────────────────────────────
  renderStageTiles() {
    if (!this.tilesContainer) return;

    const activeClients = this.clients.filter(c => c.is_active);

    if (activeClients.length === 0) {
      this.tilesContainer.innerHTML = `
        <div class="empty-room-state" id="emptyRoomState">
          <div class="empty-room-graphic">👥</div>
          <h3>Phòng Họp Đang Trống</h3>
          <p>Chưa có Client nào kết nối tới Server. Hãy mở tab mới hoặc chạy Desktop Client để thấy người tham gia xuất hiện tại đây!</p>
          <div class="empty-room-actions">
            <a href="/" target="_blank" class="btn-primary-gradient">
              🚀 Mở Phòng Chat Client
            </a>
          </div>
        </div>
      `;
      return;
    }

    this.tilesContainer.innerHTML = activeClients.map(c => {
      const isWeb = c.type === 'websocket';
      const avatarChar = this.getInitials(c.fullname || c.username);
      const avatarColor = this.generateColorFromString(c.username || 'User');
      const isMuted = !!c.is_muted;
      const statusIcon = isMuted ? '🔇' : '🟢';

      const platformBadge = isWeb
        ? '<span class="tile-platform-chip">🌐 Web</span>'
        : '<span class="tile-platform-chip">💻 TCP</span>';

      return `
        <div class="participant-tile ${isMuted ? 'is-muted' : ''}" data-client-id="${c.id}">
          
          <!-- Avatar tròn giữa thẻ -->
          <div class="tile-avatar-halo ${isMuted ? 'muted' : ''}" style="background:${avatarColor};">
            ${avatarChar}
            ${!isMuted ? '<div class="tile-live-wave"></div>' : ''}
          </div>

          <!-- Thanh thông tin đáy thẻ -->
          <div class="tile-bottom-bar">
            <div class="tile-user-info">
              <span class="tile-status-icon">${statusIcon}</span>
              <span class="tile-name">${this.escapeHTML(c.username || 'Chờ JOIN')}</span>
              <span class="tile-id-badge">#${c.id}</span>
              ${platformBadge}
            </div>
            <span style="font-family:var(--font-code); font-size:0.65rem; color:#94A3B8;">${c.msg_count || 0} msgs</span>
          </div>

          <!-- Nút thao tác nhanh khi hover thẻ -->
          <div class="tile-hover-overlay">
            <button class="btn-tile-act mute" data-action="mute" data-client-id="${c.id}" title="${isMuted ? 'Mở lại quyền chat' : 'Tắt quyền chat (Mute)'}">
              ${isMuted ? '🔊' : '🔇'}
            </button>
            <button class="btn-tile-act dm" data-action="dm" data-client-id="${c.id}" data-name="${this.escapeHTML(c.username)}" title="Nhắn tin riêng">
              💬
            </button>
            <button class="btn-tile-act kick" data-action="kick" data-client-id="${c.id}" data-name="${this.escapeHTML(c.username)}" title="Mời ra khỏi phòng">
              👢
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Bắt sự kiện thao tác trên Tiles
    this.tilesContainer.querySelectorAll('.btn-tile-act').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = e.currentTarget.dataset.action;
        const cid = parseInt(e.currentTarget.dataset.clientId, 10);
        const name = e.currentTarget.dataset.name;

        if (action === 'mute') {
          this.sendCommand('ADMIN_TOGGLE_MUTE', { client_id: cid });
        } else if (action === 'dm') {
          this.selectedClientId = cid;
          if (this.dmTargetName) this.dmTargetName.textContent = name || `Client #${cid}`;
          this.openModal(this.modalDm);
        } else if (action === 'kick') {
          this.selectedClientId = cid;
          if (this.kickTargetName) this.kickTargetName.textContent = name || `Client #${cid}`;
          this.openModal(this.modalKick);
        }
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // RENDER PARTICIPANTS LIST (SIDEPANEL)
  // ─────────────────────────────────────────────────────────────────
  renderParticipants() {
    if (!this.participantsScrollList) return;

    const filtered = this.clients.filter(c => {
      if (!c.is_active) return false;
      if (!this.participantQuery) return true;
      return (c.username || '').toLowerCase().includes(this.participantQuery);
    });

    if (filtered.length === 0) {
      this.participantsScrollList.innerHTML = `
        <div style="text-align:center; padding:30px; font-size:0.8rem; color:#64748B;">
          Không tìm thấy người tham gia phù hợp.
        </div>
      `;
      return;
    }

    this.participantsScrollList.innerHTML = filtered.map(c => {
      const avatarChar = this.getInitials(c.fullname || c.username);
      const avatarColor = this.generateColorFromString(c.username || 'User');
      const isMuted = !!c.is_muted;
      const isWeb = c.type === 'websocket';
      const platformIcon = isWeb ? '🌐 Web' : '💻 TCP';

      return `
        <div class="participant-list-item">
          <div class="item-left">
            <div class="item-avatar" style="background:${avatarColor};">${avatarChar}</div>
            <div class="item-info">
              <div class="item-name-row">
                <span class="item-name">${this.escapeHTML(c.username || 'Chờ JOIN')}</span>
                <span class="tile-id-badge">#${c.id}</span>
              </div>
              <div class="item-sub">${platformIcon} • ${c.address || c.ip}</div>
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-item-ctrl mute ${isMuted ? 'is-muted' : ''}" data-client-id="${c.id}" title="${isMuted ? 'Bỏ mute' : 'Tắt quyền chat'}">
              ${isMuted ? 'Bỏ Mute' : 'Mute'}
            </button>
            <button class="btn-item-ctrl dm" data-client-id="${c.id}" data-name="${this.escapeHTML(c.username)}" title="Nhắn riêng">
              Nhắn
            </button>
            <button class="btn-item-ctrl kick" data-client-id="${c.id}" data-name="${this.escapeHTML(c.username)}" title="Kick">
              Kick
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Bắt sự kiện trong Sidepanel list
    this.participantsScrollList.querySelectorAll('.btn-item-ctrl.mute').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const cid = parseInt(e.currentTarget.dataset.clientId, 10);
        this.sendCommand('ADMIN_TOGGLE_MUTE', { client_id: cid });
      });
    });

    this.participantsScrollList.querySelectorAll('.btn-item-ctrl.dm').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.selectedClientId = parseInt(e.currentTarget.dataset.clientId, 10);
        const name = e.currentTarget.dataset.name;
        if (this.dmTargetName) this.dmTargetName.textContent = name;
        this.openModal(this.modalDm);
      });
    });

    this.participantsScrollList.querySelectorAll('.btn-item-ctrl.kick').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.selectedClientId = parseInt(e.currentTarget.dataset.clientId, 10);
        const name = e.currentTarget.dataset.name;
        if (this.kickTargetName) this.kickTargetName.textContent = name;
        this.openModal(this.modalKick);
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // LIVE CHAT MONITOR STREAM
  // ─────────────────────────────────────────────────────────────────
  appendLiveChatMessage(msg) {
    if (!this.chatMessagesContainer) return;

    const hint = this.chatMessagesContainer.querySelector('.empty-chat-hint');
    if (hint) hint.remove();

    const item = document.createElement('div');
    item.style.padding = '8px 10px';
    item.style.borderRadius = '8px';
    item.style.fontSize = '0.78rem';
    item.style.lineHeight = '1.4';
    item.style.background = 'rgba(255,255,255,0.03)';
    item.style.border = '1px solid rgba(255,255,255,0.06)';

    if (msg.type === 'PRIVATE') {
      item.style.borderColor = 'rgba(168, 85, 247, 0.4)';
      item.innerHTML = `
        <div style="font-size:0.68rem; color:#C084FC; font-weight:700;">🔒 [RIÊNG] ${this.escapeHTML(msg.from_user)} ➔ ${this.escapeHTML(msg.to_user)}</div>
        <div style="color:#F8FAFC;">${this.escapeHTML(msg.content)}</div>
      `;
    } else {
      item.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
          <strong style="color:#818CF8;">${this.escapeHTML(msg.username || 'System')} <span style="font-family:var(--font-code); color:#64748B;">#${msg.client_id || ''}</span></strong>
          <span style="font-size:0.68rem; color:#64748B;">${msg.timestamp || ''}</span>
        </div>
        <div style="color:#E2E8F0;">${this.escapeHTML(msg.content || msg.message || '')}</div>
      `;
    }

    this.chatMessagesContainer.appendChild(item);
    this.chatMessagesContainer.scrollTop = this.chatMessagesContainer.scrollHeight;
  }

  // ─────────────────────────────────────────────────────────────────
  // TERMINAL LOGS
  // ─────────────────────────────────────────────────────────────────
  renderTerminalLogs() {
    if (!this.hostTerminalLines) return;

    const filtered = this.logs.filter(entry => {
      const matchTag = this.activeTag === 'ALL' || entry.tag === this.activeTag;
      const matchSearch = !this.searchQuery || entry.message.toLowerCase().includes(this.searchQuery);
      return matchTag && matchSearch;
    });

    this.hostTerminalLines.innerHTML = filtered.map(item => this.createLogRowHTML(item)).join('');
    this.scrollTerminal();
  }

  appendTerminalLogEntry(item) {
    if (!this.hostTerminalLines) return;

    const matchTag = this.activeTag === 'ALL' || item.tag === this.activeTag;
    const matchSearch = !this.searchQuery || item.message.toLowerCase().includes(this.searchQuery);

    if (matchTag && matchSearch) {
      const row = document.createElement('div');
      row.className = 'term-row';
      row.innerHTML = this.createLogRowHTML(item);
      this.hostTerminalLines.appendChild(row);
      this.scrollTerminal();
    }
  }

  createLogRowHTML(item) {
    const tagClass = `tag-${item.tag || 'INFO'}`;
    return `
      <span class="term-time">[${item.timestamp}]</span>
      <span class="term-tag ${tagClass}">${item.tag || 'INFO'}</span>
      <span class="term-msg">${this.escapeHTML(item.message)}</span>
    `;
  }

  scrollTerminal() {
    if (this.chkAutoScroll?.checked && this.hostTerminalScroll) {
      this.hostTerminalScroll.scrollTop = this.hostTerminalScroll.scrollHeight;
    }
  }

  exportLogsToFile() {
    const textContent = this.logs.map(l => `[${l.timestamp}] [${l.tag}] ${l.message}`).join('\n');
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `meeting_host_logs_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    this.showToast('Đã tải xuống tệp nhật ký Host!', 'info');
  }

  // ─────────────────────────────────────────────────────────────────
  // NAVIGATION & THEME HELPERS
  // ─────────────────────────────────────────────────────────────────
  switchSidePanel(panelKey) {
    this.panelTabBtns.forEach(b => {
      if (b.dataset.panel === panelKey) b.classList.add('active');
      else b.classList.remove('active');
    });

    Object.keys(this.panelViews).forEach(key => {
      if (key === panelKey) this.panelViews[key]?.classList.add('active');
      else this.panelViews[key]?.classList.remove('active');
    });
  }

  applyTheme() {
    const theme = localStorage.getItem('netsphere_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('netsphere_theme', next);
  }

  applySound() {
    const isMuted = localStorage.getItem('netsphere_sound_muted') === 'true';
    this.updateSoundIcons(isMuted);
  }

  updateSoundIcons(isMuted) {
    const iconOn = document.getElementById('iconSoundOn');
    const iconOff = document.getElementById('iconSoundOff');
    if (isMuted) {
      iconOn?.classList.add('hidden');
      iconOff?.classList.remove('hidden');
    } else {
      iconOn?.classList.remove('hidden');
      iconOff?.classList.add('hidden');
    }
  }

  openModal(modal) {
    if (modal) modal.classList.remove('hidden');
  }

  closeModal(modal) {
    if (modal) modal.classList.add('hidden');
  }

  showToast(message, type = 'info') {
    if (!this.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast-item ${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'danger') icon = '❌';

    toast.innerHTML = `<span style="font-size:1.1rem;">${icon}</span><span>${this.escapeHTML(message)}</span>`;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  generateColorFromString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = Math.abs(hash % 360);
    return `hsl(${h}, 65%, 48%)`;
  }

  getInitials(name) {
    if (!name) return 'U';
    let clean = name.replace(/[\(\[][^\)\]]*[\)\]]?/g, ' ').replace(/[\(\)\[\]\{\}]/g, ' ').trim();
    const words = clean.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      const match = name.match(/[\p{L}\p{N}]/u);
      return match ? match[0].toUpperCase() : 'U';
    }
    const targetWord = words[words.length - 1];
    const letterMatch = targetWord.match(/[\p{L}\p{N}]/u);
    return letterMatch ? letterMatch[0].toUpperCase() : 'U';
  }

  escapeHTML(str) {
    return String(str || '').replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

// Khởi tạo
document.addEventListener('DOMContentLoaded', () => {
  window.meetingHost = new MeetingHostController();
});
