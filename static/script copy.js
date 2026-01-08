// ============================================
// SMART HOME DASHBOARD - JAVASCRIPT
// ============================================

const soundManager = {
  lightBeepAudio: null,
  deviceBeepAudio: null,
  isPlaying: {
    light: false,
    device: false,
  },

  init() {
    this.lightBeepAudio = document.getElementById("lightBeep")
    this.deviceBeepAudio = document.getElementById("deviceBeep")

    // Create beep sounds using Web Audio API
    this.createLightBeep()
    this.createDeviceBeep()
  },

  createLightBeep() {
    const context = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = context.createOscillator()
    const gainNode = context.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(context.destination)

    oscillator.frequency.value = 800
    oscillator.type = "sine"

    gainNode.gain.setValueAtTime(0.3, context.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.1)

    oscillator.start(context.currentTime)
    oscillator.stop(context.currentTime + 0.1)
  },

  createDeviceBeep() {
    const context = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = context.createOscillator()
    const gainNode = context.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(context.destination)

    oscillator.frequency.value = 600
    oscillator.type = "sine"

    gainNode.gain.setValueAtTime(0.3, context.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.15)

    oscillator.start(context.currentTime)
    oscillator.stop(context.currentTime + 0.15)
  },

  playLightBeep() {
    if (this.isPlaying.light) return
    this.isPlaying.light = true
    this.createLightBeep()

    setTimeout(() => {
      this.isPlaying.light = false
    }, 100)
  },

  playDeviceBeep() {
    if (this.isPlaying.device) return
    this.isPlaying.device = true
    this.createDeviceBeep()

    setTimeout(() => {
      this.isPlaying.device = false
    }, 150)
  },

  stopAll() {
    this.isPlaying.light = false
    this.isPlaying.device = false
  },
}

// State management
const appState = {
  houseStatus: "kosong",
  rooms: {},
  devices: {},
  notifications: [],
  logs: [],
  lastNotifications: [],
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard initialized")
  soundManager.init()
  initializeApp()
  setupEventListeners()
})

async function initializeApp() {
  await fetchAllData()
  renderRooms()
  renderDevices()
  startClock()

  // Update data every 2 seconds
  setInterval(fetchAllData, 2000)
}

// ============================================
// API CALLS
// ============================================
async function fetchAllData() {
  try {
    const [status, rooms, devices, notifications, logs] = await Promise.all([
      fetch("/api/status").then((r) => r.json()),
      fetch("/api/rooms").then((r) => r.json()),
      fetch("/api/devices").then((r) => r.json()),
      fetch("/api/notifications").then((r) => r.json()),
      fetch("/api/logs").then((r) => r.json()),
    ])

    appState.houseStatus = status.status
    appState.rooms = rooms
    appState.devices = devices
    appState.notifications = notifications
    appState.logs = logs

    checkNewNotifications()

    updateUI()
  } catch (error) {
    console.error("Error fetching data:", error)
  }
}

function checkNewNotifications() {
  const newNotifications = appState.notifications.filter(
    (notif) => !appState.lastNotifications.some((old) => old.id === notif.id),
  )

  newNotifications.forEach((notif) => {
    if (notif.sound_type === "light") {
      soundManager.playLightBeep()
    } else if (notif.sound_type === "device") {
      soundManager.playDeviceBeep()
    }
  })

  appState.lastNotifications = appState.notifications
}

async function toggleRoomLight(roomId) {
  try {
    const response = await fetch(`/api/room/${roomId}/toggle`, { method: "POST" })
    if (!response.ok) {
      const error = await response.json()
      showNotification(error.error, "warning")
      return
    }
    await fetchAllData()
  } catch (error) {
    console.error("Error toggling light:", error)
  }
}

async function setRoomOccupied(roomId, occupied) {
  try {
    const response = await fetch(`/api/room/${roomId}/occupied`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ occupied }),
    })
    if (!response.ok) {
      return
    }
    await fetchAllData()
  } catch (error) {
    console.error("Error setting room occupied:", error)
  }
}

