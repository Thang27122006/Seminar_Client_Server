/**
 * AuthManager - Hệ Thống Xác Thực & Quản Lý Phiên Người Dùng (Zoom & Google Meet Style)
 * Quản lý Token, Đăng Ký, Đăng Nhập, Đăng Xuất và Lưu Phiên Trong LocalStorage.
 */

class AuthManager {
  constructor() {
    this.tokenKey = 'netsphere_auth_token';
    this.userKey = 'netsphere_user_info';
    this.currentUser = this.getSavedUser();
    this.token = localStorage.getItem(this.tokenKey) || '';
  }

  getSavedUser() {
    try {
      const raw = localStorage.getItem(this.userKey);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  getToken() {
    return this.token || localStorage.getItem(this.tokenKey) || '';
  }

  getUser() {
    return this.currentUser;
  }

  isAuthenticated() {
    return !!(this.getToken() && this.currentUser);
  }

  async checkAuth() {
    const token = this.getToken();
    if (!token) {
      this.currentUser = null;
      return null;
    }

    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.authenticated && data.user) {
        this.currentUser = data.user;
        localStorage.setItem(this.userKey, JSON.stringify(data.user));
        return data.user;
      } else {
        this.logout();
        return null;
      }
    } catch (e) {
      console.warn("Lỗi kiểm tra phiên làm việc:", e);
      return this.currentUser;
    }
  }

  async login(username, password) {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.success) {
        this.token = data.token;
        this.currentUser = data.user;
        localStorage.setItem(this.tokenKey, data.token);
        localStorage.setItem(this.userKey, JSON.stringify(data.user));
      }
      return data;
    } catch (e) {
      return { success: false, message: "Lỗi kết nối máy chủ!" };
    }
  }

  async register(username, password, fullname, email) {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, fullname, email })
      });
      const data = await res.json();
      if (data.success) {
        this.token = data.token;
        this.currentUser = data.user;
        localStorage.setItem(this.tokenKey, data.token);
        localStorage.setItem(this.userKey, JSON.stringify(data.user));
      }
      return data;
    } catch (e) {
      return { success: false, message: "Lỗi kết nối máy chủ!" };
    }
  }

  async logout() {
    const token = this.getToken();
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ token })
        });
      } catch (e) {}
    }

    this.token = '';
    this.currentUser = null;
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }
}

window.authManager = new AuthManager();
