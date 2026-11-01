/**
 * ProtocolView - Quản lý Trình Giám Sát Gói Tin (Inspector),
 * Bảng Đặc Tả Giao Thức & Bộ Mô Phỏng Luồng Gói Tin (Simulator).
 */

class ProtocolManager {
  constructor() {
    this.packets = [];
    this.maxPackets = 200;
    this.totalBytes = 0;

    // Danh mục 8 lệnh giao thức chuẩn của Seminar
    this.protocolSpecs = [
      {
        type: 'JOIN',
        direction: 'Client ➔ Server',
        payload: '{"username": "Alice"}',
        desc: 'Đăng ký phiên với Server, yêu cầu cấp Client ID và xác thực tên không trùng.',
        sample: { type: 'JOIN', data: { username: 'Alice' } }
      },
      {
        type: 'WELCOME',
        direction: 'Server ➔ Client',
        payload: '{"message": "Chào mừng...", "client_id": 1}',
        desc: 'Phản hồi chào mừng Client, gửi kèm Client ID định danh duy nhất của phiên.',
        sample: { type: 'WELCOME', data: { message: 'Chào mừng Alice (ID: #1)!', client_id: 1 } }
      },
      {
        type: 'MSG',
        direction: 'Client ⇄ Server',
        payload: '{"content": "Xin chào!", "client_id": 1, "username": "Alice", "timestamp": "20:30:00"}',
        desc: 'Gửi tin nhắn phát sóng (Broadcast) tới toàn bộ các Client trong phòng chat.',
        sample: { type: 'MSG', data: { content: 'Xin chào mọi người!', username: 'Alice', client_id: 1, timestamp: '20:30:00' } }
      },
      {
        type: 'PRIVATE',
        direction: 'Client ⇄ Server',
        payload: '{"to": "Bob", "content": "Tin mật", "from": "Alice", "is_sender": false}',
        desc: 'Tin nhắn riêng tư (Whisper/PM) giữa 2 Client cụ thể, không phát ra phòng chung.',
        sample: { type: 'PRIVATE', data: { from: 'Alice', to: 'Bob', content: 'Gặp nhau sau nhé', timestamp: '20:30:15', is_sender: false } }
      },
      {
        type: 'ONLINE_LIST',
        direction: 'Server ➔ Client',
        payload: '{"users": ["Alice", "Bob", "Charlie"]}',
        desc: 'Đồng bộ danh sách người dùng đang trực tuyến sau mỗi sự kiện Join/Leave.',
        sample: { type: 'ONLINE_LIST', data: { users: ['Alice', 'Bob', 'Server_Admin'] } }
      },
      {
        type: 'SYSTEM',
        direction: 'Server ➔ Client',
        payload: '{"message": "\'Bob\' đã tham gia phòng chat."}',
        desc: 'Thông báo sự kiện hệ thống (kết nối, rời phòng, kick, hoặc thông báo của Admin).',
        sample: { type: 'SYSTEM', data: { message: "'Bob' (ID: #2) đã tham gia phòng chat." } }
      },
      {
        type: 'ERROR',
        direction: 'Server ➔ Client',
        payload: '{"message": "Tên \'Alice\' đã được sử dụng."}',
        desc: 'Thông báo lỗi khi vi phạm quy tắc (trùng tên, chưa JOIN, gửi sai cú pháp).',
        sample: { type: 'ERROR', data: { message: "Tên đã tồn tại trên Server." } }
      },
      {
        type: 'QUIT',
        direction: 'Client ➔ Server',
        payload: '{}',
        desc: 'Client chủ động gửi tín hiệu rời phòng để Server đóng socket an toàn.',
        sample: { type: 'QUIT', data: {} }
      }
    ];

    this.initDOM();
    this.renderProtocolSpecsTable();
    this.bindSimulator();
  }

