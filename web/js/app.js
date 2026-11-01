/**
 * App - Trình Điều Phối Chính của NetSphere Web Platform.
 * Quản lý chuyển đổi Tab, Dark/Light Theme, Toast Notifications và Khởi tạo.
 */

class NetSphereApp {
  constructor() {
    this.currentTab = 'chat';
    this.initDOM();
    this.applySavedTheme();
    this.applySavedSound();
    this.handleInitialHash();
  }

  initDOM() {
    // Navigation Tabs
    this.navBtns = document.querySelectorAll('.nav-tab-btn');
    this.viewPanels = {
      chat: document.getElementById('viewChat'),
      architecture: document.getElementById('viewArchitecture')
    };

    // Tiện ích Header
    this.btnToggleTheme = document.getElementById('btnToggleTheme');
    this.iconMoon = document.getElementById('iconMoon');
    this.iconSun = document.getElementById('iconSun');

    this.btnToggleSound = document.getElementById('btnToggleSound');
    this.iconSoundOn = document.getElementById('iconSoundOn');
    this.iconSoundOff = document.getElementById('iconSoundOff');

    this.btnToggleInspector = document.getElementById('btnToggleInspector');
    this.toastContainer = document.getElementById('toastContainer');

    this.bindEvents();
  }

  bindEvents() {
    // Chuyển đổi Tab điều hướng
    this.navBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Chuyển Theme Sáng / Tối
    if (this.btnToggleTheme) {
      this.btnToggleTheme.addEventListener('click', () => {
        this.toggleTheme();
      });
    }

    // Bật / Tắt Âm Thanh
    if (this.btnToggleSound) {
      this.btnToggleSound.addEventListener('click', () => {
        const isMuted = window.soundFX?.toggleMute();
        this.updateSoundIcons(isMuted);
        this.showToast(isMuted ? 'Đã tắt âm thanh hiệu ứng' : 'Đã bật âm thanh hiệu ứng', 'info');
      });
    }

    // Bật / Tắt Ngăn Kéo Giám Sát Gói Tin
    if (this.btnToggleInspector) {
      this.btnToggleInspector.addEventListener('click', () => {
        window.protocolManager?.toggleDrawer();
      });
    }

    // Lắng nghe thay đổi hash trên URL
    window.addEventListener('hashchange', () => {
      this.handleInitialHash();
    });
  }

  switchTab(tabName) {
    if (!this.viewPanels[tabName]) return;

    this.currentTab = tabName;

    // Cập nhật trạng thái nút tab
    this.navBtns.forEach(btn => {
      if (btn.dataset.tab === tabName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Ẩn hiện các view panel
    Object.keys(this.viewPanels).forEach(key => {
      if (key === tabName) {
        this.viewPanels[key].classList.add('active');
      } else {
        this.viewPanels[key].classList.remove('active');
      }
    });

    // Cập nhật hash trên URL mà không cuộn trang
    history.replaceState(null, null, `#${tabName}`);

    // Xóa unread nếu quay lại tab chat
    if (tabName === 'chat') {
      window.chatClient?.clearUnread();
    }
  }

  handleInitialHash() {
    const hash = location.hash.replace('#', '').toLowerCase();
    if (['chat', 'architecture'].includes(hash)) {
      this.switchTab(hash);
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // THEME (DARK / LIGHT)
  // ─────────────────────────────────────────────────────────────────
  applySavedTheme() {
    const savedTheme = localStorage.getItem('netsphere_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    this.updateThemeIcons(savedTheme);
  }

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('netsphere_theme', nextTheme);
    this.updateThemeIcons(nextTheme);
    this.showToast(`Đã chuyển sang giao diện ${nextTheme === 'dark' ? 'Tối' : 'Sáng'}`, 'info');
  }

  updateThemeIcons(theme) {
    if (theme === 'dark') {
      this.iconMoon?.classList.remove('hidden');
      this.iconSun?.classList.add('hidden');
    } else {
      this.iconMoon?.classList.add('hidden');
      this.iconSun?.classList.remove('hidden');
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // SOUND FX
  // ─────────────────────────────────────────────────────────────────
  applySavedSound() {
    const isMuted = localStorage.getItem('netsphere_sound_muted') === 'true';
    this.updateSoundIcons(isMuted);
  }

  updateSoundIcons(isMuted) {
    if (isMuted) {
      this.iconSoundOn?.classList.add('hidden');
      this.iconSoundOff?.classList.remove('hidden');
    } else {
      this.iconSoundOn?.classList.remove('hidden');
      this.iconSoundOff?.classList.add('hidden');
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // TOAST NOTIFICATIONS
  // ─────────────────────────────────────────────────────────────────
  showToast(message, type = 'info') {
    if (!this.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast-item ${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'danger') icon = '❌';

    toast.innerHTML = `
      <span style="font-size:1.1rem;">${icon}</span>
      <span>${this.escapeHTML(message)}</span>
    `;

    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  escapeHTML(str) {
    return String(str || '').replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

// Khởi chạy ứng dụng
document.addEventListener('DOMContentLoaded', () => {
  window.app = new NetSphereApp();
});
