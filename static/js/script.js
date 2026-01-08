// State Management
const state = {
  rooms: [
    { id: "kamar1", name: "Kamar 1", icon: "🛏️" },
    { id: "kamar2", name: "Kamar 2", icon: "🛏️" },
    { id: "kamar3", name: "Kamar 3", icon: "🛏️" },
    { id: "ruang_keluarga", name: "Ruang Keluarga", icon: "🛋️" },
    { id: "dapur", name: "Dapur", icon: "🍳" },
    { id: "ruang_cuci_baju", name: "Ruang Cuci Baju", icon: "👕" },
    { id: "kamar_mandi", name: "Kamar Mandi", icon: "🚿" },
    { id: "teras_garasi", name: "Teras/Garasi", icon: "🏠" },
  ],
  devices: [
    { id: "mesin_cuci", name: "Mesin Cuci", icon: "🌀", power: "500W" },
    { id: "pompa_air", name: "Pompa Air", icon: "💧", power: "200W" },
    { id: "kompor", name: "Kompor", icon: "🔥", power: "300W" },
  ],
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  renderRooms()
  renderDevices()
  updateStatus()
  updateClock()
  setupEventListeners()

  // Update setiap 1 detik untuk clock
  setInterval(updateClock, 1000)
  // Update setiap 500ms untuk status
  setInterval(updateStatus, 500)
})

// Update Real-time Clock
function updateClock() {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, "0")
  const minutes = String(now.getMinutes()).padStart(2, "0")
  const seconds = String(now.getSeconds()).padStart(2, "0")

  document.getElementById("realtime-clock").textContent = `${hours}:${minutes}:${seconds}`
}

// Render Rooms
function renderRooms() {
  const roomsGrid = document.getElementById("rooms-grid")
  roomsGrid.innerHTML = state.rooms
    .map(
      (room) => `
        <div class="room-card">
            <div class="card-header">
                <div>
                    <div class="card-title">${room.name}</div>
                    <div class="card-status">
                        <div class="status-indicator off" id="status-${room.id}"></div>
                        <span id="status-text-${room.id}">Mati</span>
                    </div>
                </div>
                <div class="card-icon">${room.icon}</div>
            </div>
            <div class="card-controls">
                <button class="toggle-btn" id="light-${room.id}" onclick="toggleLight('${room.id}')">
                    Lampu
                </button>
                <button class="occupancy-btn" id="occupancy-${room.id}" onclick="toggleOccupancy('${room.id}')">
                    Kosong
                </button>
            </div>
        </div>
    `,
    )
    .join("")
}

// Render Devices
function renderDevices() {
  const devicesGrid = document.getElementById("devices-grid")
  devicesGrid.innerHTML = state.devices
    .map(
      (device) => `
        <div class="device-card">
            <div class="card-header">
                <div>
                    <div class="card-title">${device.name}</div>
                    <div class="card-status">
                        <div class="status-indicator off" id="device-status-${device.id}"></div>
                        <span id="device-status-text-${device.id}">Mati</span>
                    </div>
                </div>
                <div class="card-icon">${device.icon}</div>
            </div>
            <div class="card-controls">
                <button class="toggle-btn" id="device-${device.id}" onclick="toggleDevice('${device.id}')">
                    Kontrol
                </button>
                <div style="flex: 1; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; color: var(--slate-gray); background: var(--off-white); border-radius: 8px; padding: 0.75rem;">
                    ${device.power}
                </div>
            </div>
        </div>
    `,
    )
    .join("")
}

// Setup Event Listeners
function setupEventListeners() {
  const modeBtn = document.getElementById("mode-btn")
  const allLightsBtn = document.getElementById("all-lights-btn")
  const allDevicesBtn = document.getElementById("all-devices-btn")

  modeBtn.addEventListener("click", toggleMode)
  allLightsBtn.addEventListener("click", () => toggleAllLights())
  allDevicesBtn.addEventListener("click", () => toggleAllDevices())
}

// Toggle Mode
async function toggleMode() {
  const modeBtn = document.getElementById("mode-btn")
  const isOccupied = modeBtn.classList.contains("occupied")
  const newMode = isOccupied ? "empty" : "occupied"

  try {
    const response = await fetch(`/api/set-house-mode/${newMode}`, { method: "POST" })
    const data = await response.json()

    if (data.success) {
      updateStatus()
    }
  } catch (error) {
    console.error("Error:", error)
  }
}

// Toggle Light
async function toggleLight(roomId) {
  try {
    const response = await fetch(`/api/toggle-light/${roomId}`, { method: "POST" })
    const data = await response.json()

    if (!data.success) {
      alert("Tidak bisa mengubah lampu: " + (data.error || "Error"))
    }
    updateStatus()
  } catch (error) {
    console.error("Error:", error)
  }
}

// Toggle All Lights
async function toggleAllLights() {
  try {
    const response = await fetch("/api/toggle-all-lights", { method: "POST" })
    const data = await response.json()

    if (!data.success) {
      alert("Tidak bisa mematikan semua lampu: " + (data.error || "Error"))
    }
    updateStatus()
  } catch (error) {
    console.error("Error:", error)
  }
}

// Toggle Occupancy
async function toggleOccupancy(roomId) {
  const btn = document.getElementById(`occupancy-${roomId}`)
  const isOccupied = btn.classList.contains("occupied")

  try {
    const response = await fetch(`/api/set-occupancy/${roomId}/${!isOccupied}`, { method: "POST" })
    const data = await response.json()

    if (data.success) {
      updateStatus()
    }
  } catch (error) {
    console.error("Error:", error)
  }
}