async function toggleDevice(deviceId) {
  try {
    const response = await fetch(`/api/device/${deviceId}/toggle`, { method: "POST" })
    if (!response.ok) {
      const error = await response.json()
      showNotification(error.error, "warning")
      return
    }
    await fetchAllData()
  } catch (error) {
    console.error("Error toggling device:", error)
  }
}

async function turnOffAllLights() {
  try {
    const response = await fetch("/api/lights/all/off", { method: "POST" })
    if (!response.ok) {
      const error = await response.json()
      showNotification(error.error, "warning")
      return
    }
    await fetchAllData()
  } catch (error) {
    console.error("Error turning off all lights:", error)
  }
}

async function turnOffAllDevices() {
  try {
    const response = await fetch("/api/devices/all/off", { method: "POST" })
    if (!response.ok) {
      const error = await response.json()
      showNotification(error.error, "warning")
      return
    }
    await fetchAllData()
  } catch (error) {
    console.error("Error turning off all devices:", error)
  }
}

async function setHouseStatus(status) {
  try {
    await fetch("/api/house/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    })
    await fetchAllData()
  } catch (error) {
    console.error("Error setting house status:", error)
  }
}

// ============================================
// RENDERING
// ============================================
function renderRooms() {
  const grid = document.getElementById("roomsGrid")
  grid.innerHTML = ""

  const roomsData = [
    { id: "kamar1", name: "Kamar 1", icon: "🛏️" },
    { id: "kamar2", name: "Kamar 2", icon: "🛏️" },
    { id: "kamar3", name: "Kamar 3", icon: "🛏️" },
    { id: "dapur", name: "Dapur", icon: "🍳" },
    { id: "ruang_cuci", name: "Ruang Cuci", icon: "🧺" },
  ]

  roomsData.forEach((roomData) => {
    const room = appState.rooms[roomData.id]
    if (!room) return

    const card = document.createElement("div")
    card.className = "room-card"
    card.innerHTML = `
            <div class="room-header">
                <span class="room-icon">${roomData.icon}</span>
                <span class="room-name">${roomData.name}</span>
            </div>
            <!-- Tambah occupancy status badge -->
            <div class="room-occupancy">
                <span class="status-label">Ruangan</span>
                <span class="occupancy-badge ${room.occupied ? "occupied" : ""}" 
                      onclick="setRoomOccupied('${roomData.id}', ${!room.occupied})">
                    ${room.occupied ? "✓ Ditempati" : "◯ Kosong"}
                </span>
            </div>
            <div class="room-status">
                <span class="status-label">Lampu</span>
                <span class="status-badge-small ${room.light ? "on" : "off"}">
                    ${room.light ? "Nyala" : "Mati"}
                </span>
            </div>
            <!-- Light control dengan icon dan animasi -->
            <div class="light-control">
                <span class="light-icon ${room.light ? "on" : ""}">💡</span>
                <button class="light-toggle ${room.light ? "on" : ""}" 
                        onclick="toggleRoomLight('${roomData.id}')"></button>
            </div>
        `
    grid.appendChild(card)
  })
}

function renderDevices() {
  const grid = document.getElementById("devicesGrid")
  grid.innerHTML = ""

  const devicesData = [
    { id: "mesin_cuci", name: "Mesin Cuci", icon: "🔄", type: "Ruang Cuci" },
    { id: "pompa_air", name: "Pompa Air", icon: "💧", type: "Ruang Cuci" },
    { id: "kompor", name: "Kompor", icon: "🔥", type: "Dapur" },
  ]

  devicesData.forEach((deviceData) => {
    const device = appState.devices[deviceData.id]
    if (!device) return

    const card = document.createElement("div")
    card.className = "device-card"
    card.innerHTML = `
            <div class="device-icon ${device.status ? "active" : ""}">${deviceData.icon}</div>
            <div class="device-name">${deviceData.name}</div>
            <div class="device-type">${deviceData.type}</div>
            <div class="device-status">
                <div class="status-indicator ${device.status ? "active" : ""}"></div>
                <span class="device-status-text">${device.status ? "Aktif" : "Tidak Aktif"}</span>
            </div>
            <!-- Button on/off dengan warna berbeda saat active -->
            <button class="btn-device-control ${device.status ? "active" : ""}" 
                    onclick="toggleDevice('${deviceData.id}')">
                ${device.status ? "⊗ Matikan" : "⊙ Nyalakan"}
            </button>
        `
    grid.appendChild(card)
  })
}

function renderNotifications() {
  const container = document.getElementById("notificationsContainer")

  if (appState.notifications.length === 0) {
    container.innerHTML = '<p class="empty-state">Tidak ada notifikasi</p>'
    return
  }

  container.innerHTML = appState.notifications
    .map(
      (notif) => `
        <div class="notification-item ${notif.type}">
            <div class="notification-content">
                <div class="notification-message">${notif.message}</div>
                <div class="notification-time">${notif.timestamp}</div>
            </div>
        </div>
    `,
    )
    .join("")
}

function renderLogs() {
  const container = document.getElementById("logsContainer").querySelector(".logs-content")

  if (appState.logs.length === 0) {
    container.innerHTML = '<div class="log-item empty"><span>Tidak ada aktivitas</span></div>'
    return
  }

  const reversedLogs = [...appState.logs].reverse()
  container.innerHTML = reversedLogs
    .map(
      (log) => `
        <div class="log-item">
            <span class="log-timestamp">${log.timestamp}</span>
            <div class="log-action">
                <div class="log-action-type">${log.action}</div>
                <div class="log-action-details">${log.details}</div>
            </div>
        </div>
    `,
    )
    .join("")
}

function updateUI() {
  // Update house status
  const statusText = document.getElementById("statusText")
  const statusDot = document.querySelector(".status-dot")
  const houseSummary = document.getElementById("houseSummary")
  const statusButtons = document.querySelectorAll(".btn-status")

  statusText.textContent = appState.houseStatus === "kosong" ? "Kosong" : "Berpenghuni"

  statusDot.className = `status-dot ${appState.houseStatus}`
  houseSummary.textContent = appState.houseStatus === "kosong" ? "Kosong" : "Berpenghuni"

  statusButtons.forEach((btn) => {
    const btnStatus = btn.dataset.status
    if (btnStatus === appState.houseStatus) {
      btn.classList.add("active")
    } else {
      btn.classList.remove("active")
    }
  })

  const lightsOn = Object.values(appState.rooms).filter((r) => r.light).length
  const lightsTotal = Object.keys(appState.rooms).length
  document.getElementById("lightsCount").textContent = `${lightsOn}/${lightsTotal}`

  const devicesActive = Object.values(appState.devices).filter((d) => d.status).length
  const devicesTotal = Object.keys(appState.devices).length
  document.getElementById("devicesCount").textContent = `${devicesActive}/${devicesTotal}`

  // Update all controls buttons
  const turnOffLights = document.getElementById("turnOffAllLights")
  const turnOffDevices = document.getElementById("turnOffAllDevices")

  turnOffLights.disabled = appState.houseStatus !== "kosong"
  turnOffDevices.disabled = appState.houseStatus !== "kosong"

  // Update UI components
  renderRooms()
  renderDevices()
  renderNotifications()
  renderLogs()
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function startClock() {
  function updateClock() {
    const now = new Date()
    const time = now.toLocaleTimeString("id-ID", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
    document.getElementById("clock").textContent = time
  }

  updateClock()
  setInterval(updateClock, 1000)
}

function showNotification(message, type = "info") {
  console.log(`[${type}] ${message}`)
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
  // Event listeners sudah inline di HTML (onclick)
}

// Export functions for HTML onclick
window.toggleRoomLight = toggleRoomLight
window.toggleDevice = toggleDevice
window.turnOffAllLights = turnOffAllLights
window.turnOffAllDevices = turnOffAllDevices
window.setHouseStatus = setHouseStatus
window.setRoomOccupied = setRoomOccupied
