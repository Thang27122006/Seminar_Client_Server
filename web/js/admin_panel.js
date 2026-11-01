/**
 * AdminPanel - Điều khiển & Giám Sát Server Quản Trị Thời Gian Thực.
 * Tương ứng và nâng cấp từ server/gui.py (Tkinter GUI).
 */

class AdminDashboard {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.logs = [];
    this.activeFilterTag = 'ALL';
    this.searchQuery = '';
    this.clients = [];
    this.stats = {};
    this.selectedClientId = null;

    this.initDOM();
  }

  initDOM() {
    // KPI elements
    this.kpiStatusEl = document.getElementById('kpiServerStatus');
    this.kpiUptimeEl = document.getElementById('kpiUptime');
    this.kpiOnlineClientsEl = document.getElementById('kpiOnlineClients');
    this.kpiWebClientsEl = document.getElementById('kpiWebClients');
    this.kpiTcpClientsEl = document.getElementById('kpiTcpClients');
    this.kpiTotalMessagesEl = document.getElementById('kpiTotalMessages');
    this.kpiTrafficBytesEl = document.getElementById('kpiTrafficBytes');
    this.kpiTotalSessionsEl = document.getElementById('kpiTotalSessions');

    // Table elements
    this.tbodyClients = document.getElementById('tbodyAdminClients');
    this.btnRefreshClients = document.getElementById('btnRefreshAdminClients');

    // Broadcast Form
    this.formBroadcast = document.getElementById('formAdminBroadcast');
    this.inputBroadcastText = document.getElementById('inputAdminBroadcastText');

    // Terminal elements
    this.terminalLinesEl = document.getElementById('terminalLines');
    this.terminalScrollArea = document.getElementById('terminalScrollArea');
    this.logFilterBar = document.getElementById('logFilterBar');
    this.inputSearchLog = document.getElementById('inputSearchLog');
    this.chkAutoScroll = document.getElementById('chkAutoScrollLogs');
    this.btnClearLogs = document.getElementById('btnClearAdminLogs');
    this.btnExportLogs = document.getElementById('btnExportAdminLogs');

    // Modals
    this.modalKick = document.getElementById('modalKick');
    this.kickTargetNameEl = document.getElementById('kickTargetName');
    this.inputKickReason = document.getElementById('inputKickReason');
    this.btnConfirmKick = document.getElementById('btnConfirmKick');

    this.modalAdminDm = document.getElementById('modalAdminDm');
    this.adminDmTargetNameEl = document.getElementById('adminDmTargetName');
    this.inputAdminDmText = document.getElementById('inputAdminDmText');
    this.btnConfirmAdminDm = document.getElementById('btnConfirmAdminDm');

    this.bindEvents();
    this.connectAdminWS();
  }

  bindEvents() {
    // Làm mới danh sách client
    if (this.btnRefreshClients) {
      this.btnRefreshClients.addEventListener('click', () => {
        this.fetchClientsViaHTTP();
      });
    }

    // Gửi thông báo toàn hệ thống
    if (this.formBroadcast) {
      this.formBroadcast.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = (this.inputBroadcastText?.value || '').trim();
        if (!text) return;
        this.sendCommand('ADMIN_BROADCAST', { message: text });
        this.inputBroadcastText.value = '';
        window.app?.showToast('Đã phát thông báo toàn hệ thống!', 'success');
      });
    }

    // Bộ lọc thẻ log
    if (this.logFilterBar) {
      this.logFilterBar.querySelectorAll('.filter-chip').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.logFilterBar.querySelectorAll('.filter-chip').forEach(b => b.classList.remove('active'));
          e.currentTarget.classList.add('active');
          this.activeFilterTag = e.currentTarget.dataset.tag || 'ALL';
          this.renderLogs();
        });
      });
    }

    // Tìm kiếm trong log
    if (this.inputSearchLog) {
      this.inputSearchLog.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.renderLogs();
      });
    }

    // Xóa log
    if (this.btnClearLogs) {
      this.btnClearLogs.addEventListener('click', () => {
        this.logs = [];
        this.renderLogs();
        this.sendCommand('ADMIN_CLEAR_LOGS', {});
      });
    }

    // Xuất / Tải log file
    if (this.btnExportLogs) {
      this.btnExportLogs.addEventListener('click', () => {
        this.exportLogsToFile();
      });
    }

    // Xử lý xác nhận Kick modal
    if (this.btnConfirmKick) {
      this.btnConfirmKick.addEventListener('click', () => {
        if (!this.selectedClientId) return;
        const reason = this.inputKickReason?.value.trim() || 'Quản trị viên ngắt kết nối.';
        this.sendCommand('ADMIN_KICK', {
          client_id: this.selectedClientId,
          reason
        });
        this.closeModal(this.modalKick);
        window.app?.showToast(`Đã gửi lệnh Kick Client #${this.selectedClientId}`, 'warning');
      });
    }

    // Xử lý xác nhận Admin DM modal
    if (this.btnConfirmAdminDm) {
      this.btnConfirmAdminDm.addEventListener('click', () => {
        if (!this.selectedClientId) return;
        const msg = (this.inputAdminDmText?.value || '').trim();
        if (!msg) return;
        this.sendCommand('ADMIN_DM', {
          client_id: this.selectedClientId,
          message: msg
        });
        this.inputAdminDmText.value = '';
        this.closeModal(this.modalAdminDm);
        window.app?.showToast(`Đã gửi tin nhắn riêng tới Client #${this.selectedClientId}`, 'success');
      });
    }

    // Đóng modal bằng các nút có data-close-modal
    document.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const modalId = e.currentTarget.dataset.closeModal;
        const modal = document.getElementById(modalId);
        if (modal) this.closeModal(modal);
      });
    });
  }

  connectAdminWS() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${location.host}/ws/admin`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        if (this.kpiStatusEl) {
          this.kpiStatusEl.textContent = 'ĐANG HOẠT ĐỘNG';
          this.kpiStatusEl.className = 'kpi-value text-success';
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleAdminEvent(payload.event, payload.data);
        } catch (_) {}
      };

      this.ws.onclose = () => {
        if (this.kpiStatusEl) {
          this.kpiStatusEl.textContent = 'MẤT KẾT NỐI';
          this.kpiStatusEl.className = 'kpi-value text-amber';
        }
        // Tự động kết nối lại sau 2.5 giây
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => this.connectAdminWS(), 2500);
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch (_) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.connectAdminWS(), 3000);
    }
  }

  sendCommand(type, data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }

  handleAdminEvent(event, data) {
    if (event === 'INIT') {
      this.updateStats(data.stats);
      this.updateClientsList(data.clients);
      if (Array.isArray(data.logs)) {
        this.logs = data.logs;
        this.renderLogs();
      }
    } else if (event === 'STATS_UPDATE') {
      this.updateStats(data);
    } else if (event === 'CLIENTS_UPDATE') {
      this.updateClientsList(data);
    } else if (event === 'CLIENT_CONNECT' || event === 'CLIENT_JOIN' || event === 'CLIENT_LEAVE') {
      // Cập nhật lại danh sách client
      this.fetchClientsViaHTTP();
    } else if (event === 'LOG') {
      this.logs.push(data);
      if (this.logs.length > 500) this.logs.shift();
      this.appendLogEntry(data);
    } else if (event === 'LOGS_CLEARED') {
      this.logs = [];
      this.renderLogs();
    }
  }

  async fetchClientsViaHTTP() {
    try {
      const res = await fetch('/api/clients');
      if (res.ok) {
        const clients = await res.json();
        this.updateClientsList(clients);
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

    if (this.kpiUptimeEl) this.kpiUptimeEl.textContent = stats.uptime_str || '00:00:00';
    if (this.kpiOnlineClientsEl) this.kpiOnlineClientsEl.textContent = stats.online_total || 0;
    if (this.kpiWebClientsEl) this.kpiWebClientsEl.textContent = stats.online_ws || 0;
    if (this.kpiTcpClientsEl) this.kpiTcpClientsEl.textContent = stats.online_tcp || 0;
    if (this.kpiTotalMessagesEl) this.kpiTotalMessagesEl.textContent = stats.total_messages || 0;
    if (this.kpiTotalSessionsEl) this.kpiTotalSessionsEl.textContent = stats.total_connections || 0;

    if (this.kpiTrafficBytesEl) {
      const b = stats.bytes_transferred || 0;
      if (b < 1024) {
        this.kpiTrafficBytesEl.textContent = b + ' B';
      } else if (b < 1024 * 1024) {
        this.kpiTrafficBytesEl.textContent = (b / 1024).toFixed(1) + ' KB';
      } else {
        this.kpiTrafficBytesEl.textContent = (b / (1024 * 1024)).toFixed(2) + ' MB';
      }
    }
  }

  updateClientsList(clients) {
    if (!Array.isArray(clients)) return;
    this.clients = clients;

    if (!this.tbodyClients) return;

    if (clients.length === 0) {
      this.tbodyClients.innerHTML = `
        <tr>
          <td colspan="8" class="text-center-muted">Chưa có Client nào kết nối tới Server.</td>
        </tr>
      `;
      return;
    }

    this.tbodyClients.innerHTML = clients.map(c => {
      const isWeb = c.type === 'websocket';
      const typeBadge = isWeb
        ? `<span class="user-platform-tag web">🌐 Web WS</span>`
        : `<span class="user-platform-tag tcp">💻 TCP Sock</span>`;

      const statusBadge = c.is_active
        ? `<span style="color:var(--success); font-weight:600;">🟢 Online</span>`
        : `<span style="color:var(--text-muted);">🔴 Đã ngắt</span>`;

      return `
        <tr>
          <td><strong style="font-family:var(--font-code); color:var(--primary);">#${c.id}</strong></td>
          <td>
            <div style="font-weight:600; color:var(--text-primary);">${this.escapeHTML(c.username || '(Chờ JOIN)')}</div>
          </td>
          <td>${typeBadge}</td>
          <td><code style="font-family:var(--font-code); font-size:0.75rem; color:var(--text-secondary);">${c.address || c.ip}</code></td>
          <td style="font-size:0.75rem; color:var(--text-muted);">${c.connected_at || '--:--'}</td>
          <td style="font-family:var(--font-code); font-size:0.75rem;">${c.msg_count || 0}</td>
          <td>${statusBadge}</td>
          <td style="text-align: center;">
            <div style="display:inline-flex; gap:6px;">
              <button class="btn-tbl-action dm" data-client-id="${c.id}" data-client-name="${this.escapeHTML(c.username || 'Client #' + c.id)}">
                💬 Nhắn
              </button>
              <button class="btn-tbl-action kick" data-client-id="${c.id}" data-client-name="${this.escapeHTML(c.username || 'Client #' + c.id)}">
                👢 Kick
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Bắt sự kiện các nút Kick & DM trên bảng
    this.tbodyClients.querySelectorAll('.btn-tbl-action.kick').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.selectedClientId = parseInt(e.currentTarget.dataset.clientId, 10);
        const name = e.currentTarget.dataset.clientName;
        if (this.kickTargetNameEl) this.kickTargetNameEl.textContent = name;
        this.openModal(this.modalKick);
      });
    });

    this.tbodyClients.querySelectorAll('.btn-tbl-action.dm').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.selectedClientId = parseInt(e.currentTarget.dataset.clientId, 10);
        const name = e.currentTarget.dataset.clientName;
        if (this.adminDmTargetNameEl) this.adminDmTargetNameEl.textContent = name;
        this.openModal(this.modalAdminDm);
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // TERMINAL LOG STREAM
  // ─────────────────────────────────────────────────────────────────
  renderLogs() {
    if (!this.terminalLinesEl) return;

    const filtered = this.logs.filter(entry => {
      const matchTag = this.activeFilterTag === 'ALL' || entry.tag === this.activeFilterTag;
      const matchSearch = !this.searchQuery || entry.message.toLowerCase().includes(this.searchQuery);
      return matchTag && matchSearch;
    });

    this.terminalLinesEl.innerHTML = filtered.map(item => this.createLogRowHTML(item)).join('');
    this.scrollToBottom();
  }

  appendLogEntry(item) {
    if (!this.terminalLinesEl) return;

    const matchTag = this.activeFilterTag === 'ALL' || item.tag === this.activeFilterTag;
    const matchSearch = !this.searchQuery || item.message.toLowerCase().includes(this.searchQuery);

    if (matchTag && matchSearch) {
      const row = document.createElement('div');
      row.className = 'term-row';
      row.innerHTML = this.createLogRowHTML(item);
      this.terminalLinesEl.appendChild(row);
      this.scrollToBottom();
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

  scrollToBottom() {
    if (this.chkAutoScroll?.checked && this.terminalScrollArea) {
      this.terminalScrollArea.scrollTop = this.terminalScrollArea.scrollHeight;
    }
  }

  exportLogsToFile() {
    const textContent = this.logs.map(l => `[${l.timestamp}] [${l.tag}] ${l.message}`).join('\n');
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `server_logs_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    window.app?.showToast('Đã tải xuống tệp nhật ký Server!', 'info');
  }

  openModal(modal) {
    if (modal) modal.classList.remove('hidden');
  }

  closeModal(modal) {
    if (modal) modal.classList.add('hidden');
  }

  escapeHTML(str) {
    return String(str || '').replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

// Khởi tạo instance toàn cục
window.adminDashboard = new AdminDashboard();
