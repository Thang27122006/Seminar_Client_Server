/**
 * Home - Trình Điều Phối Trang Chủ Google Meet & Zoom Home Lobby
 * Quản lý Đồng Hồ Trực Tiếp, Tạo Cuộc Họp Mới, Nhập Mã Phòng, Đăng Nhập/Đăng Ký
 */

class NetSphereHome {
  constructor() {
    this.initDOM();
    this.initClock();
    this.initAuthUI();
    this.initCarousel();
    this.bindEvents();
    this.loadActiveRooms();
    
    // Tự động làm mới danh sách phòng họp mỗi 4 giây
    setInterval(() => this.loadActiveRooms(), 4000);
  }

  initCarousel() {
    this.slides = document.querySelectorAll('.gm-carousel-slide');
    this.dots = document.querySelectorAll('.gm-page-dot');
    this.currentSlideIndex = 0;

    if (!this.slides.length) return;

    this.showSlide = (index) => {
      this.currentSlideIndex = (index + this.slides.length) % this.slides.length;
      this.slides.forEach((s, idx) => {
        s.classList.toggle('active', idx === this.currentSlideIndex);
      });
      this.dots.forEach((d, idx) => {
        d.classList.toggle('active', idx === this.currentSlideIndex);
      });
    };

    this.dots.forEach((dot, idx) => {
      dot.addEventListener('click', () => {
        this.showSlide(idx);
      });
    });

    // Tự động chuyển slide sau mỗi 6 giây
    setInterval(() => {
      this.showSlide(this.currentSlideIndex + 1);
    }, 6000);
  }

  initDOM() {
    // Header & Clock
    this.liveClockEl = document.getElementById('homeLiveClock');
    this.userAuthContainer = document.getElementById('userAuthContainer');
    this.btnToggleTheme = document.getElementById('btnToggleTheme');

    // Hero Actions
    this.btnNewMeeting = document.getElementById('btnNewMeeting');
    this.meetingDropdown = document.getElementById('meetingDropdown');
    this.optCreateForLater = document.getElementById('optCreateForLater');
    this.optStartInstant = document.getElementById('optStartInstant');

    // Input Code & Join
    this.inputMeetCode = document.getElementById('inputMeetCode');
    this.btnJoinMeeting = document.getElementById('btnJoinMeeting');
    this.sampleCodePills = document.querySelectorAll('.sample-code-pill');

    // Active Rooms List
    this.activeRoomsList = document.getElementById('activeRoomsList');

    // Auth Modal
    this.modalAuth = document.getElementById('modalAuth');
    this.btnCloseAuth = document.getElementById('btnCloseAuth');
    this.tabLogin = document.getElementById('tabLogin');
    this.tabRegister = document.getElementById('tabRegister');
    this.formLogin = document.getElementById('formLogin');
    this.formRegister = document.getElementById('formRegister');
    this.loginAlert = document.getElementById('loginAlert');
    this.registerAlert = document.getElementById('registerAlert');

    // Meeting Ready Modal
    this.modalMeetingReady = document.getElementById('modalMeetingReady');
    this.btnCloseReadyModal = document.getElementById('btnCloseReadyModal');
    this.inputReadyLink = document.getElementById('inputReadyLink');
    this.btnCopyReadyLink = document.getElementById('btnCopyReadyLink');
    this.btnJoinReadyRoom = document.getElementById('btnJoinReadyRoom');

    // Toast Container
    this.toastContainer = document.getElementById('toastContainer');
  }

  initClock() {
    const updateTime = () => {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');

      const daysOfWeek = ['CN', 'Th 2', 'Th 3', 'Th 4', 'Th 5', 'Th 6', 'Th 7'];
      const dayName = daysOfWeek[now.getDay()];
      const day = now.getDate();
      const month = now.getMonth() + 1;

      if (this.liveClockEl) {
        this.liveClockEl.textContent = `${hours}:${minutes} • ${dayName}, ${day} thg ${month}`;
      }
    };
    updateTime();
    setInterval(updateTime, 1000);
  }