// Toggle Device
async function toggleDevice(deviceId) {
  try {
    const response = await fetch(`/api/toggle-device/${deviceId}`, { method: "POST" })
    const data = await response.json()

    if (!data.success) {
      alert("Tidak bisa mengubah perangkat: " + (data.error || "Error"))
    }
    updateStatus()
  } catch (error) {
    console.error("Error:", error)
  }
}

// Toggle All Devices
async function toggleAllDevices() {
  try {
    const response = await fetch("/api/toggle-all-devices", { method: "POST" })
    const data = await response.json()

    if (!data.success) {
      alert("Tidak bisa mematikan semua perangkat: " + (data.error || "Error"))
    }
    updateStatus()
  } catch (error) {
    console.error("Error:", error)
  }
}

// Update Status
async function updateStatus() {
  try {
    const response = await fetch("/api/status")
    const data = await response.json()
    const { status, notifications, logs } = data

    // Update Mode Button
    const modeBtn = document.getElementById("mode-btn")
    if (status.occupied) {
      modeBtn.classList.add("occupied")
      modeBtn.classList.remove("empty")
      modeBtn.textContent = "Mode: Ditempati"
    } else {
      modeBtn.classList.remove("occupied")
      modeBtn.classList.add("empty")
      modeBtn.textContent = "Mode: Kosong"
    }

    // Update Rooms
    let lightsOn = 0
    state.rooms.forEach((room) => {
      const roomData = status.rooms[room.id]
      const btn = document.getElementById(`light-${room.id}`)
      const statusIndicator = document.getElementById(`status-${room.id}`)
      const statusText = document.getElementById(`status-text-${room.id}`)
      const occupancyBtn = document.getElementById(`occupancy-${room.id}`)

      if (roomData.light) {
        btn.classList.add("active")
        statusIndicator.classList.remove("off")
        statusIndicator.classList.add("on")
        statusText.textContent = "Nyala"
        lightsOn++
      } else {
        btn.classList.remove("active")
        statusIndicator.classList.add("off")
        statusIndicator.classList.remove("on")
        statusText.textContent = "Mati"
      }

      // Update occupancy button
      if (roomData.occupancy) {
        occupancyBtn.classList.add("occupied")
        occupancyBtn.textContent = "Terisi"
      } else {
        occupancyBtn.classList.remove("occupied")
        occupancyBtn.textContent = "Kosong"
      }
    })

    // Update Devices
    let devicesActive = 0
    state.devices.forEach((device) => {
      const deviceData = status.devices[device.id]
      const btn = document.getElementById(`device-${device.id}`)
      const statusIndicator = document.getElementById(`device-status-${device.id}`)
      const statusText = document.getElementById(`device-status-text-${device.id}`)

      if (deviceData.status) {
        btn.classList.add("active")
        statusIndicator.classList.remove("off")
        statusIndicator.classList.add("on")
        statusText.textContent = "Aktif"
        devicesActive++
      } else {
        btn.classList.remove("active")
        statusIndicator.classList.add("off")
        statusIndicator.classList.remove("on")
        statusText.textContent = "Mati"
      }
    })

    // Update Summary
    document.getElementById("lights-on").textContent = lightsOn
    document.getElementById("devices-active").textContent = devicesActive
    document.getElementById("current-power").textContent = Math.round(status.energy_usage) + "W"
    document.getElementById("peak-power").textContent = Math.round(status.peak_usage) + "W"
    document.getElementById("avg-power").textContent = Math.round(status.avg_usage) + "W"
    document.getElementById("house-status").textContent = status.occupied ? "Ditempati" : "Kosong"

    // Update Energy Bar
    const energyPercentage = Math.min((status.energy_usage / 4000) * 100, 100)
    document.getElementById("energy-progress").style.width = energyPercentage + "%"
    document.getElementById("energy-percentage").textContent = Math.round(energyPercentage) + "%"

    // Enable/Disable Control Buttons
    const allLightsBtn = document.getElementById("all-lights-btn")
    const allDevicesBtn = document.getElementById("all-devices-btn")
    allLightsBtn.disabled = status.occupied
    allDevicesBtn.disabled = status.occupied

    // Update Notifications
    updateNotifications(notifications)

    // Update Logs
    updateLogs(logs)
  } catch (error) {
    console.error("Error fetching status:", error)
  }
}

// Update Notifications
function updateNotifications(notifications) {
  const container = document.getElementById("notifications")

  if (notifications.length === 0) {
    container.innerHTML = '<p class="empty-state">Tidak ada notifikasi penting</p>'
    return
  }

  container.innerHTML = notifications
    .map(
      (notif) => `
        <div class="notification ${notif.type}">
            <div class="notification-icon">${notif.icon}</div>
            <div class="notification-message">${notif.message}</div>
        </div>
    `,
    )
    .join("")
}

// Update Logs
function updateLogs(logs) {
  const container = document.getElementById("logs")

  if (logs.length === 0) {
    container.innerHTML = '<p class="empty-state">Belum ada aktivitas</p>'
    return
  }

  container.innerHTML = logs
    .map(
      (log) => `
        <div class="log-entry">
            <span class="log-time">${log.timestamp}</span>
            <span class="log-action">${log.action}</span>
            <span class="log-detail">${log.detail}</span>
        </div>
    `,
    )
    .reverse()
    .join("")
}