  initDOM() {
    this.drawer = document.getElementById('inspectorDrawer');
    this.backdrop = document.getElementById('drawerBackdrop');
    this.packetListEl = document.getElementById('packetStreamList');
    this.drawerPacketCountEl = document.getElementById('drawerPacketCount');
    this.drawerPacketBytesEl = document.getElementById('drawerPacketBytes');
    this.headerPacketCountEl = document.getElementById('headerPacketCount');
    this.emptyHintEl = document.getElementById('emptyPacketsHint');

    const btnClose = document.getElementById('btnCloseInspector');
    const btnClear = document.getElementById('btnClearPackets');

    if (btnClose) btnClose.addEventListener('click', () => this.closeDrawer());
    if (this.backdrop) this.backdrop.addEventListener('click', () => this.closeDrawer());
    if (btnClear) btnClear.addEventListener('click', () => this.clearPackets());
  }

  toggleDrawer() {
    if (!this.drawer) return;
    this.drawer.classList.toggle('open');
    if (this.backdrop) this.backdrop.classList.toggle('active');
  }

  openDrawer() {
    if (!this.drawer) return;
    this.drawer.classList.add('open');
    if (this.backdrop) this.backdrop.classList.add('active');
  }

  closeDrawer() {
    if (!this.drawer) return;
    this.drawer.classList.remove('open');
    if (this.backdrop) this.backdrop.classList.remove('active');
  }

  /**
   * Ghi nhận một gói tin mạng thời gian thực vào Inspector.
   * @param {'OUT'|'IN'} direction - Chiều gửi đi hoặc nhận về
   * @param {Object} rawPacket - Đối tượng gói tin JSON
   */
  recordPacket(direction, rawPacket) {
    const jsonString = JSON.stringify(rawPacket, null, 2);
    const byteSize = new TextEncoder().encode(JSON.stringify(rawPacket)).length;
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');

    const packetItem = {
      id: Date.now() + Math.random(),
      direction,
      opcode: rawPacket.type || 'RAW',
      timestamp: timeStr,
      byteSize,
      jsonString,
      raw: rawPacket
    };

    this.packets.unshift(packetItem);
    if (this.packets.length > this.maxPackets) {
      this.packets.pop();
    }

    this.totalBytes += byteSize;
    this.updateCounters();
    this.renderPacketRow(packetItem);
  }

  updateCounters() {
    const count = this.packets.length;
    if (this.drawerPacketCountEl) this.drawerPacketCountEl.textContent = count;
    if (this.headerPacketCountEl) this.headerPacketCountEl.textContent = count;

    let bytesStr = this.totalBytes + ' B';
    if (this.totalBytes > 1024) {
      bytesStr = (this.totalBytes / 1024).toFixed(1) + ' KB';
    }
    if (this.drawerPacketBytesEl) this.drawerPacketBytesEl.textContent = bytesStr;
  }

  renderPacketRow(packet) {
    if (this.emptyHintEl) {
      this.emptyHintEl.style.display = 'none';
    }

    const card = document.createElement('div');
    card.className = 'packet-card';

    const dirClass = packet.direction.toLowerCase();
    const dirLabel = packet.direction === 'OUT' ? 'GỬI ĐI (OUT)' : 'NHẬN VỀ (IN)';

    card.innerHTML = `
      <div class="packet-header-line">
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="packet-direction-badge ${dirClass}">${dirLabel}</span>
          <span class="packet-opcode">${packet.opcode}</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--text-muted);">${packet.byteSize} bytes</span>
          <span class="packet-time">${packet.timestamp}</span>
        </div>
      </div>
      <div class="packet-body-json">${this.escapeHTML(packet.jsonString)}</div>
    `;

    if (this.packetListEl) {
      this.packetListEl.insertBefore(card, this.packetListEl.firstChild);
    }
  }