  async initAuthUI() {
    await window.authManager?.checkAuth();
    this.renderUserBadge();
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

  renderUserBadge() {
    if (!this.userAuthContainer) return;
    const user = window.authManager?.getUser();

    if (user) {
      const initial = this.getInitials(user.fullname || user.username);
      const color = user.avatar_color || '#1a73e8';

      this.userAuthContainer.innerHTML = `
        <div class="user-profile-pill" id="btnUserMenu" title="Tài khoản: ${user.fullname} (@${user.username})">
          <div class="user-avatar-circle" style="background: ${color};">${initial}</div>
          <span class="user-name-text">${user.fullname || user.username}</span>
          <button class="btn-icon-xs" id="btnLogoutAction" title="Đăng xuất" style="background:transparent; border:none; color:var(--text-muted); cursor:pointer;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      `;

      document.getElementById('btnLogoutAction')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        await window.authManager?.logout();
        this.renderUserBadge();
        this.showToast("Đã đăng xuất tài khoản.", "info");
      });
    } else {
      this.userAuthContainer.innerHTML = `
        <button class="btn-gr-auth btn-gr-auth-login" id="btnOpenLogin">Đăng nhập</button>
        <button class="btn-gr-auth btn-gr-auth-register" id="btnOpenRegister">Đăng ký</button>
      `;

      document.getElementById('btnOpenLogin')?.addEventListener('click', () => {
        this.openAuthModal('login');
      });
      document.getElementById('btnOpenRegister')?.addEventListener('click', () => {
        this.openAuthModal('register');
      });
    }
  }

  bindEvents() {
    const container = document.getElementById('newMeetingContainer');

    // Tự động reset trạng thái force-hidden khi chuột rời khỏi vùng nút
    container?.addEventListener('mouseleave', () => {
      this.meetingDropdown?.classList.remove('force-hidden', 'show');
    });

    container?.addEventListener('mouseenter', () => {
      this.meetingDropdown?.classList.remove('force-hidden');
    });

    // Đóng dropdown khi click ra ngoài
    document.addEventListener('click', (e) => {
      if (!container?.contains(e.target)) {
        this.meetingDropdown?.classList.remove('show');
        this.meetingDropdown?.classList.add('force-hidden');
      }
    });

    // Toggle Dropdown Cuộc Họp Mới khi click
    this.btnNewMeeting?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.meetingDropdown?.classList.remove('force-hidden');
      this.meetingDropdown?.classList.toggle('show');
    });

    // Tùy chọn 1: Tạo cuộc họp để dùng sau (Get link to share)
    this.optCreateForLater?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.meetingDropdown?.classList.remove('show');
      this.meetingDropdown?.classList.add('force-hidden');
      this.handleCreateRoom(false);
    });

    // Tùy chọn 2: Bắt đầu cuộc họp tức thì
    this.optStartInstant?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.meetingDropdown?.classList.remove('show');
      this.meetingDropdown?.classList.add('force-hidden');
      this.handleCreateRoom(true);
    });

    // Lắng nghe gõ mã cuộc họp
    this.inputMeetCode?.addEventListener('input', (e) => {
      const val = e.target.value.trim();
      if (val.length > 0) {
        this.btnJoinMeeting?.classList.add('active');
        this.btnJoinMeeting.disabled = false;
      } else {
        this.btnJoinMeeting?.classList.remove('active');
        this.btnJoinMeeting.disabled = true;
      }
    });

    // Tham gia khi Enter
    this.inputMeetCode?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        this.handleJoinMeeting();
      }
    });

    // Nút Tham gia
    this.btnJoinMeeting?.addEventListener('click', () => {
      this.handleJoinMeeting();
    });

    // Gợi ý mã mẫu
    this.sampleCodePills.forEach(pill => {
      pill.addEventListener('click', () => {
        const code = pill.dataset.code || pill.textContent.trim();
        if (this.inputMeetCode) {
          this.inputMeetCode.value = code;
          this.btnJoinMeeting?.classList.add('active');
          this.btnJoinMeeting.disabled = false;
        }
        this.handleJoinMeeting();
      });
    });

    // Đổi Theme
    this.btnToggleTheme?.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('netsphere_theme', next);
    });

    // Modal Auth tabs
    this.tabLogin?.addEventListener('click', () => this.switchAuthTab('login'));
    this.tabRegister?.addEventListener('click', () => this.switchAuthTab('register'));
    this.btnCloseAuth?.addEventListener('click', () => this.closeAuthModal());
    this.modalAuth?.addEventListener('click', (e) => {
      if (e.target === this.modalAuth) this.closeAuthModal();
    });

    // Submit Đăng Nhập
    this.formLogin?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('loginUsername').value.trim();
      const password = document.getElementById('loginPassword').value.trim();

      const res = await window.authManager.login(username, password);
      if (res.success) {
        this.closeAuthModal();
        this.renderUserBadge();
        this.showToast(`Chào mừng ${res.user.fullname}! Đăng nhập thành công.`, 'success');
      } else {
        this.showAuthError(this.loginAlert, res.message);
      }
    });

    // Submit Đăng Ký
    this.formRegister?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fullname = document.getElementById('regFullname').value.trim();
      const username = document.getElementById('regUsername').value.trim();
      const email = document.getElementById('regEmail').value.trim();
      const password = document.getElementById('regPassword').value.trim();
      const confirmPwd = document.getElementById('regConfirmPassword').value.trim();

      if (password !== confirmPwd) {
        this.showAuthError(this.registerAlert, "Mật khẩu xác nhận không khớp!");
        return;
      }

      const res = await window.authManager.register(username, password, fullname, email);
      if (res.success) {
        this.closeAuthModal();
        this.renderUserBadge();
        this.showToast(`Tạo tài khoản thành công! Xin chào ${res.user.fullname}`, 'success');
      } else {
        this.showAuthError(this.registerAlert, res.message);
      }
    });

    // Modal Meeting Ready
    this.btnCloseReadyModal?.addEventListener('click', () => {
      this.modalMeetingReady?.classList.add('hidden');
    });
    this.btnCopyReadyLink?.addEventListener('click', () => {
      if (this.inputReadyLink) {
        navigator.clipboard.writeText(this.inputReadyLink.value);
        this.showToast("Đã sao chép liên kết phòng họp!", "success");
      }
    });
  }

  cleanMeetingCode(rawInput) {
    let code = rawInput.trim();
    // Nếu người dùng dán link URL đầy đủ (ví dụ: http://localhost:8080/room?code=abc-defg-hij)
    if (code.includes('?code=') || code.includes('&code=')) {
      try {
        const url = new URL(code.startsWith('http') ? code : `http://localhost/${code}`);
        code = url.searchParams.get('code') || code;
      } catch (e) {}
    } else if (code.includes('/room/')) {
      code = code.split('/room/').pop();
    }
    return code.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase();
  }

  handleJoinMeeting() {
    const raw = this.inputMeetCode?.value || '';
    const code = this.cleanMeetingCode(raw);
    if (!code) {
      this.showToast("Vui lòng nhập mã phòng họp hoặc đường liên kết hợp lệ!", "warning");
      return;
    }

    // Chuyển hướng vào phòng họp
    window.location.href = `/room?code=${encodeURIComponent(code)}`;
  }

  async handleCreateRoom(instant = false) {
    const user = window.authManager?.getUser();
    const token = window.authManager?.getToken();

    const title = user ? `Cuộc họp của ${user.fullname}` : `Cuộc họp seminar ${new Date().toLocaleTimeString('vi-VN')}`;

    try {
      const res = await fetch('/api/rooms/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          title: title,
          token: token
        })
      });

      const data = await res.json();
      if (data.success && data.room) {
        const roomCode = data.room.code;
        const meetingUrl = `${window.location.origin}/room?code=${roomCode}`;

        if (instant) {
          // Bắt đầu ngay: vào thẳng phòng họp
          window.location.href = `/room?code=${roomCode}`;
        } else {
          // Hiển thị modal sao chép liên kết để dùng sau
          if (this.inputReadyLink) {
            this.inputReadyLink.value = meetingUrl;
          }
          if (this.btnJoinReadyRoom) {
            this.btnJoinReadyRoom.onclick = () => {
              window.location.href = `/room?code=${roomCode}`;
            };
          }
          this.modalMeetingReady?.classList.remove('hidden');
        }
      } else {
        this.showToast("Không thể tạo phòng họp. Vui lòng thử lại!", "danger");
      }
    } catch (e) {
      this.showToast("Lỗi kết nối máy chủ khi tạo phòng!", "danger");
    }
  }

  async loadActiveRooms() {
    if (!this.activeRoomsList) return;

    try {
      const res = await fetch('/api/rooms');
      const rooms = await res.json();

      if (!rooms || rooms.length === 0) {
        this.activeRoomsList.innerHTML = `
          <div class="text-center" style="padding: 20px; color: var(--text-muted); font-size: 0.9rem;">
            Chưa có phòng họp nào. Hãy bấm <strong>Cuộc họp mới</strong> để bắt đầu!
          </div>
        `;
        return;
      }

      this.activeRoomsList.innerHTML = rooms.map(room => `
        <div class="gm-room-item">
          <div>
            <div style="font-weight:500; font-size:0.95rem; color:var(--gm-text-primary);">${room.title}</div>
            <div style="font-size:0.8rem; color:var(--gm-text-secondary); margin-top:3px;">
              <span class="gm-room-code-badge">${room.code}</span>
              <span>&bull;</span>
              <span>Host: ${room.host_fullname || room.host_username}</span>
              <span>&bull;</span>
              <span>👥 ${room.online_count} online</span>
            </div>
          </div>
          <a href="/room?code=${encodeURIComponent(room.code)}" class="btn-join-google active" style="text-decoration:none; height:32px; display:inline-flex; align-items:center; padding:0 12px; font-size:0.85rem;">
            Tham gia
          </a>
        </div>
      `).join('');

    } catch (e) {
      console.warn("Lỗi tải danh sách phòng active:", e);
    }
  }

  openAuthModal(tab = 'login') {
    this.switchAuthTab(tab);
    this.modalAuth?.classList.remove('hidden');
    this.hideAuthErrors();
  }

  closeAuthModal() {
    this.modalAuth?.classList.add('hidden');
    this.hideAuthErrors();
  }

  switchAuthTab(tab) {
    if (tab === 'login') {
      this.tabLogin?.classList.add('active');
      this.tabRegister?.classList.remove('active');
      this.formLogin?.classList.remove('hidden');
      this.formRegister?.classList.add('hidden');
    } else {
      this.tabRegister?.classList.add('active');
      this.tabLogin?.classList.remove('active');
      this.formRegister?.classList.remove('hidden');
      this.formLogin?.classList.add('hidden');
    }
    this.hideAuthErrors();
  }

  showAuthError(container, message) {
    if (container) {
      container.textContent = message;
      container.classList.remove('hidden');
    }
  }

  hideAuthErrors() {
    this.loginAlert?.classList.add('hidden');
    this.registerAlert?.classList.add('hidden');
  }

  showToast(message, type = 'info') {
    if (!this.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.textContent = message;
    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3500);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.netsphereHome = new NetSphereHome();
});
