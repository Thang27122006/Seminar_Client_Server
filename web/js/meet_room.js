/**
 * Google Meet In-Call & Green Room Engine for NetSphere
 * 100% Faithful Replica of Google Meet Experience
 * Supports: Green Room Preview, Video Grid, WebRTC Media, Screen Sharing,
 * Raise Hand with Chimes, Floating Emojis, Live Captions, In-Call Chat, Host Controls
 */

(function () {
  'use strict';

  // ─────────────────────────────────────────────────────────────────
  // STATE MANAGEMENT
  // ─────────────────────────────────────────────────────────────────
  const state = {
    roomCode: 'seminar-network-lab',
    roomTitle: 'Cuộc họp trực tuyến',
    currentUser: null,
    clientId: null,
    isHost: false,
    isJoined: false,

    // Media
    localStream: null,
    screenStream: null,
    mediaState: {
      mic: true,
      cam: true,
      screen: false,
      hand: false
    },
    audioContext: null,
    analyserNode: null,
    audioLevelInterval: null,

    // Remote Participants
    participants: new Map(), // username -> user object
    avatarColors: new Map(), // key -> { initial, color }
    peerConnections: new Map(), // key -> RTCPeerConnection
    remoteScreenStream: null,

    // UI
    captionsEnabled: false,
    activeDrawer: null, // 'people' | 'chat' | 'host' | 'info' | null
    unreadChatCount: 0,
    ws: null,
    pingInterval: null
  };

  // ─────────────────────────────────────────────────────────────────
  // DOM REFERENCES
  // ─────────────────────────────────────────────────────────────────
  const DOM = {
    // Green Room
    greenRoomContainer: document.getElementById('greenRoomContainer'),
    grVideoStream: document.getElementById('grVideoStream'),
    grAvatarPlaceholder: document.getElementById('grAvatarPlaceholder'),
    grAvatarCircle: document.getElementById('grAvatarCircle'),
    grBtnMic: document.getElementById('grBtnMic'),
    grBtnCam: document.getElementById('grBtnCam'),
    grIconMicOn: document.getElementById('grIconMicOn'),
    grIconMicOff: document.getElementById('grIconMicOff'),
    grIconCamOn: document.getElementById('grIconCamOn'),
    grIconCamOff: document.getElementById('grIconCamOff'),
    grLiveClock: document.getElementById('grLiveClock'),
    grChipAvatar: document.getElementById('grChipAvatar'),
    grChipName: document.getElementById('grChipName'),
    grRoomSummaryText: document.getElementById('grRoomSummaryText'),
    grInputUsername: document.getElementById('grInputUsername'),
    btnGrJoinNow: document.getElementById('btnGrJoinNow'),
    btnGrPresent: document.getElementById('btnGrPresent'),

    // Main Stage
    meetMainStage: document.getElementById('meetMainStage'),
    meetGridContainer: document.getElementById('meetGridContainer'),
    meetPresentationStage: document.getElementById('meetPresentationStage'),
    screenShareVideo: document.getElementById('screenShareVideo'),
    screenShareBanner: document.getElementById('screenShareBanner'),
    screenSharePresenterText: document.getElementById('screenSharePresenterText'),
    btnStopPresentation: document.getElementById('btnStopPresentation'),
    emojiFlyContainer: document.getElementById('emojiFlyContainer'),
    reactionPopup: document.getElementById('reactionPopup'),
    meetCaptionsBox: document.getElementById('meetCaptionsBox'),
    captionText: document.getElementById('captionText'),

    // Bottom Bar
    meetBottomBar: document.getElementById('meetBottomBar'),
    meetBottomTime: document.getElementById('meetBottomTime'),
    meetBottomCode: document.getElementById('meetBottomCode'),
    btnBottomCopyCode: document.getElementById('btnBottomCopyCode'),
    btnMeetMic: document.getElementById('btnMeetMic'),
    iconCallMicOn: document.getElementById('iconCallMicOn'),
    iconCallMicOff: document.getElementById('iconCallMicOff'),
    btnMeetCam: document.getElementById('btnMeetCam'),
    iconCallCamOn: document.getElementById('iconCallCamOn'),
    iconCallCamOff: document.getElementById('iconCallCamOff'),
    btnMeetCC: document.getElementById('btnMeetCC'),
    btnMeetReact: document.getElementById('btnMeetReact'),
    btnMeetShareScreen: document.getElementById('btnMeetShareScreen'),
    btnMeetHand: document.getElementById('btnMeetHand'),
    btnMeetMore: document.getElementById('btnMeetMore'),
    btnMeetEndCall: document.getElementById('btnMeetEndCall'),

    // Tool Toggles
    btnToggleInfo: document.getElementById('btnToggleInfo'),
    btnTogglePeople: document.getElementById('btnTogglePeople'),
    btnToggleChat: document.getElementById('btnToggleChat'),
    btnToggleHostControls: document.getElementById('btnToggleHostControls'),
    badgePeopleCount: document.getElementById('badgePeopleCount'),
    badgeChatCount: document.getElementById('badgeChatCount'),

    // Right Drawer
    meetSideDrawer: document.getElementById('meetSideDrawer'),
    drawerHeaderTitle: document.getElementById('drawerHeaderTitle'),
    btnCloseDrawer: document.getElementById('btnCloseDrawer'),
    tabBtnDrawerPeople: document.getElementById('tabBtnDrawerPeople'),
    tabBtnDrawerChat: document.getElementById('tabBtnDrawerChat'),
    tabBtnDrawerHost: document.getElementById('tabBtnDrawerHost'),
    panelDrawerPeople: document.getElementById('panelDrawerPeople'),
    panelDrawerChat: document.getElementById('panelDrawerChat'),
    panelDrawerHost: document.getElementById('panelDrawerHost'),
    panelDrawerInfo: document.getElementById('panelDrawerInfo'),
    drawerPeopleList: document.getElementById('drawerPeopleList'),
    peopleCountLabel: document.getElementById('peopleCountLabel'),
    btnHostMuteAll: document.getElementById('btnHostMuteAll'),
    meetChatStream: document.getElementById('meetChatStream'),
    formMeetChat: document.getElementById('formMeetChat'),
    inputMeetChat: document.getElementById('inputMeetChat'),
    drawerMeetingUrl: document.getElementById('drawerMeetingUrl'),
    btnDrawerCopyLink: document.getElementById('btnDrawerCopyLink'),

    // Host Controls toggles
    toggleHostShareScreen: document.getElementById('toggleHostShareScreen'),
    toggleHostChat: document.getElementById('toggleHostChat'),
    toggleHostMic: document.getElementById('toggleHostMic'),
    toggleHostCam: document.getElementById('toggleHostCam'),

    // Toast
    meetToast: document.getElementById('meetToast'),
    meetToastMessage: document.getElementById('meetToastMessage')
  };

  // ─────────────────────────────────────────────────────────────────
  // HELPER UTILITIES
  // ─────────────────────────────────────────────────────────────────
  function showToast(message, duration = 3000) {
    if (!DOM.meetToast) return;
    DOM.meetToastMessage.textContent = message;
    DOM.meetToast.classList.remove('hidden');
    clearTimeout(DOM.meetToast._timer);
    DOM.meetToast._timer = setTimeout(() => {
      DOM.meetToast.classList.add('hidden');
    }, duration);
  }

  const GOOGLE_MEET_PALETTE = [
    '#1a73e8', // Google Blue
    '#d93025', // Google Red
    '#1e8e3e', // Google Green
    '#f29900', // Google Yellow / Orange
    '#9334e6', // Purple
    '#00897b', // Teal
    '#e64a19', // Deep Orange
    '#3949ab', // Indigo
    '#0097a7', // Cyan
    '#d81b60', // Pink
    '#5e35b1', // Deep Purple
    '#2e7d32', // Dark Green
    '#0288d1', // Light Blue
    '#c2185b', // Ruby / Crimson
    '#7b1fa2', // Purple Dark
    '#00796b'  // Teal Dark
  ];

  function hashString(str) {
    let hash = 0;
    if (!str) return 0;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  }

  function getInitials(name) {
    if (!name) return 'U';
    // 1. Loại bỏ toàn bộ nội dung trong ngoặc đơn, ngoặc vuông và triệt tiêu mọi ký tự ngoặc
    let clean = name.replace(/[\(\[][^\)\]]*[\)\]]?/g, ' ').replace(/[\(\)\[\]\{\}]/g, ' ').trim();
    // 2. Tách từ
    const words = clean.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      const match = name.match(/[\p{L}\p{N}]/u);
      return match ? match[0].toUpperCase() : 'U';
    }
    // 3. Quy chuẩn tên tiếng Việt: lấy tên gọi chính (từ cuối cùng)
    const targetWord = words[words.length - 1];
    // 4. Chỉ lấy đúng 1 ký tự chữ cái duy nhất (loại bỏ tuyệt đối mọi ký tự ngoặc, đặc biệt)
    const letterMatch = targetWord.match(/[\p{L}\p{N}]/u);
    return letterMatch ? letterMatch[0].toUpperCase() : 'U';
  }

  function resolveAvatarColors() {
    const colorMap = new Map();
    const usedByInitial = new Map(); // initial -> Set<color>
    const allUsedColors = new Set();

    const participantsList = [];
    const localUsername = state.currentUser ? state.currentUser.username : 'local';
    const localFullname = state.currentUser ? (state.currentUser.fullname || state.currentUser.username) : 'Bạn';
    const localColor = state.currentUser ? state.currentUser.avatar_color : null;

    participantsList.push({
      key: 'local',
      username: localUsername,
      fullname: localFullname,
      avatar_color: localColor || '#1a73e8'
    });

    const remotes = Array.from(state.participants.values()).sort((a, b) =>
      (a.username || '').localeCompare(b.username || '')
    );

    remotes.forEach(u => {
      participantsList.push({
        key: u.username,
        username: u.username,
        fullname: u.fullname || u.username,
        avatar_color: u.avatar_color
      });
    });

    participantsList.forEach((user, index) => {
      const initial = getInitials(user.fullname || user.username);
      if (!usedByInitial.has(initial)) {
        usedByInitial.set(initial, new Set());
      }
      const initialUsed = usedByInitial.get(initial);

      // Điểm màu xuất phát theo mã băm hoặc avatar_color đã có
      let baseIdx = 0;
      if (user.avatar_color && GOOGLE_MEET_PALETTE.includes(user.avatar_color)) {
        baseIdx = GOOGLE_MEET_PALETTE.indexOf(user.avatar_color);
      } else {
        baseIdx = hashString(user.username || user.fullname || user.key) % GOOGLE_MEET_PALETTE.length;
      }

      let chosenColor = null;

      // Ưu tiên 1: Không trùng với người cùng chữ cái đầu VÀ chưa dùng trong phòng
      for (let offset = 0; offset < GOOGLE_MEET_PALETTE.length; offset++) {
        const candidate = GOOGLE_MEET_PALETTE[(baseIdx + offset) % GOOGLE_MEET_PALETTE.length];
        if (!initialUsed.has(candidate) && !allUsedColors.has(candidate)) {
          chosenColor = candidate;
          break;
        }
      }

      // Ưu tiên 2: Nếu đã hết màu mới trong phòng, bắt buộc KHÔNG ĐƯỢC TRÙNG với người cùng chữ cái đầu
      if (!chosenColor) {
        for (let offset = 0; offset < GOOGLE_MEET_PALETTE.length; offset++) {
          const candidate = GOOGLE_MEET_PALETTE[(baseIdx + offset) % GOOGLE_MEET_PALETTE.length];
          if (!initialUsed.has(candidate)) {
            chosenColor = candidate;
            break;
          }
        }
      }

      // Trường hợp hiếm (quá 16 người cùng chữ cái đầu): dịch bước theo vị trí
      if (!chosenColor) {
        chosenColor = GOOGLE_MEET_PALETTE[(baseIdx + index) % GOOGLE_MEET_PALETTE.length];
      }

      initialUsed.add(chosenColor);
      allUsedColors.add(chosenColor);
      colorMap.set(user.key, { initial, color: chosenColor });
    });

    state.avatarColors = colorMap;
    return colorMap;
  }

  function formatTime(date = new Date()) {
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  }

  function updateClock() {
    const timeStr = formatTime();
    if (DOM.grLiveClock) DOM.grLiveClock.textContent = timeStr;
    if (DOM.meetBottomTime) DOM.meetBottomTime.textContent = timeStr;
  }

  function parseRoomCode() {
    const params = new URLSearchParams(window.location.search);
    let code = params.get('room') || params.get('code') || '';
    code = code.trim().toLowerCase();
    if (!code) code = 'seminar-network-lab';
    state.roomCode = code;

    if (DOM.meetBottomCode) DOM.meetBottomCode.textContent = code;
    if (DOM.drawerMeetingUrl) {
      DOM.drawerMeetingUrl.textContent = `${window.location.origin}/room?code=${code}`;
    }
    document.title = `${code} - Google Meet`;
  }

  // ─────────────────────────────────────────────────────────────────
  // INITIALIZE MEDIA (WEBCAM & MIC)
  // ─────────────────────────────────────────────────────────────────
  async function initLocalMedia() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: { echoCancellation: true, noiseSuppression: true }
      });
      state.localStream = stream;
      if (DOM.grVideoStream) {
        DOM.grVideoStream.srcObject = stream;
        DOM.grVideoStream.play().catch(() => {});
      }
      DOM.grAvatarPlaceholder.style.display = 'none';
      initVoiceVolumeDetection(stream);
    } catch (err) {
      console.warn('Webcam/Mic not accessible, falling back to avatar placeholder:', err);
      state.mediaState.cam = false;
      updateCamButtonsUI(false);
      DOM.grAvatarPlaceholder.style.display = 'flex';
    }
  }

  function initVoiceVolumeDetection(stream) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      state.audioContext = new AudioCtx();
      const source = state.audioContext.createMediaStreamSource(stream);
      state.analyserNode = state.audioContext.createAnalyser();
      state.analyserNode.fftSize = 256;
      source.connect(state.analyserNode);

      const bufferLength = state.analyserNode.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      state.audioLevelInterval = setInterval(() => {
        if (!state.mediaState.mic) {
          updateSpeakingIndicator(state.currentUser ? state.currentUser.username : 'local', false);
          return;
        }
        state.analyserNode.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const isSpeaking = avg > 25; // threshold
        updateSpeakingIndicator(state.currentUser ? state.currentUser.username : 'local', isSpeaking);
      }, 100);
    } catch (e) {
      console.warn('Voice level detection setup failed:', e);
    }
  }

  function updateSpeakingIndicator(username, isSpeaking) {
    const tile = document.getElementById(`tile-${username}`);
    if (tile) {
      if (isSpeaking) {
        tile.classList.add('speaking');
      } else {
        tile.classList.remove('speaking');
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // MIC & CAM TOGGLE LOGIC
  // ─────────────────────────────────────────────────────────────────
  function toggleMic() {
    state.mediaState.mic = !state.mediaState.mic;
    if (state.localStream) {
      state.localStream.getAudioTracks().forEach(track => {
        track.enabled = state.mediaState.mic;
      });
    }
    updateMicButtonsUI(state.mediaState.mic);
    sendMediaState();
    renderLocalTile();
    showToast(state.mediaState.mic ? 'Micrô đã được bật' : 'Micrô đã được tắt');
  }

  function updateMicButtonsUI(isOn) {
    // Green Room
    if (DOM.grBtnMic) {
      DOM.grBtnMic.classList.toggle('off', !isOn);
      DOM.grIconMicOn.classList.toggle('hidden', !isOn);
      DOM.grIconMicOff.classList.toggle('hidden', isOn);
    }
    // In-Call Bar
    if (DOM.btnMeetMic) {
      DOM.btnMeetMic.classList.toggle('off', !isOn);
      DOM.iconCallMicOn.classList.toggle('hidden', !isOn);
      DOM.iconCallMicOff.classList.toggle('hidden', isOn);
    }
  }

  function toggleCam() {
    state.mediaState.cam = !state.mediaState.cam;
    if (state.localStream) {
      state.localStream.getVideoTracks().forEach(track => {
        track.enabled = state.mediaState.cam;
      });
    }
    updateCamButtonsUI(state.mediaState.cam);
    sendMediaState();
    renderLocalTile();
    showToast(state.mediaState.cam ? 'Máy ảnh đã được bật' : 'Máy ảnh đã được tắt');
  }

  function updateCamButtonsUI(isOn) {
    // Green Room
    if (DOM.grBtnCam) {
      DOM.grBtnCam.classList.toggle('off', !isOn);
      DOM.grIconCamOn.classList.toggle('hidden', !isOn);
      DOM.grIconCamOff.classList.toggle('hidden', isOn);
      DOM.grAvatarPlaceholder.style.display = isOn ? 'none' : 'flex';
      if (DOM.grVideoStream) {
        DOM.grVideoStream.style.display = isOn ? 'block' : 'none';
      }
    }
    // In-Call Bar
    if (DOM.btnMeetCam) {
      DOM.btnMeetCam.classList.toggle('off', !isOn);
      DOM.iconCallCamOn.classList.toggle('hidden', !isOn);
      DOM.iconCallCamOff.classList.toggle('hidden', isOn);
    }
  }

  function toggleHandRaise() {
    state.mediaState.hand = !state.mediaState.hand;
    if (DOM.btnMeetHand) {
      DOM.btnMeetHand.classList.toggle('raised', state.mediaState.hand);
    }
    if (state.mediaState.hand && window.soundFX) {
      window.soundFX.playHandRaise();
    }
    showToast(state.mediaState.hand ? 'Bạn đã giơ tay phát biểu ✋' : 'Bạn đã hạ tay xuống');
    sendMediaState();
    renderLocalTile();
  }

  // ─────────────────────────────────────────────────────────────────
  // ─────────────────────────────────────────────────────────────────
  // ─────────────────────────────────────────────────────────────────
  // WEBRTC PEER CONNECTION & SCREEN SHARING SIGNALING
  // ─────────────────────────────────────────────────────────────────
  const RTC_CONFIG = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ]
  };

  const pendingIceCandidates = new Map(); // key -> Array<candidate>

  function storePeer(keyOrUser, pc) {
    if (!keyOrUser) return;
    if (typeof keyOrUser === 'object') {
      if (keyOrUser.id != null) state.peerConnections.set(String(keyOrUser.id), pc);
      if (keyOrUser.username) state.peerConnections.set(String(keyOrUser.username), pc);
    } else {
      state.peerConnections.set(String(keyOrUser), pc);
    }
  }

  function getPeer(keyOrUser) {
    if (!keyOrUser) return null;
    if (typeof keyOrUser === 'object') {
      return (keyOrUser.id != null && state.peerConnections.get(String(keyOrUser.id))) ||
             (keyOrUser.username && state.peerConnections.get(String(keyOrUser.username))) || null;
    }
    return state.peerConnections.get(String(keyOrUser)) || null;
  }

  async function flushPendingIceCandidates(key, pc) {
    if (!key || !pc) return;
    const strKey = String(key);
    const queue = pendingIceCandidates.get(strKey);
    if (queue && queue.length > 0) {
      pendingIceCandidates.delete(strKey);
      for (const cand of queue) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(cand));
          console.log(`🧊 [WebRTC] Đã nạp ICE candidate tồn đọng cho ${strKey}`);
        } catch (err) {
          console.warn(`Lỗi khi nạp candidate tồn đọng cho ${strKey}:`, err);
        }
      }
    }
  }

  async function createPeerOfferForUser(targetUser, stream) {
    if (!stream) return;
    console.log(`📡 [WebRTC] Khởi tạo Peer Offer chia sẻ màn hình tới ${targetUser.username} (ID: ${targetUser.id})`);

    // Đóng peer cũ nếu đã có
    const oldPc = getPeer(targetUser);
    if (oldPc) {
      try { oldPc.close(); } catch (_) {}
    }
    if (targetUser.id != null) state.peerConnections.delete(String(targetUser.id));
    if (targetUser.username) state.peerConnections.delete(String(targetUser.username));

    const pc = new RTCPeerConnection(RTC_CONFIG);
    storePeer(targetUser, pc);

    // Gắn track video màn hình vào peer connection
    stream.getTracks().forEach(track => {
      pc.addTrack(track, stream);
    });

    pc.onicecandidate = (event) => {
      if (event.candidate && state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({
          type: 'SIGNAL',
          data: {
            to_id: targetUser.id,
            to_user: targetUser.username,
            signal_type: 'candidate',
            signal: event.candidate.toJSON ? event.candidate.toJSON() : event.candidate
          }
        }));
      }
    };

    pc.onconnectionstatechange = () => {
      console.log(`📡 [WebRTC] Kết nối tới ${targetUser.username}: ${pc.connectionState}`);
    };

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({
          type: 'SIGNAL',
          data: {
            to_id: targetUser.id,
            to_user: targetUser.username,
            signal_type: 'offer',
            signal: offer.toJSON ? offer.toJSON() : { type: offer.type, sdp: offer.sdp },
            is_screen: true
          }
        }));
        console.log(`📡 [WebRTC] Đã gửi Offer màn hình tới ${targetUser.username}`);
      }
    } catch (err) {
      console.warn('Failed to create offer for', targetUser.username, err);
    }
  }

  function broadcastScreenShare(stream) {
    state.participants.forEach(user => {
      createPeerOfferForUser(user, stream);
    });
  }

  async function handleSignalMessage(data) {
    const fromId = data.from_id;
    const fromUser = data.from_user;
    const signalType = data.signal_type;
    const signal = data.signal;

    if (!signalType || !signal) return;

    if (signalType === 'offer') {
      console.log(`📡 [WebRTC] Nhận được Offer màn hình từ ${data.from_fullname || fromUser} (#${fromId})`);
      const oldPc = getPeer(fromId) || getPeer(fromUser);
      if (oldPc) {
        try { oldPc.close(); } catch (_) {}
      }

      const pc = new RTCPeerConnection(RTC_CONFIG);
      if (fromId != null) storePeer(fromId, pc);
      if (fromUser) storePeer(fromUser, pc);

      pc.ontrack = (event) => {
        console.log(`📺 [WebRTC] Nhận luồng video màn hình trực tiếp từ ${data.from_fullname || fromUser}!`);
        const stream = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
        state.remoteScreenStream = stream;

        if (DOM.screenShareVideo) {
          DOM.screenShareVideo.muted = true;
          DOM.screenShareVideo.srcObject = stream;
          DOM.screenShareVideo.play().catch(e => console.warn('screenShareVideo play warning:', e));
        }
        if (DOM.meetPresentationStage) {
          DOM.meetPresentationStage.classList.add('active');
        }
        if (DOM.meetMainStage) {
          DOM.meetMainStage.classList.add('has-presentation');
        }
        if (DOM.screenSharePresenterText) {
          DOM.screenSharePresenterText.textContent = `${data.from_fullname || fromUser} đang trình bày màn hình`;
        }
        if (DOM.btnStopPresentation) {
          DOM.btnStopPresentation.style.display = 'none'; // Người xem không có nút "Dừng chia sẻ"
        }

        event.track.onunmute = () => {
          if (DOM.screenShareVideo) {
            DOM.screenShareVideo.play().catch(() => {});
          }
        };
      };

      pc.onicecandidate = (event) => {
        if (event.candidate && state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({
            type: 'SIGNAL',
            data: {
              to_id: fromId,
              to_user: fromUser,
              signal_type: 'candidate',
              signal: event.candidate.toJSON ? event.candidate.toJSON() : event.candidate
            }
          }));
        }
      };

      pc.onconnectionstatechange = () => {
        console.log(`📡 [WebRTC Receiver] Trạng thái kết nối: ${pc.connectionState}`);
      };

      try {
        await pc.setRemoteDescription(new RTCSessionDescription(signal));
        // Xả hàng đợi các candidate đến sớm trước khi Remote Description được set
        if (fromId != null) await flushPendingIceCandidates(fromId, pc);
        if (fromUser) await flushPendingIceCandidates(fromUser, pc);

        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({
            type: 'SIGNAL',
            data: {
              to_id: fromId,
              to_user: fromUser,
              signal_type: 'answer',
              signal: answer.toJSON ? answer.toJSON() : { type: answer.type, sdp: answer.sdp }
            }
          }));
          console.log(`📡 [WebRTC] Đã gửi Answer phản hồi cho ${fromUser}`);
        }
      } catch (err) {
        console.warn('Failed to handle WebRTC offer from', fromUser, err);
      }

    } else if (signalType === 'answer') {
      console.log(`📡 [WebRTC] Nhận được Answer từ ${fromUser} (#${fromId})`);
      const pc = getPeer(fromId) || getPeer(fromUser);
      if (pc) {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription(signal));
          if (fromId != null) await flushPendingIceCandidates(fromId, pc);
          if (fromUser) await flushPendingIceCandidates(fromUser, pc);
        } catch (err) {
          console.warn('Failed to set remote answer from', fromUser, err);
        }
      }

    } else if (signalType === 'candidate') {
      const pc = getPeer(fromId) || getPeer(fromUser);
      if (pc && pc.remoteDescription && pc.remoteDescription.type) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(signal));
        } catch (err) {
          console.warn('Failed to add ICE candidate from', fromUser, err);
        }
      } else {
        // Lưu tạm candidate vào queue chờ setRemoteDescription xong
        const qKey = String(fromId != null ? fromId : fromUser);
        if (!pendingIceCandidates.has(qKey)) {
          pendingIceCandidates.set(qKey, []);
        }
        pendingIceCandidates.get(qKey).push(signal);
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // SCREEN SHARING (GETDISPLAYMEDIA)
  // ─────────────────────────────────────────────────────────────────
  async function toggleScreenShare() {
    if (state.mediaState.screen) {
      stopScreenShare();
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      showToast('⚠️ Tính năng chia sẻ màn hình yêu cầu kết nối an toàn (localhost hoặc HTTPS)', 4000);
      return;
    }

    let stream = null;
    try {
      // 1. Thử lấy quyền chia sẻ với cấu hình tiêu chuẩn
      try {
        stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false
        });
      } catch (errConstraint) {
        // Fallback đơn giản nhất cho các trình duyệt hoặc hệ điều hành (Linux portal / Wayland / Windows)
        stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      }

      if (!stream) return;

      state.screenStream = stream;
      state.mediaState.screen = true;

      if (DOM.screenShareVideo) {
        DOM.screenShareVideo.muted = true;
        DOM.screenShareVideo.srcObject = stream;
        try {
          await DOM.screenShareVideo.play();
        } catch (_) {}
      }

      if (DOM.meetPresentationStage) {
        DOM.meetPresentationStage.classList.add('active');
      }
      if (DOM.meetMainStage) {
        DOM.meetMainStage.classList.add('has-presentation');
      }
      if (DOM.btnMeetShareScreen) {
        DOM.btnMeetShareScreen.classList.add('active-blue');
      }
      if (DOM.screenSharePresenterText) {
        DOM.screenSharePresenterText.textContent = 'Bạn đang trình bày màn hình cho mọi người';
      }
      if (DOM.btnStopPresentation) {
        DOM.btnStopPresentation.style.display = 'inline-block';
      }

      // Phát luồng WebRTC tới tất cả các thành viên trong phòng (bên M sẽ thấy ngay!)
      broadcastScreenShare(stream);

      // Lắng nghe sự kiện người dùng nhấn "Dừng chia sẻ" (Stop sharing) trên thanh điều khiển của trình duyệt
      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.onended = () => {
          stopScreenShare();
        };
      }

      sendMediaState();
      showToast('Đang chia sẻ màn hình 🖥️');
    } catch (err) {
      console.warn('Screen share cancelled/denied:', err);
      if (err.name === 'NotAllowedError') {
        showToast('Bạn đã hủy yêu cầu chia sẻ màn hình');
      } else {
        showToast('Không thể chia sẻ màn hình: ' + (err.message || 'Lỗi thiết bị'));
      }
    }
  }

  function stopScreenShare() {
    if (state.screenStream) {
      state.screenStream.getTracks().forEach(t => t.stop());
      state.screenStream = null;
    }
    state.mediaState.screen = false;

    // Đóng tất cả kết nối WebRTC đang phát
    state.peerConnections.forEach(pc => {
      try {
        pc.close();
      } catch (_) {}
    });
    state.peerConnections.clear();
    pendingIceCandidates.clear();

    if (DOM.screenShareVideo) {
      DOM.screenShareVideo.srcObject = null;
    }
    if (DOM.meetPresentationStage) {
      DOM.meetPresentationStage.classList.remove('active');
    }
    if (DOM.meetMainStage) {
      DOM.meetMainStage.classList.remove('has-presentation');
    }
    if (DOM.btnMeetShareScreen) {
      DOM.btnMeetShareScreen.classList.remove('active-blue');
    }

    sendMediaState();
    showToast('Đã dừng chia sẻ màn hình');
  }

  // ─────────────────────────────────────────────────────────────────
  // REACTIONS & FLOATING EMOJIS
  // ─────────────────────────────────────────────────────────────────
  function triggerEmoji(emoji, isLocal = false) {
    if (!DOM.emojiFlyContainer) return;
    const elem = document.createElement('div');
    elem.className = 'floating-emoji';
    elem.textContent = emoji;
    const randomOffset = Math.floor(Math.random() * 40) - 20;
    elem.style.left = `${Math.max(10, 30 + randomOffset)}px`;
    DOM.emojiFlyContainer.appendChild(elem);

    setTimeout(() => {
      elem.remove();
    }, 2500);

    if (isLocal && state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify({
        type: 'REACTION',
        data: { emoji: emoji }
      }));
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // WEBSOCKET & DUAL PROTOCOL INTEGRATION
  // ─────────────────────────────────────────────────────────────────
  function connectWebSocket(username) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = (window.Auth && window.Auth.getToken()) || '';
    const wsUrl = `${protocol}//${location.host}/ws?room=${encodeURIComponent(state.roomCode)}&token=${encodeURIComponent(token)}`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
      console.log('Connected to Google Meet WebSocket Gateway');
      // Send JOIN message
      state.ws.send(JSON.stringify({
        type: 'JOIN',
        data: {
          username: username,
          room: state.roomCode,
          token: token
        }
      }));

      // Start keepalive ping
      clearInterval(state.pingInterval);
      state.pingInterval = setInterval(() => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({ type: 'PING' }));
        }
      }, 25000);
    };

    state.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleServerMessage(payload);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    state.ws.onclose = () => {
      console.warn('WebSocket connection closed');
      clearInterval(state.pingInterval);
      if (state.isJoined) {
        showToast('Kết nối bị gián đoạn. Đang kết nối lại...');
        setTimeout(() => connectWebSocket(username), 3000);
      }
    };

    state.ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }

  function handleServerMessage(msg) {
    const type = msg.type;
    const data = msg.data || {};

    switch (type) {
      case 'WELCOME':
        state.clientId = data.client_id;
        state.isHost = data.is_host || false;
        state.roomTitle = data.room_title || state.roomCode;
        if (state.currentUser) {
          state.currentUser.is_host = state.isHost;
          state.currentUser.avatar_color = data.avatar_color || state.currentUser.avatar_color;
        }
        renderLocalTile();
        if (window.soundFX) window.soundFX.playJoin();
        showToast(`Đã tham gia cuộc họp ${state.roomTitle}`);
        break;

      case 'ONLINE_LIST':
        handleOnlineList(data);
        break;

      case 'MSG':
        handleIncomingChatMessage(data);
        break;

      case 'PRIVATE':
        handleIncomingPrivateMessage(data);
        break;

      case 'SYSTEM':
        handleIncomingSystemNotice(data);
        break;

      case 'MEDIA_STATE':
        handleRemoteMediaState(data);
        break;

      case 'SIGNAL':
        handleSignalMessage(data);
        break;

      case 'REACTION':
        if (data.username !== (state.currentUser && state.currentUser.username)) {
          triggerEmoji(data.emoji, false);
        }
        break;

      case 'ERROR':
        showToast(`⚠️ ${data.message || 'Có lỗi xảy ra'}`);
        break;

      case 'PONG':
        break;

      default:
        console.log('Unhandled server message:', msg);
    }
  }

  function sendMediaState() {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
    state.ws.send(JSON.stringify({
      type: 'MEDIA_STATE',
      data: {
        state: state.mediaState
      }
    }));
  }

  function handleOnlineList(data) {
    const usersDetail = data.users_detail || [];
    const myUsername = state.currentUser ? state.currentUser.username : '';

    state.participants.clear();
    usersDetail.forEach(u => {
      if (u.username !== myUsername) {
        state.participants.set(u.username, u);
        // Nếu mình đang chia sẻ màn hình, tự động kết nối WebRTC gửi stream cho người mới vào
        if (state.mediaState.screen && state.screenStream) {
          const key = String(u.id || u.username);
          if (!state.peerConnections.has(key)) {
            createPeerOfferForUser(u, state.screenStream);
          }
        }
      }
    });

    updateParticipantsUI();
    renderVideoGrid();
  }

  function handleRemoteMediaState(data) {
    const user = state.participants.get(data.username);
    if (user) {
      user.media_state = data.media_state;
      if (data.media_state && data.media_state.hand) {
        if (window.soundFX) window.soundFX.playHandRaise();
        showToast(`${user.fullname || user.username} đã giơ tay ✋`);
      }
      // Khi người trong phòng bắt đầu chia sẻ màn hình
      if (data.media_state && data.media_state.screen === true) {
        if (DOM.meetPresentationStage) {
          DOM.meetPresentationStage.classList.add('active');
        }
        if (DOM.meetMainStage) {
          DOM.meetMainStage.classList.add('has-presentation');
        }
        if (DOM.screenSharePresenterText) {
          DOM.screenSharePresenterText.textContent = `${user.fullname || user.username} đang trình bày màn hình`;
        }
        if (DOM.btnStopPresentation) {
          DOM.btnStopPresentation.style.display = 'none';
        }
      }
      // Khi người đang trình bày dừng chia sẻ màn hình
      if (data.media_state && data.media_state.screen === false) {
        if (state.remoteScreenStream) {
          state.remoteScreenStream.getTracks().forEach(t => t.stop());
          state.remoteScreenStream = null;
        }
        if (DOM.screenShareVideo) {
          DOM.screenShareVideo.srcObject = null;
        }
        if (DOM.meetPresentationStage) {
          DOM.meetPresentationStage.classList.remove('active');
        }
        if (DOM.meetMainStage) {
          DOM.meetMainStage.classList.remove('has-presentation');
        }
        showToast(`${user.fullname || user.username} đã dừng chia sẻ màn hình`);
      }
      renderVideoGrid();
      updateParticipantsUI();
    }
  }

  function handleIncomingChatMessage(data) {
    appendChatMessage(data);
    if (window.soundFX) window.soundFX.playReceived();

    if (state.activeDrawer !== 'chat') {
      state.unreadChatCount++;
      DOM.badgeChatCount.textContent = state.unreadChatCount;
      DOM.badgeChatCount.classList.remove('hidden');
    }

    if (state.captionsEnabled) {
      DOM.captionText.textContent = `${data.fullname || data.username}: ${data.content}`;
    }
  }

  function handleIncomingPrivateMessage(data) {
    data.isPrivate = true;
    appendChatMessage(data);
    if (window.soundFX) window.soundFX.playReceived();
  }

  function handleIncomingSystemNotice(data) {
    const text = data.message || '';
    if (window.soundFX) {
      if (text.includes('tham gia')) window.soundFX.playJoin();
      else if (text.includes('rời phòng')) window.soundFX.playLeave();
    }
    appendSystemMessage(text);
  }

  // ─────────────────────────────────────────────────────────────────
  // VIDEO GRID RENDERING
  // ─────────────────────────────────────────────────────────────────
  function renderVideoGrid() {
    if (!DOM.meetGridContainer) return;
    const totalTiles = 1 + state.participants.size;
    DOM.meetGridContainer.setAttribute('data-tiles', String(Math.min(totalTiles, 9)));

    const colorMap = resolveAvatarColors();
    const localColorInfo = colorMap.get('local') || {
      initial: getInitials(state.currentUser ? (state.currentUser.fullname || state.currentUser.username) : 'Bạn'),
      color: '#1a73e8'
    };

    // Keep track of existing tiles
    const existingTiles = new Set();
    Array.from(DOM.meetGridContainer.children).forEach(child => {
      existingTiles.add(child.id);
    });

    // 1. Render Local Tile
    const localId = `tile-${state.currentUser ? state.currentUser.username : 'local'}`;
    const localFullname = state.currentUser ? `${state.currentUser.fullname || state.currentUser.username} (Bạn)` : 'Bạn';
    if (!document.getElementById(localId)) {
      const localTile = createTileElement({
        id: localId,
        username: state.currentUser ? state.currentUser.username : 'Bạn',
        fullname: localFullname,
        isLocal: true,
        avatar_color: localColorInfo.color,
        avatar_initial: localColorInfo.initial,
        media_state: state.mediaState,
        is_host: state.isHost
      });
      DOM.meetGridContainer.appendChild(localTile);
    } else {
      updateTileContent(document.getElementById(localId), {
        fullname: localFullname,
        isLocal: true,
        avatar_color: localColorInfo.color,
        avatar_initial: localColorInfo.initial,
        media_state: state.mediaState,
        is_host: state.isHost
      });
    }

    // 2. Render Remote Participants Tiles
    state.participants.forEach((user, uname) => {
      const tileId = `tile-${uname}`;
      const remoteColorInfo = colorMap.get(uname) || {
        initial: getInitials(user.fullname || user.username),
        color: '#34a853'
      };
      let tile = document.getElementById(tileId);
      if (!tile) {
        tile = createTileElement({
          id: tileId,
          username: user.username,
          fullname: user.fullname || user.username,
          isLocal: false,
          avatar_color: remoteColorInfo.color,
          avatar_initial: remoteColorInfo.initial,
          media_state: user.media_state || { mic: true, cam: true, hand: false },
          is_host: user.is_host,
          type: user.type
        });
        DOM.meetGridContainer.appendChild(tile);
      } else {
        updateTileContent(tile, {
          fullname: user.fullname || user.username,
          isLocal: false,
          avatar_color: remoteColorInfo.color,
          avatar_initial: remoteColorInfo.initial,
          media_state: user.media_state || { mic: true, cam: true, hand: false },
          is_host: user.is_host,
          type: user.type
        });
      }
      existingTiles.delete(tileId);
    });

    existingTiles.delete(localId);
    // Remove obsolete tiles
    existingTiles.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });
  }

  function renderLocalTile() {
    const localId = `tile-${state.currentUser ? state.currentUser.username : 'local'}`;
    const localTile = document.getElementById(localId);
    if (localTile) {
      const colorMap = resolveAvatarColors();
      const localColorInfo = colorMap.get('local') || {
        initial: getInitials(state.currentUser ? (state.currentUser.fullname || state.currentUser.username) : 'Bạn'),
        color: '#1a73e8'
      };
      updateTileContent(localTile, {
        fullname: state.currentUser ? `${state.currentUser.fullname || state.currentUser.username} (Bạn)` : 'Bạn',
        isLocal: true,
        avatar_color: localColorInfo.color,
        avatar_initial: localColorInfo.initial,
        media_state: state.mediaState,
        is_host: state.isHost
      });
    }
  }

  function createTileElement(info) {
    const tile = document.createElement('div');
    tile.className = 'meet-participant-tile';
    tile.id = info.id;

    updateTileContent(tile, info);
    return tile;
  }

  function updateTileContent(tile, info) {
    const isCamOn = info.isLocal ? state.mediaState.cam : (info.media_state && info.media_state.cam);
    const isMicOn = info.isLocal ? state.mediaState.mic : (info.media_state && info.media_state.mic !== false);
    const isHandRaised = info.isLocal ? state.mediaState.hand : (info.media_state && info.media_state.hand);

    let html = '';

    // Hand Raised Badge
    if (isHandRaised) {
      html += `<div class="tile-hand-badge">✋ Giơ tay</div>`;
    }

    // Video or Avatar
    if (info.isLocal && state.localStream && isCamOn) {
      html += `<video class="tile-video-elem" autoplay playsinline muted></video>`;
    } else {
      const initial = info.avatar_initial || getInitials(info.fullname);
      html += `
        <div class="tile-avatar-box">
          <div class="tile-avatar-circle" style="background-color: ${info.avatar_color || '#1a73e8'};">
            ${initial}
          </div>
        </div>
      `;
    }

    // Bottom-Left Name Tag
    const micIcon = isMicOn
      ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`
      : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ea4335" stroke-width="2"><line x1="1" y1="1" x2="23" y2="23"></line><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`;

    const hostBadge = info.is_host ? `<span style="background: rgba(251,191,36,0.25); color: #fbbf24; font-size: 0.7rem; padding: 2px 6px; border-radius: 8px; font-weight: 600;">Chủ trì</span>` : '';
    const platformBadge = info.type === 'tcp' ? `<span style="background: rgba(168,85,247,0.25); color: #c084fc; font-size: 0.7rem; padding: 2px 6px; border-radius: 8px;">💻 TCP</span>` : '';

    html += `
      <div class="tile-name-tag">
        <span class="tile-mic-indicator ${!isMicOn ? 'muted' : ''}">${micIcon}</span>
        <span>${info.fullname}</span>
        ${hostBadge}
        ${platformBadge}
      </div>
    `;

    // Hover actions (pin, spotlight)
    html += `
      <div class="tile-hover-actions">
        <button class="btn-tile-act" title="Ghim ô này" onclick="this.closest('.meet-participant-tile').classList.toggle('pinned')">📌</button>
      </div>
    `;

    tile.innerHTML = html;

    // Attach local stream to video if cam is on
    if (info.isLocal && state.localStream && isCamOn) {
      const vid = tile.querySelector('video');
      if (vid) {
        vid.srcObject = state.localStream;
        vid.play().catch(() => {});
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // RIGHT DRAWER & TABS LOGIC
  // ─────────────────────────────────────────────────────────────────
  function toggleDrawer(tabName) {
    if (state.activeDrawer === tabName) {
      closeDrawer();
      return;
    }
    openDrawer(tabName);
  }

  function openDrawer(tabName) {
    state.activeDrawer = tabName;
    DOM.meetSideDrawer.classList.remove('hidden');

    // Update bottom tool icons active state
    DOM.btnToggleInfo.classList.toggle('active', tabName === 'info');
    DOM.btnTogglePeople.classList.toggle('active', tabName === 'people');
    DOM.btnToggleChat.classList.toggle('active', tabName === 'chat');
    DOM.btnToggleHostControls.classList.toggle('active', tabName === 'host');

    // Hide all panels
    DOM.panelDrawerPeople.classList.add('hidden');
    DOM.panelDrawerChat.classList.add('hidden');
    DOM.panelDrawerHost.classList.add('hidden');
    DOM.panelDrawerInfo.classList.add('hidden');

    // Reset tab buttons active state
    DOM.tabBtnDrawerPeople.classList.remove('active');
    DOM.tabBtnDrawerChat.classList.remove('active');
    DOM.tabBtnDrawerHost.classList.remove('active');

    if (tabName === 'people') {
      DOM.drawerHeaderTitle.textContent = 'Mọi người';
      DOM.panelDrawerPeople.classList.remove('hidden');
      DOM.tabBtnDrawerPeople.classList.add('active');
    } else if (tabName === 'chat') {
      DOM.drawerHeaderTitle.textContent = 'Tin nhắn trong cuộc gọi';
      DOM.panelDrawerChat.classList.remove('hidden');
      DOM.tabBtnDrawerChat.classList.add('active');
      state.unreadChatCount = 0;
      DOM.badgeChatCount.classList.add('hidden');
      if (DOM.inputMeetChat) DOM.inputMeetChat.focus();
    } else if (tabName === 'host') {
      DOM.drawerHeaderTitle.textContent = 'Bộ điều khiển của người tổ chức';
      DOM.panelDrawerHost.classList.remove('hidden');
      DOM.tabBtnDrawerHost.classList.add('active');
    } else if (tabName === 'info') {
      DOM.drawerHeaderTitle.textContent = 'Chi tiết cuộc họp';
      DOM.panelDrawerInfo.classList.remove('hidden');
    }
  }

  function closeDrawer() {
    state.activeDrawer = null;
    DOM.meetSideDrawer.classList.add('hidden');
    DOM.btnToggleInfo.classList.remove('active');
    DOM.btnTogglePeople.classList.remove('active');
    DOM.btnToggleChat.classList.remove('active');
    DOM.btnToggleHostControls.classList.remove('active');
  }

  function updateParticipantsUI() {
    const totalCount = 1 + state.participants.size;
    if (DOM.badgePeopleCount) DOM.badgePeopleCount.textContent = totalCount;
    if (DOM.peopleCountLabel) DOM.peopleCountLabel.textContent = `Trong cuộc gọi (${totalCount})`;

    if (!DOM.drawerPeopleList) return;
    DOM.drawerPeopleList.innerHTML = '';

    const colorMap = resolveAvatarColors();
    const localColorInfo = colorMap.get('local') || {
      initial: getInitials(state.currentUser ? (state.currentUser.fullname || state.currentUser.username) : 'Bạn'),
      color: '#1a73e8'
    };

    // 1. Local user row
    const localUser = state.currentUser || { username: 'local', fullname: 'Bạn', avatar_color: '#1a73e8' };
    DOM.drawerPeopleList.appendChild(createPeopleItemRow({
      fullname: `${localUser.fullname || localUser.username} (Bạn)`,
      avatar_color: localColorInfo.color,
      avatar_initial: localColorInfo.initial,
      is_host: state.isHost,
      isMicOn: state.mediaState.mic
    }));

    // 2. Remote users rows
    state.participants.forEach((u, uname) => {
      const remColorInfo = colorMap.get(uname) || {
        initial: getInitials(u.fullname || u.username),
        color: '#34a853'
      };
      DOM.drawerPeopleList.appendChild(createPeopleItemRow({
        fullname: u.fullname || u.username,
        avatar_color: remColorInfo.color,
        avatar_initial: remColorInfo.initial,
        is_host: u.is_host,
        type: u.type,
        isMicOn: u.media_state ? u.media_state.mic : true
      }));
    });
  }

  function createPeopleItemRow(item) {
    const row = document.createElement('div');
    row.className = 'people-item-row';
    const initial = item.avatar_initial || getInitials(item.fullname);
    const micIcon = item.isMicOn
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ea4335" stroke-width="2"><line x1="1" y1="1" x2="23" y2="23"></line><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`;

    row.innerHTML = `
      <div class="people-info-left">
        <div class="people-avatar-sm" style="background-color: ${item.avatar_color || '#1a73e8'};">
          ${initial}
        </div>
        <div>
          <span class="people-name">${item.fullname}</span>
          ${item.is_host ? '<span class="people-role-tag">(Chủ trì)</span>' : ''}
          ${item.type === 'tcp' ? '<span style="font-size: 0.7rem; color: #a855f7; margin-left: 4px;">[TCP]</span>' : ''}
        </div>
      </div>
      <div>${micIcon}</div>
    `;
    return row;
  }

  // ─────────────────────────────────────────────────────────────────
  // IN-CALL CHAT STREAM
  // ─────────────────────────────────────────────────────────────────
  function appendChatMessage(data) {
    if (!DOM.meetChatStream) return;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble-meet';

    const time = data.timestamp || formatTime();
    const isMe = data.username === (state.currentUser && state.currentUser.username);
    const author = isMe ? 'Bạn' : (data.fullname || data.username);
    const authorColor = data.avatar_color || (isMe ? '#8ab4f8' : '#81c995');

    let badge = '';
    if (data.is_host) badge = '<span style="color: #fbbc04; font-size: 0.7rem; margin-left: 4px;">👑 Host</span>';
    if (data.client_type === 'tcp') badge += '<span style="color: #c084fc; font-size: 0.7rem; margin-left: 4px;">💻 TCP</span>';
    if (data.isPrivate) badge += '<span style="color: #ea4335; font-size: 0.7rem; margin-left: 4px;">🔒 Riêng tư</span>';

    bubble.innerHTML = `
      <div class="chat-meta-row">
        <span class="chat-author-name" style="color: ${authorColor};">${author}</span>
        ${badge}
        <span>${time}</span>
      </div>
      <div class="chat-message-text">${escapeHtml(data.content || '')}</div>
    `;

    DOM.meetChatStream.appendChild(bubble);
    DOM.meetChatStream.scrollTop = DOM.meetChatStream.scrollHeight;
  }

  function appendSystemMessage(text) {
    if (!DOM.meetChatStream) return;
    const notice = document.createElement('div');
    notice.style.fontSize = '0.78rem';
    notice.style.color = '#9aa0a6';
    notice.style.textAlign = 'center';
    notice.style.padding = '4px 8px';
    notice.textContent = text;
    DOM.meetChatStream.appendChild(notice);
    DOM.meetChatStream.scrollTop = DOM.meetChatStream.scrollHeight;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function sendChatMessage(text) {
    text = (text || '').trim();
    if (!text || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;

    // Check whisper command e.g. /w user message
    if (text.startsWith('/w ') || text.startsWith('/whisper ')) {
      const parts = text.split(/\s+/);
      if (parts.length >= 3) {
        const target = parts[1];
        const content = parts.slice(2).join(' ');
        state.ws.send(JSON.stringify({
          type: 'PRIVATE',
          data: { to: target, content: content }
        }));
        return;
      }
    }

    state.ws.send(JSON.stringify({
      type: 'MSG',
      data: { content: text }
    }));
  }

  // ─────────────────────────────────────────────────────────────────
  // JOIN MEETING ACTION
  // ─────────────────────────────────────────────────────────────────
  async function joinMeeting(withScreen = false) {
    let name = '';
    if (state.currentUser && state.currentUser.fullname) {
      name = state.currentUser.fullname;
    } else if (DOM.grInputUsername && DOM.grInputUsername.value.trim()) {
      name = DOM.grInputUsername.value.trim();
    } else {
      name = `Khách_${Math.floor(1000 + Math.random() * 9000)}`;
    }

    if (!state.currentUser) {
      state.currentUser = {
        username: name,
        fullname: name,
        avatar_color: '#1a73e8'
      };
    }

    state.isJoined = true;

    // Switch UI from Green Room to Main Stage
    DOM.greenRoomContainer.classList.add('hidden');
    DOM.meetMainStage.style.display = 'flex';
    DOM.meetBottomBar.style.display = 'flex';

    // Connect WebSocket
    connectWebSocket(name);

    // Initial render of local tile
    renderVideoGrid();
    updateParticipantsUI();

    if (withScreen) {
      toggleScreenShare();
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // LEAVE CALL ACTION
  // ─────────────────────────────────────────────────────────────────
  function endCall() {
    if (confirm('Bạn có chắc chắn muốn rời khỏi cuộc gọi?')) {
      state.isJoined = false;

      // Stop all media tracks
      if (state.localStream) {
        state.localStream.getTracks().forEach(t => t.stop());
      }
      if (state.screenStream) {
        state.screenStream.getTracks().forEach(t => t.stop());
      }
      if (state.audioLevelInterval) {
        clearInterval(state.audioLevelInterval);
      }
      if (state.ws) {
        state.ws.send(JSON.stringify({ type: 'QUIT' }));
        state.ws.close();
      }

      window.location.href = '/';
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // EVENT LISTENERS BINDING
  // ─────────────────────────────────────────────────────────────────
  function bindEvents() {
    // Green Room Controls
    if (DOM.grBtnMic) DOM.grBtnMic.addEventListener('click', toggleMic);
    if (DOM.grBtnCam) DOM.grBtnCam.addEventListener('click', toggleCam);
    if (DOM.btnGrJoinNow) DOM.btnGrJoinNow.addEventListener('click', () => joinMeeting(false));
    if (DOM.btnGrPresent) DOM.btnGrPresent.addEventListener('click', () => joinMeeting(true));
    if (DOM.grInputUsername) {
      DOM.grInputUsername.addEventListener('input', () => {
        const val = DOM.grInputUsername.value.trim();
        const initial = getInitials(val || 'Khách');
        if (DOM.grChipAvatar) DOM.grChipAvatar.textContent = initial;
        if (DOM.grAvatarCircle) DOM.grAvatarCircle.textContent = initial;
        if (DOM.grChipName) DOM.grChipName.textContent = val || 'Khách';
      });
    }

    // Bottom Bar Controls
    if (DOM.btnMeetMic) DOM.btnMeetMic.addEventListener('click', toggleMic);
    if (DOM.btnMeetCam) DOM.btnMeetCam.addEventListener('click', toggleCam);
    if (DOM.btnMeetHand) DOM.btnMeetHand.addEventListener('click', toggleHandRaise);
    if (DOM.btnMeetShareScreen) DOM.btnMeetShareScreen.addEventListener('click', toggleScreenShare);
    if (DOM.btnStopPresentation) DOM.btnStopPresentation.addEventListener('click', stopScreenShare);
    if (DOM.btnMeetEndCall) DOM.btnMeetEndCall.addEventListener('click', endCall);

    // Captions toggle
    if (DOM.btnMeetCC) {
      DOM.btnMeetCC.addEventListener('click', () => {
        state.captionsEnabled = !state.captionsEnabled;
        DOM.btnMeetCC.classList.toggle('active-blue', state.captionsEnabled);
        DOM.meetCaptionsBox.classList.toggle('hidden', !state.captionsEnabled);
        showToast(state.captionsEnabled ? 'Đã bật phụ đề' : 'Đã tắt phụ đề');
      });
    }

    // Reactions popup toggle
    if (DOM.btnMeetReact) {
      DOM.btnMeetReact.addEventListener('click', (e) => {
        e.stopPropagation();
        DOM.reactionPopup.classList.toggle('hidden');
      });
    }
    document.addEventListener('click', () => {
      if (DOM.reactionPopup) DOM.reactionPopup.classList.add('hidden');
    });
    if (DOM.reactionPopup) {
      DOM.reactionPopup.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-emoji-react');
        if (btn) {
          const emoji = btn.getAttribute('data-emoji');
          triggerEmoji(emoji, true);
        }
      });
    }

    // More Options toggle (Fullscreen)
    if (DOM.btnMeetMore) {
      DOM.btnMeetMore.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
          showToast('Đã chuyển sang chế độ toàn màn hình');
        } else {
          document.exitFullscreen().catch(() => {});
          showToast('Đã thoát toàn màn hình');
        }
      });
    }

    // Right Drawer toggles
    if (DOM.btnToggleInfo) DOM.btnToggleInfo.addEventListener('click', () => toggleDrawer('info'));
    if (DOM.btnTogglePeople) DOM.btnTogglePeople.addEventListener('click', () => toggleDrawer('people'));
    if (DOM.btnToggleChat) DOM.btnToggleChat.addEventListener('click', () => toggleDrawer('chat'));
    if (DOM.btnToggleHostControls) DOM.btnToggleHostControls.addEventListener('click', () => toggleDrawer('host'));
    if (DOM.btnCloseDrawer) DOM.btnCloseDrawer.addEventListener('click', closeDrawer);

    // Drawer Tabs switching
    if (DOM.tabBtnDrawerPeople) DOM.tabBtnDrawerPeople.addEventListener('click', () => openDrawer('people'));
    if (DOM.tabBtnDrawerChat) DOM.tabBtnDrawerChat.addEventListener('click', () => openDrawer('chat'));
    if (DOM.tabBtnDrawerHost) DOM.tabBtnDrawerHost.addEventListener('click', () => openDrawer('host'));

    // Copy links
    const copyUrlAction = () => {
      const url = `${window.location.origin}/room?code=${state.roomCode}`;
      navigator.clipboard.writeText(url).then(() => {
        showToast('Đã sao chép đường liên kết tham gia cuộc họp');
      }).catch(() => {
        showToast(`Mã phòng: ${state.roomCode}`);
      });
    };
    if (DOM.btnBottomCopyCode) DOM.btnBottomCopyCode.addEventListener('click', copyUrlAction);
    if (DOM.btnDrawerCopyLink) DOM.btnDrawerCopyLink.addEventListener('click', copyUrlAction);

    // Chat form submit
    if (DOM.formMeetChat) {
      DOM.formMeetChat.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = DOM.inputMeetChat.value;
        if (text) {
          sendChatMessage(text);
          DOM.inputMeetChat.value = '';
        }
      });
    }

    // Host Mute All action
    if (DOM.btnHostMuteAll) {
      DOM.btnHostMuteAll.addEventListener('click', () => {
        if (!state.isHost) {
          showToast('⚠️ Chỉ có Chủ trì cuộc họp mới có quyền tắt tiếng tất cả.');
          return;
        }
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({
            type: 'HOST_ACTION',
            data: { action: 'mute_all' }
          }));
          showToast('Đã gửi lệnh tắt tiếng toàn bộ thành viên');
        }
      });
    }

    // Host security switch toggles
    if (DOM.toggleHostChat) {
      DOM.toggleHostChat.addEventListener('change', (e) => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({
            type: 'HOST_ACTION',
            data: { action: 'toggle_public_chat', enable: e.target.checked }
          }));
        }
      });
    }

    // Keyboard shortcuts (Google Meet standard: Ctrl+D for mic, Ctrl+E for cam)
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.ctrlKey && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        toggleMic();
      } else if (e.ctrlKey && e.key.toLowerCase() === 'e') {
        e.preventDefault();
        toggleCam();
      } else if (e.key.toLowerCase() === 'c') {
        if (DOM.btnMeetCC) DOM.btnMeetCC.click();
      }
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // INIT ON PAGE LOAD
  // ─────────────────────────────────────────────────────────────────
  async function init() {
    parseRoomCode();
    updateClock();
    setInterval(updateClock, 1000);

    // Check authenticated user
    if (window.Auth) {
      const user = window.Auth.getUser();
      if (user) {
        state.currentUser = user;
        const initial = getInitials(user.fullname || user.username);
        const color = user.avatar_color || '#1a73e8';
        if (DOM.grChipName) DOM.grChipName.textContent = user.fullname || user.username;
        if (DOM.grChipAvatar) {
          DOM.grChipAvatar.textContent = initial;
          DOM.grChipAvatar.style.backgroundColor = color;
        }
        if (DOM.grAvatarCircle) {
          DOM.grAvatarCircle.textContent = initial;
          DOM.grAvatarCircle.style.backgroundColor = color;
        }
        if (DOM.grInputUsername) DOM.grInputUsername.value = user.fullname || user.username;
      }
    }

    // Query room info
    try {
      const res = await fetch(`/api/rooms/${state.roomCode}`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.room) {
          state.roomTitle = data.room.title || state.roomCode;
          const count = data.room.client_count || 0;
          if (DOM.grRoomSummaryText) {
            DOM.grRoomSummaryText.textContent = count > 0
              ? `Có ${count} người đang tham gia cuộc gọi`
              : 'Chưa có ai ở đây';
          }
        }
      }
    } catch (_) {
      if (DOM.grRoomSummaryText) DOM.grRoomSummaryText.textContent = 'Sẵn sàng tham gia';
    }

    bindEvents();
    initLocalMedia();
  }

  window.addEventListener('DOMContentLoaded', init);
})();