  clearPackets() {
    this.packets = [];
    this.totalBytes = 0;
    this.updateCounters();
    if (this.packetListEl) {
      this.packetListEl.innerHTML = `
        <div class="empty-packets-hint" id="emptyPacketsHint">
          Chưa có gói tin nào được ghi nhận. Hãy gửi hoặc nhận tin nhắn để theo dõi luồng giao thức!
        </div>
      `;
      this.emptyHintEl = document.getElementById('emptyPacketsHint');
    }
  }

  escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }

  // ─────────────────────────────────────────────────────────────────
  // BẢNG ĐẶC TẢ GIAO THỨC & BỘ MÔ PHỎNG (TAB 3: ARCHITECTURE)
  // ─────────────────────────────────────────────────────────────────
  renderProtocolSpecsTable() {
    const tbody = document.getElementById('tbodyProtocolSpecs');
    if (!tbody) return;

    tbody.innerHTML = this.protocolSpecs.map(spec => `
      <tr>
        <td><strong style="font-family:var(--font-code); color:var(--primary); font-size:0.88rem;">${spec.type}</strong></td>
        <td><span style="font-size:0.75rem; color:var(--text-secondary);">${spec.direction}</span></td>
        <td><code style="font-family:var(--font-code); font-size:0.72rem; color:#A5B4FC; word-break:break-all;">${this.escapeHTML(spec.payload)}</code></td>
        <td style="font-size:0.8rem; color:var(--text-secondary);">${spec.desc}</td>
        <td>
          <button class="btn-sm-action btn-test-spec" data-spec="${spec.type}">
            Mô phỏng
          </button>
        </td>
      </tr>
    `).join('');

    // Bắt sự kiện nút Mô phỏng trong bảng
    tbody.querySelectorAll('.btn-test-spec').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const type = e.currentTarget.dataset.spec;
        this.runSimulation(type);
      });
    });
  }

  bindSimulator() {
    document.querySelectorAll('.btn-sim-action').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const simType = e.currentTarget.dataset.sim;
        this.runSimulation(simType);
      });
    });
  }

  /**
   * Chạy mô phỏng từng bước của chu trình gói tin.
   */
  runSimulation(simType) {
    const spec = this.protocolSpecs.find(s => s.type === simType) || this.protocolSpecs[0];

    const box1 = document.getElementById('simBox1');
    const box2 = document.getElementById('simBox2');
    const box3 = document.getElementById('simBox3');

    if (!box1 || !box2 || !box3) return;

    // Reset boxes
    box1.className = 'step-box';
    box2.className = 'step-box';
    box3.className = 'step-box';

    box1.textContent = 'Đang đóng gói JSON...';
    box2.textContent = 'Chờ truyền qua Socket...';
    box3.textContent = 'Chờ xử lý...';

    // Bước 1: Client đóng gói
    setTimeout(() => {
      box1.classList.add('active-flow');
      box1.textContent = JSON.stringify(spec.sample, null, 2);
      window.soundFX?.playSent();
    }, 100);

    // Bước 2: Server tiếp nhận & xử lý
    setTimeout(() => {
      box1.classList.remove('active-flow');
      box2.classList.add('active-flow');
      box2.textContent = `Server nhận qua Socket:\n- Loại lệnh: ${spec.type}\n- Kiểm tra JSON: Hợp lệ\n- Gán ClientSession ID #1\n- Định tuyến: Đa luồng (Async)`;
    }, 1200);

    // Bước 3: Phản hồi hoặc phát sóng tới các Client
    setTimeout(() => {
      box2.classList.remove('active-flow');
      box3.classList.add('active-flow');
      box3.textContent = `Client nhận qua Web/TCP:\n- Giải mã JSON-Lines (UTF-8)\n- Cập nhật giao diện / Âm thanh\n- Trạng thái: Thành công!`;
      window.soundFX?.playReceived();
    }, 2400);

    // Hoàn tất
    setTimeout(() => {
      box3.classList.remove('active-flow');
    }, 4500);
  }
}

// Khởi tạo instance toàn cục
window.protocolManager = new ProtocolManager();
