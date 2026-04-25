const API = window.location.origin;
const IS_NATIVE = !!(window.Capacitor && window.Capacitor.isNativePlatform());

let _deferredInstallPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    _deferredInstallPrompt = e;
});

function getToken() {
    return localStorage.getItem("token");
}

function setToken(token) {
    localStorage.setItem("token", token);
}

function clearToken() {
    localStorage.removeItem("token");
}

async function api(path, opts = {}) {
    const token = getToken();
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Request failed");
    }
    return res.json();
}

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

let _clientConfig = null;

async function getClientConfig() {
    if (_clientConfig) return _clientConfig;
    const res = await fetch("/api/config");
    _clientConfig = await res.json();
    return _clientConfig;
}

function getTrialStatus(user) {
    if (user.has_paid) return { active: true, paid: true };
    if (!user.trial_ends_at) return { active: false, paid: false, expired: true, daysLeft: 0 };
    const ends = new Date(user.trial_ends_at);
    const now = new Date();
    const ms = ends - now;
    if (ms <= 0) return { active: false, paid: false, expired: true, daysLeft: 0 };
    return { active: true, paid: false, expired: false, daysLeft: Math.ceil(ms / 86400000) };
}

function showTrialBanner(daysLeft) {
    let existing = document.getElementById("trial-banner");
    if (existing) existing.remove();
    const banner = document.createElement("div");
    banner.id = "trial-banner";
    const urgent = daysLeft <= 2;
    banner.style.cssText = `padding:10px 16px;text-align:center;font-size:13px;font-weight:500;cursor:pointer;border-bottom:1px solid var(--border);transition:background .15s;${urgent ? "background:rgba(233,69,96,0.12);color:var(--accent)" : "background:rgba(78,204,163,0.08);color:var(--success)"}`;
    banner.innerHTML = urgent
        ? `⚠️ ${daysLeft} day${daysLeft === 1 ? "" : "s"} left in your trial · <strong style="text-decoration:underline">Upgrade — $5 forever</strong>`
        : `🛡️ Free trial · ${daysLeft} day${daysLeft === 1 ? "" : "s"} remaining · <span style="text-decoration:underline">Upgrade</span>`;
    banner.addEventListener("click", () => showPaywall());
    const header = document.getElementById("app-header");
    header.parentNode.insertBefore(banner, header.nextSibling);
}

async function showPaywall() {
    const mainScreen = document.getElementById("main-screen");
    const nav = document.getElementById("bottom-nav");
    if (nav) nav.style.display = "none";
    mainScreen.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;text-align:center;padding:24px">
            <div style="font-size:56px;margin-bottom:20px">🛑</div>
            <h2 style="font-size:26px;font-weight:700;margin-bottom:6px;color:var(--text)">Your trial has ended</h2>
            <p style="color:var(--text-secondary);margin-bottom:8px;font-size:14px;line-height:1.6">
                Check-in reminders and escalation alerts are paused.
            </p>
            <p style="color:var(--text-muted);margin-bottom:28px;max-width:380px;font-size:13px;line-height:1.6">
                Pay once to reactivate everything — your contacts, settings, and history are all still here.
            </p>
            <button id="pay-btn" style="background:var(--success);color:#0a0a14;padding:16px 44px;border:none;border-radius:10px;font-size:18px;font-weight:700;cursor:pointer;margin-bottom:8px;letter-spacing:-0.3px">
                Pay $5 — Yours Forever
            </button>
            <p style="color:var(--text-muted);font-size:11px;margin-bottom:20px">One-time payment · No subscriptions · Appears as <strong style="color:var(--text-secondary)">Sahaj Tech LLC</strong></p>
            <button id="pay-later-btn" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:13px;text-decoration:underline">Log out</button>
            <div id="pay-error" style="color:var(--accent);margin-top:12px;font-size:14px"></div>
        </div>
    `;
    document.getElementById("pay-btn").addEventListener("click", async () => {
        const btn = document.getElementById("pay-btn");
        btn.disabled = true;
        btn.textContent = "Redirecting to checkout...";
        try {
            const data = await api("/stripe/checkout", { method: "POST" });
            window.location.href = data.url;
        } catch(e) {
            document.getElementById("pay-error").textContent = e.message || "Checkout failed — try again.";
            btn.disabled = false;
            btn.textContent = "Pay $5 — Yours Forever";
        }
    });
    document.getElementById("pay-later-btn").addEventListener("click", () => {
        clearToken();
        showScreen("auth");
    });
}

function showScreen(id) {
    const header = document.getElementById("app-header");
    const nav = document.getElementById("bottom-nav");
    document.getElementById("auth-screen").style.display = id === "auth" ? "flex" : "none";
    document.getElementById("main-screen").style.display = id === "main" ? "flex" : "none";
    if (header) header.style.display = id === "main" ? "" : "none";
    if (nav) nav.style.display = id === "main" ? "flex" : "none";
}

function switchTab(tabName) {
    document.querySelectorAll(".tab-panel").forEach((p) => {
        p.classList.remove("active");
        p.style.display = "none";
    });
    const target = document.getElementById("tab-" + tabName);
    if (target) {
        target.classList.add("active");
        target.style.display = "block";
    }
    document.querySelectorAll(".nav-item").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
    if (tabName === "activity") loadActivity();
    if (tabName === "contacts") { loadGroups(); loadMutual(); }
    if (tabName === "settings") { loadFamily(); loadSensors(); loadApiKeys(); loadNetcore(); loadDeadLetters(); }
}

function showToast(message, type) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("toast-visible"));
    setTimeout(() => {
        toast.classList.remove("toast-visible");
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

document.getElementById("login-btn").addEventListener("click", async () => {
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    if (!email || !password) {
        document.getElementById("login-error").textContent = "Please fill in all fields";
        return;
    }
    try {
        const data = await api("/users/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });
        setToken(data.token);
        await loadMain();
    } catch (e) {
        document.getElementById("login-error").textContent = e.message;
    }
});

document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.getElementById("checkin-btn").addEventListener("click", async () => {
    const btn = document.getElementById("checkin-btn");
    btn.disabled = true;
    try {
        const body = {};
        if (navigator.geolocation) {
            try {
                const pos = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
                });
                body.lat = pos.coords.latitude;
                body.lng = pos.coords.longitude;
            } catch {}
        }
        const data = await api("/checkin", { method: "POST", body: JSON.stringify(body) });
        showToast("Checked in! ✓", "success");
        document.getElementById("note-input-wrap").style.display = "";
        btn.textContent = "✓ Still Here";
        btn.classList.add("checked-in");
        await loadStatus();
        await loadBuddyStatus();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
    }
});

document.getElementById("save-note-btn").addEventListener("click", async () => {
    const note = document.getElementById("checkin-note").value.trim();
    if (!note) return;
    try {
        await api("/checkin/note", { method: "PATCH", body: JSON.stringify({ note }) });
        showToast("Note saved", "success");
        document.getElementById("note-input-wrap").style.display = "none";
    } catch (e) {
        showToast(e.message, "error");
    }
});

document.getElementById("add-contact-toggle").addEventListener("click", () => {
    document.getElementById("add-contact-modal").style.display = "";
});

document.getElementById("cancel-contact-btn").addEventListener("click", () => {
    document.getElementById("add-contact-modal").style.display = "none";
    document.getElementById("contact-name").value = "";
    document.getElementById("contact-phone").value = "";
    document.getElementById("contact-email").value = "";
    document.getElementById("contacts-error").textContent = "";
});

document.getElementById("add-contact-btn").addEventListener("click", async () => {
    const name = document.getElementById("contact-name").value.trim();
    const phone = document.getElementById("contact-phone").value.trim();
    const email = document.getElementById("contact-email").value.trim() || null;
    if (!name || !phone) {
        document.getElementById("contacts-error").textContent = "Name and phone are required";
        return;
    }
    try {
        await api("/contacts", {
            method: "POST",
            body: JSON.stringify({ name, phone, email }),
        });
        document.getElementById("add-contact-modal").style.display = "none";
        document.getElementById("contact-name").value = "";
        document.getElementById("contact-phone").value = "";
        document.getElementById("contact-email").value = "";
        document.getElementById("contacts-error").textContent = "";
        showToast("Contact added!", "success");
        await loadContacts();
    } catch (e) {
        document.getElementById("contacts-error").textContent = e.message;
    }
});

document.getElementById("save-settings-btn").addEventListener("click", async () => {
    const checkin_time = document.getElementById("setting-checkin-time").value;
    const grace_minutes = parseInt(document.getElementById("setting-grace").value);
    const retry_count = parseInt(document.getElementById("setting-retries").value);
    const retry_interval_hours = parseInt(document.getElementById("setting-interval").value);
    const contact_grace_hours = parseInt(document.getElementById("setting-contact-grace").value);
    const confirm_by_minutes = parseInt(document.getElementById("setting-confirm-by").value);
    const streak_reminder_hours = parseInt(document.getElementById("setting-streak-reminder").value);
    if (!checkin_time || isNaN(grace_minutes) || isNaN(retry_count) || isNaN(retry_interval_hours) || isNaN(contact_grace_hours) || isNaN(confirm_by_minutes)) {
        document.getElementById("settings-error").textContent = "Please fill in all settings";
        return;
    }
    try {
        await api("/users/me", {
            method: "PATCH",
            body: JSON.stringify({ checkin_time, grace_minutes, retry_count, retry_interval_hours, contact_grace_hours, confirm_by_minutes, streak_reminder_hours }),
        });
        document.getElementById("settings-error").textContent = "";
        showToast("Settings saved", "success");
    } catch (e) {
        document.getElementById("settings-error").textContent = e.message;
    }
});

document.getElementById("dry-run-btn").addEventListener("click", async () => {
    const btn = document.getElementById("dry-run-btn");
    btn.disabled = true;
    btn.textContent = "Running test...";
    try {
        const data = await api("/api/demo/dry-run", { method: "POST" });
        const list = data.preview || [];
        if (list.length === 0) {
            showToast("Add contacts first to test escalation", "error");
            return;
        }
        let msg = `Dry run complete! ${list.length} contacts would receive:\n\n`;
        list.forEach(p => {
            msg += `${p.contact_name} (${p.contact_phone}):\n"${p.sms_text}"\n\n`;
        });
        alert(msg);
        showToast(`Dry run sent to ${list.length} contacts (simulated)`, "success");
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Test My Setup (Dry Run)";
    }
});

document.getElementById("save-notif-prefs-btn").addEventListener("click", async () => {
    const notify_push = document.getElementById("pref-push").checked;
    const notify_email = document.getElementById("pref-email").checked;
    const notify_sms = document.getElementById("pref-sms").checked;
    const notify_weekly_digest = document.getElementById("pref-digest").checked;
    const quiet_hours_start = document.getElementById("quiet-start").value || null;
    const quiet_hours_end = document.getElementById("quiet-end").value || null;
    if ((quiet_hours_start && !quiet_hours_end) || (!quiet_hours_start && quiet_hours_end)) {
        showToast("Set both quiet hours start and end, or clear both", "error");
        return;
    }
    try {
        await api("/users/me", {
            method: "PATCH",
            body: JSON.stringify({ notify_push, notify_email, notify_sms, notify_weekly_digest, quiet_hours_start, quiet_hours_end }),
        });
        showToast("Notification preferences saved", "success");
    } catch (e) {
        showToast(e.message, "error");
    }
});

function loadNonEmergencyDisplay(phone, verified) {
    const el = document.getElementById("ne-lookup-result");
    if (!el) return;
    document.getElementById("ne-phone").textContent = phone;
    document.getElementById("ne-dept").textContent = verified ? "Verified" : "Saved (unverified)";
    document.getElementById("ne-source").style.display = "none";
    el.style.display = "";
}

document.getElementById("addr-lookup-btn").addEventListener("click", async () => {
    const city = document.getElementById("addr-city").value.trim();
    const state = document.getElementById("addr-state").value.trim();
    const errEl = document.getElementById("addr-error");
    errEl.textContent = "";
    if (!city || !state) { errEl.textContent = "City and state are required for lookup"; return; }
    try {
        const data = await api("/safety/lookup-non-emergency", {
            method: "POST",
            body: JSON.stringify({ city, state }),
        });
        if (data.phone) {
            document.getElementById("ne-phone").textContent = data.phone;
            document.getElementById("ne-dept").textContent = data.department || city + " Non-Emergency";
            const srcLink = document.getElementById("ne-source");
            if (data.source_url) { srcLink.href = data.source_url; srcLink.style.display = ""; }
            else { srcLink.style.display = "none"; }
            document.getElementById("ne-lookup-result").style.display = "";
        } else {
            errEl.textContent = "No number found for " + city + ", " + state + ". You can enter one manually during save.";
        }
    } catch (e) {
        errEl.textContent = e.message;
    }
});

document.getElementById("addr-save-btn").addEventListener("click", async () => {
    const address = document.getElementById("addr-street").value.trim();
    const city = document.getElementById("addr-city").value.trim();
    const state = document.getElementById("addr-state").value.trim();
    const zip_code = document.getElementById("addr-zip").value.trim();
    const errEl = document.getElementById("addr-error");
    errEl.textContent = "";
    if (!city || !state) { errEl.textContent = "City and state are required"; return; }
    try {
        await api("/users/me", {
            method: "PATCH",
            body: JSON.stringify({ address, city, state, zip_code }),
        });
        // Try to save non-emergency number if looked up
        const nePhone = document.getElementById("ne-phone").textContent;
        if (nePhone) {
            try {
                await api("/safety/save-address", {
                    method: "POST",
                    body: JSON.stringify({ address, city, state, zip_code, non_emergency_number: nePhone, verified: false }),
                });
            } catch (_) {}
        }
        showToast("Address saved", "success");
    } catch (e) {
        errEl.textContent = e.message;
    }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
    try { await api("/users/logout", { method: "POST" }); } catch {}
    clearToken();
    showScreen("auth");
    showToast("Logged out", "success");
});

let _countdownInterval = null;
let _currentUser = null;

function startCountdown(checkinTime, userTimezone) {
    if (_countdownInterval) clearInterval(_countdownInterval);
    const el = document.getElementById("stat-next");
    function update() {
        if (!checkinTime) { el.textContent = "--:--"; return; }
        const tz = userTimezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
        const now = new Date();
        // Get current date in user's timezone
        const localDateStr = now.toLocaleDateString("en-CA", { timeZone: tz });
        const [h, m] = checkinTime.slice(0, 5).split(":").map(Number);
        // Build target as "YYYY-MM-DD HH:MM" in user's timezone
        const targetStr = localDateStr + "T" + String(h).padStart(2,"0") + ":" + String(m).padStart(2,"0") + ":00";
        // Parse in user's timezone by formatting back
        const fmtOpts = { timeZone: tz, year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit", hour12: false };
        // Simple approach: compute offset and adjust
        const target = new Date(targetStr);
        const nowInTz = new Date(now.toLocaleString("en-US", { timeZone: tz }));
        const targetInTz = new Date(new Date().toLocaleString("en-US", { timeZone: tz }));
        targetInTz.setHours(h, m, 0, 0);
        if (targetInTz <= nowInTz) targetInTz.setDate(targetInTz.getDate() + 1);
        const diff = targetInTz - nowInTz;
        const hrs = Math.floor(diff / 3600000);
        const mins = Math.floor((diff % 3600000) / 60000);
        el.textContent = hrs + "h " + mins + "m";
    }
    update();
    _countdownInterval = setInterval(update, 60000);
}

async function loadMain() {
    showScreen("main");
    switchTab("home");
    const me = await api("/users/me");
    _currentUser = me;
    document.getElementById("profile-name").textContent = me.name || "";
    document.getElementById("profile-email").textContent = me.email || "";
    document.getElementById("setting-checkin-time").value = (me.checkin_time || "09:00").slice(0, 5);
    document.getElementById("setting-grace").value = me.grace_minutes || 120;
    document.getElementById("setting-retries").value = me.retry_count || 3;
    document.getElementById("setting-interval").value = me.retry_interval_hours || 8;
    document.getElementById("setting-contact-grace").value = me.contact_grace_hours || 48;
    document.getElementById("setting-confirm-by").value = me.confirm_by_minutes || 0;
    document.getElementById("setting-streak-reminder").value = me.streak_reminder_hours || 2;
    updateSnoozeStatus(me.snooze_until);
    const vacStartEl = document.getElementById("vacation-start");
    const vacEndEl = document.getElementById("vacation-end");
    if (vacStartEl) vacStartEl.value = me.vacation_start ? utcToLocalInput(me.vacation_start) : "";
    if (vacEndEl) vacEndEl.value = me.vacation_end ? utcToLocalInput(me.vacation_end) : "";
    updateVacationStatus(me.vacation_start, me.vacation_end);
    startCountdown(me.checkin_time, me.timezone);

    // Show timezone label
    const tzLabel = document.getElementById("tz-label");
    if (tzLabel) tzLabel.textContent = "(" + (me.timezone || "UTC") + ")";

    // Load address fields
    const addrStreet = document.getElementById("addr-street");
    const addrCity = document.getElementById("addr-city");
    const addrState = document.getElementById("addr-state");
    const addrZip = document.getElementById("addr-zip");
    if (addrStreet) addrStreet.value = me.address || "";
    if (addrCity) addrCity.value = me.city || "";
    if (addrState) addrState.value = me.state || "";
    if (addrZip) addrZip.value = me.zip_code || "";
    if (me.non_emergency_number) {
        loadNonEmergencyDisplay(me.non_emergency_number, me.non_emergency_verified);
    }

    // Load notification preferences
    const prefPush = document.getElementById("pref-push");
    const prefEmail = document.getElementById("pref-email");
    const prefSms = document.getElementById("pref-sms");
    const prefDigest = document.getElementById("pref-digest");
    const quietStart = document.getElementById("quiet-start");
    const quietEnd = document.getElementById("quiet-end");
    if (prefPush) prefPush.checked = me.notify_push !== false;
    if (prefEmail) prefEmail.checked = me.notify_email !== false;
    if (prefSms) prefSms.checked = me.notify_sms !== false;
    if (prefDigest) prefDigest.checked = me.notify_weekly_digest !== false;
    if (quietStart) quietStart.value = (me.quiet_hours_start || "").slice(0, 5);
    if (quietEnd) quietEnd.value = (me.quiet_hours_end || "").slice(0, 5);

    maybeShowTosGate(me, () => {});

    const trial = getTrialStatus(me);
    const params = new URLSearchParams(window.location.search);

    if (params.get("paid") === "1") {
        if (!me.has_paid) {
            showToast("Payment processing... refreshing in 3s", "success");
            setTimeout(() => window.location.reload(), 3000);
            return;
        }
        window.history.replaceState({}, document.title, "/signin");
        showToast("Payment confirmed! Welcome to Still Here. ✓", "success");
    }

    if (!trial.active) {
        await showPaywall();
        return;
    }

    if (!trial.paid) {
        showTrialBanner(trial.daysLeft);
    }

    await Promise.all([loadStatus(), loadStats(me), loadContacts(), loadBuddyStatus(), loadActivityTimer()]);
    maybeShowOnboarding();
    maybeShowPushNudge();
    api("/checkin/prompt").then(d => {
        const el = document.getElementById("daily-prompt");
        if (el && d.prompt) {
            el.textContent = "💡 " + d.prompt;
            el.style.display = "";
        }
    }).catch(() => {});
    maybeShowNotifPrompt();
}

async function loadStatus() {
    const status = await api("/checkin/status");
    const card = document.getElementById("status-card");
    const icon = document.getElementById("status-icon");
    const text = document.getElementById("status-text");
    const btn = document.getElementById("checkin-btn");
    const confirmWrap = document.getElementById("user-confirm-wrap");
    card.classList.remove("status-ok", "status-warn", "status-escalation");
    if (confirmWrap) confirmWrap.style.display = "none";

    const cancelBtn = document.getElementById("cancel-escalation-btn");
    if (cancelBtn) cancelBtn.style.display = "none";

    const vacationBanner = document.getElementById("vacation-banner");
    if (vacationBanner) vacationBanner.style.display = status.on_vacation ? "" : "none";

    if (status.active_escalation) {
        icon.textContent = "🚨";
        text.textContent = "Escalation active — your contacts have been notified";
        card.classList.add("status-escalation");
        if (confirmWrap) confirmWrap.style.display = "";
        if (cancelBtn) cancelBtn.style.display = "";
    } else if (status.checked_in_today) {
        icon.textContent = "✅";
        text.textContent = "You're checked in today";
        card.classList.add("status-ok");
        btn.textContent = "✓ Still Here";
        btn.classList.add("checked-in");
    } else {
        icon.textContent = "⚠️";
        text.textContent = "You haven't checked in yet";
        card.classList.add("status-warn");
        btn.textContent = "I'm Still Here";
        btn.classList.remove("checked-in");
    }
    const noteWrap = document.getElementById("note-input-wrap");
    if (noteWrap) noteWrap.style.display = status.checked_in_today ? "" : "none";
}

document.getElementById("user-confirm-btn").addEventListener("click", async () => {
    const btn = document.getElementById("user-confirm-btn");
    btn.disabled = true;
    try {
        const history = await api("/checkin/history");
        const esc = history.active_escalation;
        if (!esc) {
            showToast("No active escalation", "error");
            return;
        }
        const data = await api(`/confirm-user/${esc.id}`, { method: "POST" });
        if (data.status === "confirmed") {
            showToast("Confirmed! Escalation resolved. ✓", "success");
            await loadStatus();
        } else {
            showToast(data.message || "Cannot confirm yet", "error");
        }
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
    }
});

document.getElementById("cancel-escalation-btn").addEventListener("click", async () => {
    const btn = document.getElementById("cancel-escalation-btn");
    btn.disabled = true;
    try {
        const history = await api("/checkin/history");
        const esc = history.active_escalation;
        if (!esc) {
            showToast("No active escalation", "error");
            return;
        }
        const data = await api(`/escalation/${esc.id}/cancel`, { method: "POST" });
        showToast(data.message || "Escalation cancelled", "success");
        await loadStatus();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
    }
});

async function loadStats(me) {
    if (!me) me = await api("/users/me");
    const [streakData, contacts] = await Promise.all([
        api("/checkin/streak"),
        api("/contacts"),
    ]);
    document.getElementById("stat-streak").textContent = streakData.streak || 0;
    document.getElementById("stat-contacts").textContent = contacts.length || 0;
    const streakEl = document.getElementById("stat-streak");
    const streakVal = streakData.streak || 0;
    streakEl.textContent = streakVal;
    const streakLabel = document.querySelector("#quick-stats .stat-item:first-child .stat-label");
    if (streakLabel) {
        if (streakVal === 0) streakLabel.textContent = "Getting started";
        else if (streakVal < 7) streakLabel.textContent = "Day Streak";
        else if (streakVal < 31) streakLabel.textContent = "days. Someone always knew.";
        else if (streakVal < 100) streakLabel.textContent = "days strong";
        else streakLabel.textContent = "days. Someone always knew you were here.";
    }
}

async function loadContacts() {
    const contacts = await api("/contacts");
    const list = document.getElementById("contacts-list");
    list.innerHTML = "";
    try {
        const circle = await api("/contacts/circle");
        const header = document.getElementById("circle-header");
        if (header) {
            header.innerHTML = `<div style="text-align:center;padding:12px;background:#1a1a2e;border-radius:12px;margin-bottom:12px">
                <div style="font-size:32px;margin-bottom:4px">🛡️</div>
                <div style="font-size:16px;font-weight:600;color:#4ecca3">${esc(circle.message)}</div>
            </div>`;
        }
    } catch (e) {}
    if (contacts.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">👥</div>No contacts yet. Tap + to add one.</div>';
        return;
    }
    contacts.forEach((c, idx) => {
        const div = document.createElement("div");
        div.className = "contact-card";
        div.draggable = true;
        div.dataset.contactId = c.id;
        const handle = document.createElement("div");
        handle.className = "contact-drag-handle";
        handle.textContent = "⠿";
        handle.title = "Drag to reorder";
        const avatar = document.createElement("div");
        avatar.className = "contact-avatar";
        avatar.textContent = c.name.charAt(0).toUpperCase();
        const info = document.createElement("div");
        info.className = "contact-info";
        const priorityLabel = contacts.length > 1 ? `<div class="contact-priority-badge">#${idx + 1} priority</div>` : "";
        info.innerHTML =
            `<div class="contact-name">${esc(c.name)}</div>` +
            `<div class="contact-phone">${esc(c.phone)}</div>` +
            (c.email ? `<div class="contact-email">${esc(c.email)}</div>` : "") +
            priorityLabel;
        if (c.times_confirmed > 0) {
            const badge = document.createElement("span");
            badge.className = "contact-badge";
            badge.textContent = `Has your back (${c.times_confirmed}x)`;
            badge.style.cssText = "display:inline-block;font-size:11px;background:#1a2a1a;color:#4ecca3;padding:2px 8px;border-radius:4px;margin-top:4px";
            info.appendChild(badge);
        }
        const del = document.createElement("button");
        del.className = "delete-contact";
        del.textContent = "✕";
        del.addEventListener("click", async () => {
            try {
                await api(`/contacts/${c.id}`, { method: "DELETE" });
                showToast("Contact removed", "success");
                await loadContacts();
            } catch (e) {
                showToast(e.message, "error");
            }
        });
        // Drag-and-drop events
        div.addEventListener("dragstart", (e) => {
            div.classList.add("dragging");
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", c.id);
        });
        div.addEventListener("dragend", () => div.classList.remove("dragging"));
        div.addEventListener("dragover", (e) => { e.preventDefault(); div.classList.add("drag-over"); });
        div.addEventListener("dragleave", () => div.classList.remove("drag-over"));
        div.addEventListener("drop", async (e) => {
            e.preventDefault();
            div.classList.remove("drag-over");
            const cards = [...list.querySelectorAll(".contact-card")];
            const draggedId = e.dataTransfer.getData("text/plain");
            const draggedCard = list.querySelector(`[data-contact-id="${draggedId}"]`);
            if (draggedCard && draggedCard !== div) {
                list.insertBefore(draggedCard, div);
                const order = [...list.querySelectorAll(".contact-card")].map(c => c.dataset.contactId);
                try {
                    await api("/contacts/reorder", { method: "PUT", body: JSON.stringify({ order }) });
                    await loadContacts();
                } catch (err) {
                    showToast(err.message, "error");
                }
            }
        });
        div.appendChild(handle);
        div.appendChild(avatar);
        div.appendChild(info);
        div.appendChild(del);
        list.appendChild(div);
    });
}

let _auditFilter = "all";

function filterAudit(filter) {
    _auditFilter = filter;
    document.querySelectorAll(".tab-toggle").forEach((b) => {
        b.classList.toggle("active", b.dataset.filter === filter);
    });
    loadActivity();
}

document.getElementById("show-report-btn").addEventListener("click", async () => {
    const report = await api("/checkin/report");
    const card = document.getElementById("report-card");
    const btn = document.getElementById("show-report-btn");
    if (btn) btn.style.display = "none";
    card.style.display = "";
    document.getElementById("report-title").textContent = `Your ${report.year}`;
    document.getElementById("report-stats").innerHTML = `
        <div style="flex:1;min-width:80px;text-align:center;padding:8px;background:#0f0f1a;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#4ecca3">${report.total_checkins}</div>
            <div style="font-size:11px;opacity:.6">Check-ins</div>
        </div>
        <div style="flex:1;min-width:80px;text-align:center;padding:8px;background:#0f0f1a;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#4ecca3">${report.longest_streak}</div>
            <div style="font-size:11px;opacity:.6">Longest Streak</div>
        </div>
        <div style="flex:1;min-width:80px;text-align:center;padding:8px;background:#0f0f1a;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#4ecca3">${report.current_streak}</div>
            <div style="font-size:11px;opacity:.6">Current Streak</div>
        </div>`;
    const msEl = document.getElementById("report-milestones");
    if (report.milestones && report.milestones.length > 0) {
        msEl.innerHTML = '<div style="font-size:12px;opacity:.5;margin-bottom:4px">Milestones earned</div>' +
            report.milestones.map(m => `<span style="display:inline-block;padding:4px 10px;margin:2px;background:#1a2a1a;color:#4ecca3;border-radius:12px;font-size:12px">${m} days</span>`).join("");
    }
});

async function loadActivity() {
    api("/checkin/report").then(report => {
        const btn = document.getElementById("show-report-btn");
        if (report.total_checkins > 0) {
            if (btn) btn.style.display = "";
        }
    }).catch(() => {});
    const [history, streakData, auditData] = await Promise.all([
        api("/checkin/history"),
        api("/checkin/streak"),
        api("/checkin/audit").catch(() => ({ events: [] })),
    ]);
    document.getElementById("streak-number").textContent = streakData.streak || 0;
    const activityStreakEl = document.getElementById("streak-number");
    const activityStreakVal = streakData.streak || 0;
    activityStreakEl.textContent = activityStreakVal;
    const activityStreakLabel = document.querySelector("#streak-card .streak-label");
    if (activityStreakLabel) {
        if (activityStreakVal === 0) activityStreakLabel.textContent = "Start your streak today";
        else if (activityStreakVal < 7) activityStreakLabel.textContent = "Day Streak";
        else if (activityStreakVal < 31) activityStreakLabel.textContent = "days. Someone always knew.";
        else if (activityStreakVal < 100) activityStreakLabel.textContent = "days strong";
        else activityStreakLabel.textContent = "days. Someone always knew you were here.";
    }
    const bar = document.getElementById("streak-bar");
    bar.innerHTML = "";
    const checkins = history.checkins || [];
    const auditEvents = auditData.events || [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const ds = d.toISOString().slice(0, 10);
        const filled = checkins.some((c) => c.checked_in_at && c.checked_in_at.slice(0, 10) === ds);
        const box = document.createElement("div");
        box.className = "streak-box" + (filled ? " filled" : "");
        box.title = ds;
        bar.appendChild(box);
    }
    // 30-day calendar
    const grid = document.getElementById("history-cal-grid");
    if (grid) {
        grid.innerHTML = "";
        const today = new Date();
        let hitCount = 0;
        for (let i = 29; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(d.getDate() - i);
            const ds = d.toISOString().slice(0, 10);
            const isPast = i > 0;
            const hit = checkins.some(c => c.checked_in_at && c.checked_in_at.slice(0, 10) === ds);
            if (hit) hitCount++;
            const cell = document.createElement("div");
            cell.className = "hcal-cell" + (hit ? " hcal-hit" : i === 0 ? " hcal-today" : isPast ? " hcal-miss" : " hcal-future");
            const label = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
            cell.title = label + (hit ? " ✓" : "");
            grid.appendChild(cell);
        }
        const countEl = document.getElementById("history-cal-count");
        if (countEl) countEl.textContent = `${hitCount}/30`;
    }

    const list = document.getElementById("activity-list");
    list.innerHTML = "";
    const merged = [];
    checkins.forEach((c) => merged.push({ type: "checkin", time: c.checked_in_at, data: c }));
    auditEvents.forEach((e) => {
        if (e.event_type !== "checkin") {
            merged.push({ type: e.event_type, time: e.created_at, data: e });
        }
    });
    merged.sort((a, b) => new Date(b.time) - new Date(a.time));
    const filtered = _auditFilter === "all" ? merged : merged.filter((m) => {
        if (_auditFilter === "checkin") return m.type === "checkin";
        if (_auditFilter === "escalation") return m.type !== "checkin";
        return true;
    });
    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div>No activity yet</div>';
        return;
    }
    filtered.slice(0, 30).forEach((m) => {
        const item = document.createElement("div");
        item.className = "activity-item";
        const ago = timeAgo(m.time);
        if (m.type === "checkin") {
            const noteText = m.data.note ? `<br><em style="opacity:0.6;font-size:13px">${esc(m.data.note)}</em>` : "";
            item.innerHTML = `<span class="activity-icon">✓</span><div class="activity-detail"><strong>Checked in</strong>${noteText}<span class="activity-time">${esc(ago)}</span></div>`;
        } else if (m.type === "contact_confirmed") {
            const name = m.data.details?.contact_name || "Contact";
            item.innerHTML = `<span class="activity-icon">🛡️</span><div class="activity-detail"><strong>${esc(name)} confirmed</strong><span class="activity-time">${esc(ago)}</span></div>`;
        } else {
            item.innerHTML = `<span class="activity-icon">📋</span><div class="activity-detail"><strong>${esc(m.type)}</strong><span class="activity-time">${esc(ago)}</span></div>`;
        }
        list.appendChild(item);
    });
}

function timeAgo(iso) {
    if (!iso) return "";
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    const days = Math.floor(hrs / 24);
    return days + "d ago";
}

["login-email", "login-password"].forEach((id) => {
    document.getElementById(id).addEventListener("keydown", (e) => {
        if (e.key === "Enter") document.getElementById("login-btn").click();
    });
});

document.querySelectorAll(".snooze-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
        const hours = parseInt(btn.dataset.hours);
        let snoozeUntil = null;
        if (hours > 0) {
            const d = new Date(Date.now() + hours * 3600000);
            snoozeUntil = d.toISOString();
        }
        try {
            await api("/users/me", {
                method: "PATCH",
                body: JSON.stringify({ snooze_until: snoozeUntil }),
            });
            updateSnoozeStatus(snoozeUntil);
            if (snoozeUntil) btn.classList.add("active");
            showToast(snoozeUntil ? `Snoozed for ${hours}h` : "Check-ins resumed", snoozeUntil ? "warning" : "success");
        } catch (e) {
            showToast(e.message, "error");
        }
    });
});

document.getElementById("save-vacation-btn").addEventListener("click", async () => {
    const start = document.getElementById("vacation-start").value;
    const end = document.getElementById("vacation-end").value;
    if (!start || !end) {
        document.getElementById("vacation-error").textContent = "Both dates are required";
        return;
    }
    try {
        await api("/users/me", {
            method: "PATCH",
            body: JSON.stringify({
                vacation_start: new Date(start).toISOString(),
                vacation_end: new Date(end).toISOString(),
            }),
        });
        document.getElementById("vacation-error").textContent = "";
        showToast("Vacation mode saved", "success");
        updateVacationStatus(new Date(start).toISOString(), new Date(end).toISOString());
        await loadStatus();
    } catch (e) {
        document.getElementById("vacation-error").textContent = e.message;
    }
});

document.getElementById("clear-vacation-btn").addEventListener("click", async () => {
    try {
        await api("/users/me", {
            method: "PATCH",
            body: JSON.stringify({ vacation_start: null, vacation_end: null }),
        });
        document.getElementById("vacation-start").value = "";
        document.getElementById("vacation-end").value = "";
        document.getElementById("vacation-error").textContent = "";
        updateVacationStatus(null, null);
        showToast("Vacation mode cleared", "success");
        await loadStatus();
    } catch (e) {
        document.getElementById("vacation-error").textContent = e.message;
    }
});

function utcToLocalInput(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = n => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function updateSnoozeStatus(snoozeUntil) {
    const el = document.getElementById("snooze-status");
    document.querySelectorAll(".snooze-btn").forEach(b => b.classList.remove("active"));
    if (snoozeUntil && new Date(snoozeUntil) > new Date()) {
        const remaining = new Date(snoozeUntil) - new Date();
        const hrs = Math.floor(remaining / 3600000);
        const mins = Math.floor((remaining % 3600000) / 60000);
        el.textContent = `Snoozed — resumes in ${hrs}h ${mins}m`;
        el.classList.add("snoozing");
    } else {
        el.textContent = "Check-ins are active";
        el.classList.remove("snoozing");
    }
}

function updateVacationStatus(start, end) {
    const card = document.getElementById("vacation-status");
    if (!card) return;
    const now = new Date();
    const s = start ? new Date(start) : null;
    const e = end ? new Date(end) : null;
    if (s && e && now >= s && now <= e) {
        card.textContent = "Vacation active — check-ins paused";
        card.style.display = "";
    } else if (s && e && now < s) {
        card.textContent = `Scheduled: ${s.toLocaleDateString()} – ${e.toLocaleDateString()}`;
        card.style.display = "";
    } else {
        card.style.display = "none";
    }
}

function maybeShowNotifPrompt() {
    if (localStorage.getItem("notif_prompt_seen")) return;
    if (IS_NATIVE) { registerNativePush(); return; }
    if (Notification && Notification.permission === "granted") return;
    document.getElementById("notif-prompt").style.display = "";
}

document.getElementById("notif-allow-btn").addEventListener("click", async () => {
    localStorage.setItem("notif_prompt_seen", "1");
    document.getElementById("notif-prompt").style.display = "none";
    await registerPushToken();
});

function maybeShowTosGate(me, onAgree) {
    if (me.accepted_tos !== false) return;
    const gate = document.getElementById("tos-gate");
    gate.style.display = "flex";
    document.getElementById("tos-agree-btn").onclick = async () => {
        await api("/users/me", { method: "PATCH", body: JSON.stringify({ accepted_tos: true }) });
        gate.style.display = "none";
        onAgree();
    };
}

document.getElementById("notif-skip-btn").addEventListener("click", () => {
    localStorage.setItem("notif_prompt_seen", "1");
    document.getElementById("notif-prompt").style.display = "none";
});

let _firebaseInited = false;
let _nativePushInited = false;

async function registerPushToken() {
    if (IS_NATIVE) return registerNativePush();
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
    try {
        const cfg = await getClientConfig();
        const reg = await navigator.serviceWorker.ready;
        if (cfg.firebase?.apiKey) {
            if (!_firebaseInited) {
                firebase.initializeApp(cfg.firebase);
                _firebaseInited = true;
            }
            const messaging = firebase.messaging();
            messaging.onMessage((payload) => {
                new Notification(payload.notification?.title || "Still Here", { body: payload.notification?.body || "" });
            });
            const token = await messaging.getToken({ vapidKey: cfg.vapidKey, serviceWorkerRegistration: reg });
            if (token) {
                await api("/users/device-token", { method: "POST", body: JSON.stringify({ token }) });
            }
        } else if (cfg.vapidKey) {
            const sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: cfg.vapidKey,
            });
            await api("/users/web-push-subscribe", { method: "POST", body: JSON.stringify({ subscription: sub.toJSON() }) });
        }
    } catch (e) {
        console.warn("Push registration failed:", e);
    }
}

async function registerNativePush() {
    if (_nativePushInited) return;
    try {
        const { PushNotifications } = window.Capacitor.Plugins;
        const perm = await PushNotifications.requestPermissions();
        if (perm.receive !== "granted") {
            console.warn("Native push permission denied");
            return;
        }
        PushNotifications.addListener("registration", async (token) => {
            _nativePushInited = true;
            await api("/users/device-token", { method: "POST", body: JSON.stringify({ token: token.value }) });
        });
        PushNotifications.addListener("registrationError", (err) => {
            console.error("Native push registration error:", err);
        });
        PushNotifications.addListener("pushNotificationReceived", (notification) => {
            showToast(notification.body || notification.title || "Still Here", "info");
        });
        PushNotifications.addListener("pushNotificationActionPerformed", async (action) => {
            const data = action.notification?.data || {};
            if (data.quick_checkin_token) {
                try {
                    await api("/checkin/quick", { method: "POST", body: JSON.stringify({ token: data.quick_checkin_token }) });
                    showToast("Checked in!", "success");
                } catch {}
            }
        });
        await PushNotifications.register();
    } catch (e) {
        console.warn("Native push setup failed:", e);
    }
}

async function loadBuddyStatus() {
    try {
        const data = await api("/mutual/status");
        const buddies = data.buddies || [];
        const section = document.getElementById("buddy-section");
        const list = document.getElementById("buddy-list");
        if (!section || !list) return;
        if (buddies.length === 0) {
            section.style.display = "none";
            return;
        }
        section.style.display = "";
        list.innerHTML = "";
        buddies.forEach(b => {
            const card = document.createElement("div");
            card.className = "buddy-card";
            const colors = { green: "#4ecca3", yellow: "#f5a623", red: "#e94560" };
            const labels = { green: "Checked in today", yellow: "Missed today", red: "No recent check-in" };
            card.innerHTML = `<div class="buddy-name">${esc(b.buddy_name || b.buddy_email)}</div><div class="buddy-status-dot" style="background:${colors[b.status] || colors.red}" title="${labels[b.status] || ''}"></div><div class="buddy-status-label">${labels[b.status] || ''}</div>`;
            list.appendChild(card);
        });
    } catch {}
}

async function loadMutual() {
    const list = document.getElementById("mutual-list");
    if (!list) return;
    try {
        const [pending, statusData] = await Promise.all([
            api("/mutual/pending"),
            api("/mutual/status"),
        ]);
        const received = pending.received || [];
        const sent = pending.sent || [];
        const buddies = statusData.buddies || [];
        list.innerHTML = "";

        received.forEach(inv => {
            const card = document.createElement("div");
            card.className = "mutual-card";
            card.innerHTML = `<div class="mutual-card-info"><div class="mutual-card-name">${esc(inv.buddy_email || inv.email)}</div><div class="mutual-card-sub">Wants to be your buddy</div></div><div class="mutual-card-actions"><button class="btn btn-success" data-action="accept" data-pair-id="${esc(String(inv.pair_id || inv.id))}">Accept</button><button class="btn btn-outline" data-action="decline" data-pair-id="${esc(String(inv.pair_id || inv.id))}">Decline</button></div>`;
            list.appendChild(card);
        });

        sent.forEach(inv => {
            const card = document.createElement("div");
            card.className = "mutual-card";
            card.innerHTML = `<div class="mutual-card-info"><div class="mutual-card-name">${esc(inv.buddy_email || inv.email)}</div><div class="mutual-card-sub">Invite sent — waiting</div></div>`;
            list.appendChild(card);
        });

        buddies.forEach(b => {
            if (b.status === "active") {
                const lastSeen = b.last_checkin ? "Last seen: " + timeAgo(b.last_checkin) : "Never checked in";
                const card = document.createElement("div");
                card.className = "mutual-card";
                card.innerHTML = `<div class="mutual-card-info"><div class="mutual-card-name">${esc(b.buddy_name || b.buddy_email)}</div><div class="mutual-card-sub">${esc(lastSeen)}</div></div><div class="mutual-card-actions"><button class="btn btn-warning" data-action="pause" data-pair-id="${esc(String(b.pair_id))}">Pause</button><button class="btn btn-danger" data-action="end" data-pair-id="${esc(String(b.pair_id))}">End</button></div>`;
                list.appendChild(card);
            } else if (b.status === "paused") {
                const card = document.createElement("div");
                card.className = "mutual-card";
                card.innerHTML = `<div class="mutual-card-info"><div class="mutual-card-name">${esc(b.buddy_name || b.buddy_email)}</div><div class="mutual-card-sub">Paused</div></div><div class="mutual-card-actions"><button class="btn btn-success" data-action="resume" data-pair-id="${esc(String(b.pair_id))}">Resume</button><button class="btn btn-danger" data-action="end" data-pair-id="${esc(String(b.pair_id))}">End</button></div>`;
                list.appendChild(card);
            }
        });

        if (list.children.length === 0) {
            list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🤝</div>No buddies yet. Invite someone above.</div>';
        }
    } catch (e) {
        list.innerHTML = `<p class="error-text">${esc(e.message)}</p>`;
    }
}

document.getElementById("mutual-invite-btn").addEventListener("click", async () => {
    const emailEl = document.getElementById("mutual-invite-email");
    const errEl = document.getElementById("mutual-error");
    const email = emailEl.value.trim();
    errEl.textContent = "";
    if (!email) { errEl.textContent = "Enter an email address"; return; }
    try {
        await api("/mutual/invite", { method: "POST", body: JSON.stringify({ email }) });
        emailEl.value = "";
        showToast("Invite sent", "success");
        await loadMutual();
    } catch (e) {
        errEl.textContent = e.message;
    }
});

document.getElementById("mutual-list").addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    const pairId = btn.dataset.pairId;
    if (!action || !pairId) return;
    btn.disabled = true;
    try {
        await api(`/mutual/${action}/${pairId}`, { method: "POST" });
        const messages = { accept: "Buddy accepted!", decline: "Invite declined", pause: "Paused", resume: "Resumed", end: "Buddy removed" };
        showToast(messages[action] || "Done", "success");
        await loadMutual();
    } catch (e) {
        showToast(e.message, "error");
        btn.disabled = false;
    }
});

let _currentGroupId = null;

async function loadGroups() {
    try {
        const groups = await api("/groups");
        const list = document.getElementById("groups-list");
        list.innerHTML = "";
        if (groups.length === 0) {
            list.innerHTML = '<div class="empty-state" style="padding:16px"><div class="empty-state-icon">👥</div>No groups yet. Create one!</div>';
            return;
        }
        groups.forEach((g) => {
            const div = document.createElement("div");
            div.className = "group-card";
            div.innerHTML = `<div class="group-card-name">${esc(g.name)}</div><div class="group-card-meta">${new Date(g.created_at).toLocaleDateString()}</div>`;
            div.addEventListener("click", () => openGroupDetail(g.id, g.name));
            list.appendChild(div);
        });
    } catch (e) {}
}

async function openGroupDetail(groupId, groupName) {
    _currentGroupId = groupId;
    document.getElementById("group-detail-title").textContent = groupName;
    document.getElementById("group-detail-error").textContent = "";
    document.getElementById("invite-email").value = "";
    try {
        const group = await api(`/groups/${groupId}`);
        const list = document.getElementById("group-members-list");
        list.innerHTML = "";
        (group.members || []).forEach((m) => {
            const div = document.createElement("div");
            div.className = "group-member-item";
            div.innerHTML = `<span>${m.role === "admin" ? "⭐ " : ""}${m.user_id}</span>`;
            list.appendChild(div);
        });
    } catch (e) {
        document.getElementById("group-detail-error").textContent = e.message;
    }
    document.getElementById("group-detail-modal").style.display = "";
}

document.getElementById("create-group-btn").addEventListener("click", () => {
    document.getElementById("create-group-modal").style.display = "";
    document.getElementById("group-error").textContent = "";
    document.getElementById("group-name").value = "";
});

document.getElementById("cancel-group-btn").addEventListener("click", () => {
    document.getElementById("create-group-modal").style.display = "none";
});

document.getElementById("save-group-btn").addEventListener("click", async () => {
    const name = document.getElementById("group-name").value.trim();
    if (!name) {
        document.getElementById("group-error").textContent = "Name is required";
        return;
    }
    try {
        await api("/groups", { method: "POST", body: JSON.stringify({ name }) });
        document.getElementById("create-group-modal").style.display = "none";
        showToast("Group created!", "success");
        await loadGroups();
    } catch (e) {
        document.getElementById("group-error").textContent = e.message;
    }
});

document.getElementById("invite-member-btn").addEventListener("click", async () => {
    const email = document.getElementById("invite-email").value.trim();
    if (!email || !_currentGroupId) return;
    try {
        await api(`/groups/${_currentGroupId}/invite`, { method: "POST", body: JSON.stringify({ email }) });
        document.getElementById("invite-email").value = "";
        document.getElementById("group-detail-error").textContent = "";
        showToast("Member invited!", "success");
        const group = await api(`/groups/${_currentGroupId}`);
        const list = document.getElementById("group-members-list");
        list.innerHTML = "";
        (group.members || []).forEach((m) => {
            const div = document.createElement("div");
            div.className = "group-member-item";
            div.innerHTML = `<span>${m.role === "admin" ? "⭐ " : ""}${m.user_id}</span>`;
            list.appendChild(div);
        });
    } catch (e) {
        document.getElementById("group-detail-error").textContent = e.message;
    }
});

document.getElementById("leave-group-btn").addEventListener("click", async () => {
    if (!_currentGroupId) return;
    try {
        await api(`/groups/${_currentGroupId}/leave`, { method: "POST" });
        document.getElementById("group-detail-modal").style.display = "none";
        showToast("Left group", "success");
        await loadGroups();
    } catch (e) {
        document.getElementById("group-detail-error").textContent = e.message;
    }
});

document.getElementById("close-group-detail-btn").addEventListener("click", () => {
    document.getElementById("group-detail-modal").style.display = "none";
});

let _familyInviteToken = null;

function _familyStatusDot(lastCheckin) {
    if (!lastCheckin) return "dot-gray";
    const days = (Date.now() - new Date(lastCheckin).getTime()) / 86400000;
    if (days < 1) return "dot-green";
    if (days < 2) return "dot-yellow";
    return "dot-red";
}

function _familyLastSeenText(lastCheckin) {
    if (!lastCheckin) return "Never checked in";
    const days = (Date.now() - new Date(lastCheckin).getTime()) / 86400000;
    if (days < 1) return "Checked in today";
    return "Last seen " + timeAgo(lastCheckin);
}

async function loadFamily() {
    try {
        const data = await api("/family");
        const family = data.family;
        const createDiv = document.getElementById("family-create");
        const membersDiv = document.getElementById("family-members");
        const joinDiv = document.getElementById("family-join");

        joinDiv.style.display = "none";
        createDiv.style.display = "none";
        membersDiv.style.display = "none";

        const params = new URLSearchParams(window.location.search);
        const joinToken = params.get("join");
        if (joinToken) {
            try {
                const preview = await api("/family/join/" + joinToken);
                document.getElementById("family-join-name").textContent = "You've been invited to join: " + preview.family_name;
                joinDiv.style.display = "block";
            } catch {
                showToast("Invalid invite link", "error");
            }
            return;
        }

        if (!family) {
            createDiv.style.display = "block";
            return;
        }

        const isAdmin = family.admin_user_id === (_currentUser && _currentUser.id);
        document.getElementById("family-name-heading").textContent = family.name || "Family";
        membersDiv.style.display = "block";

        const adminControls = document.getElementById("family-admin-controls");
        adminControls.style.display = isAdmin ? "block" : "none";

        const disbandBtn = document.getElementById("disband-family-btn");
        if (disbandBtn) disbandBtn.style.display = isAdmin ? "" : "none";

        const list = document.getElementById("family-member-list");
        list.innerHTML = "";
        (family.members || []).forEach(m => {
            const card = document.createElement("div");
            card.className = "family-member-card";
            const dotClass = _familyStatusDot(m.last_checkin);
            const lastSeen = _familyLastSeenText(m.last_checkin);
            const initial = (m.name || m.email || "?")[0].toUpperCase();
            const isMemberAdmin = m.role === "admin";
            const removeBtn = (isAdmin && !isMemberAdmin)
                ? `<button class="family-member-remove" data-uid="${esc(m.id)}">Remove</button>`
                : "";
            card.innerHTML = `
                <div class="family-member-left">
                    <div class="family-member-avatar">${esc(initial)}</div>
                    <div class="family-member-info">
                        <div class="family-member-name">${esc(m.name || m.email)}</div>
                        <div class="family-member-meta">
                            <span class="family-status-dot ${dotClass}"></span>
                            <span class="family-member-last-seen">${esc(lastSeen)}</span>
                        </div>
                    </div>
                </div>
                <span class="family-member-role">${esc(m.role)}</span>
                ${removeBtn}
            `;
            list.appendChild(card);
        });
    } catch {}
}

async function createFamily() {
    const name = document.getElementById("family-name-input").value.trim();
    if (!name) return;
    try {
        await api("/family", { method: "POST", body: JSON.stringify({ name }) });
        showToast("Family created!", "success");
        loadFamily();
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function inviteFamilyMember() {
    const email = document.getElementById("family-invite-email").value.trim();
    if (!email) return;
    try {
        const data = await api("/family/invite", { method: "POST", body: JSON.stringify({ email }) });
        _familyInviteToken = data.token;
        const linkEl = document.getElementById("family-invite-link");
        linkEl.textContent = window.location.origin + "/signin?join=" + data.token;
        linkEl.style.display = "block";
        showToast("Invite created!", "success");
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function joinFamily(token) {
    try {
        await api("/family/join/" + token, { method: "POST" });
        showToast("Joined family!", "success");
        window.location.search = "";
    } catch (e) {
        showToast(e.message, "error");
    }
}

document.getElementById("create-family-btn")?.addEventListener("click", createFamily);
document.getElementById("family-invite-btn")?.addEventListener("click", inviteFamilyMember);

document.getElementById("family-copy-link-btn")?.addEventListener("click", async () => {
    if (!_familyInviteToken) {
        showToast("Invite someone first to get a shareable link", "error");
        return;
    }
    const link = window.location.origin + "/signin?join=" + _familyInviteToken;
    try {
        await navigator.clipboard.writeText(link);
        showToast("Invite link copied!", "success");
    } catch {
        const linkEl = document.getElementById("family-invite-link");
        linkEl.textContent = link;
        linkEl.style.display = "block";
        showToast("Link shown below — copy it manually", "success");
    }
});

document.getElementById("family-member-list")?.addEventListener("click", async (e) => {
    const btn = e.target.closest(".family-member-remove");
    if (!btn) return;
    const uid = btn.dataset.uid;
    if (!uid) return;
    if (!confirm("Remove this member from the family?")) return;
    try {
        await api("/family/remove/" + uid, { method: "POST" });
        showToast("Member removed", "success");
        loadFamily();
    } catch (e) { showToast(e.message, "error"); }
});

document.getElementById("leave-family-btn")?.addEventListener("click", async () => {
    if (!confirm("Leave this family?")) return;
    try {
        await api("/family/leave", { method: "POST" });
        showToast("Left family", "success");
        loadFamily();
    } catch (e) { showToast(e.message, "error"); }
});
document.getElementById("disband-family-btn")?.addEventListener("click", async () => {
    if (!confirm("Disband family? All members will be removed.")) return;
    try {
        await api("/family", { method: "DELETE" });
        showToast("Family disbanded", "success");
        loadFamily();
    } catch (e) { showToast(e.message, "error"); }
});
document.getElementById("family-join-btn")?.addEventListener("click", () => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("join");
    if (token) joinFamily(token);
});

async function loadSensors() {
    const list = document.getElementById("sensor-list");
    if (!list) return;
    try {
        const sensors = await api("/webhooks/sensors");
        if (!sensors.length) {
            list.innerHTML = '<p class="muted-text">No sensors registered.</p>';
            return;
        }
        list.innerHTML = sensors.map(s => `
            <div class="sensor-card">
                <div class="sensor-card-header">
                    <strong>${esc(s.sensor_type)}</strong>
                    <span class="muted-text">${esc(s.sensor_id)}</span>
                </div>
                <div class="sensor-card-reading">${s.last_reading ? esc(JSON.stringify(s.last_reading)) : 'No reading yet'}</div>
                <button class="btn-danger btn-sm" onclick="deleteSensor('${s.id}')">Remove</button>
            </div>
        `).join("");
    } catch {
        list.innerHTML = '<p class="error-text">Failed to load sensors.</p>';
    }
}

async function deleteSensor(id) {
    if (!confirm("Remove this sensor?")) return;
    await api(`/webhooks/sensors/${id}`, { method: "DELETE" });
    loadSensors();
}

document.getElementById("add-sensor-btn")?.addEventListener("click", () => {
    document.getElementById("sensor-form").style.display = "block";
    document.getElementById("add-sensor-btn").style.display = "none";
});

document.getElementById("sensor-cancel-btn")?.addEventListener("click", () => {
    document.getElementById("sensor-form").style.display = "none";
    document.getElementById("add-sensor-btn").style.display = "inline-block";
});

document.getElementById("sensor-submit-btn")?.addEventListener("click", async () => {
    const sensorType = document.getElementById("sensor-type-select").value;
    const sensorId = document.getElementById("sensor-id-input").value.trim();
    if (!sensorId) return;
    await api("/webhooks/sensor", {
        method: "POST",
        body: JSON.stringify({ sensor_type: sensorType, sensor_id: sensorId, reading: {} }),
    });
    document.getElementById("sensor-id-input").value = "";
    document.getElementById("sensor-form").style.display = "none";
    document.getElementById("add-sensor-btn").style.display = "inline-block";
    loadSensors();
});

async function loadApiKeys() {
    const list = document.getElementById("api-key-list");
    if (!list) return;
    try {
        const data = await api("/api-keys");
        const keys = data.keys || [];
        if (!keys.length) {
            list.innerHTML = '<p class="muted-text">No API keys yet.</p>';
            return;
        }
        list.innerHTML = keys.map(k => `
            <div class="api-key-card">
                <div>
                    <strong>${esc(k.name)}</strong>
                    <span class="muted-text">${k.created_at ? new Date(k.created_at).toLocaleDateString() : ''}</span>
                </div>
                <button onclick="deleteApiKey('${k.id}')" class="btn-danger btn-sm">Revoke</button>
            </div>
        `).join("");
    } catch {
        list.innerHTML = '<p class="error-text">Failed to load API keys.</p>';
    }
}

async function generateApiKey() {
    const name = prompt("Key name (e.g. Home Assistant):", "Default");
    if (name === null) return;
    try {
        const data = await api("/api-keys", {
            method: "POST",
            body: JSON.stringify({ name: name || "Default" }),
        });
        document.getElementById("api-key-value").textContent = data.key;
        document.getElementById("api-key-modal").style.display = "flex";
        loadApiKeys();
    } catch {
        showToast("Failed to generate API key");
    }
}

async function deleteApiKey(keyId) {
    if (!confirm("Revoke this API key? External services using it will stop working.")) return;
    try {
        await api(`/api-keys/${keyId}`, { method: "DELETE" });
        loadApiKeys();
    } catch {
        showToast("Failed to revoke API key");
    }
}

document.getElementById("generate-api-key-btn")?.addEventListener("click", generateApiKey);

async function loadNetcore() {
    const status = document.getElementById("netcore-status");
    const identityBlock = document.getElementById("netcore-identity-block");
    const peersBlock = document.getElementById("netcore-peers-block");
    const addBtn = document.getElementById("netcore-add-btn");
    status.textContent = "Checking Netcore connection...";
    try {
        const [identityData, deviceData, peersData] = await Promise.all([
            api("/netcore/identity"),
            api("/netcore/device"),
            api("/netcore/peers"),
        ]);
        status.textContent = "";
        identityBlock.style.display = "";
        addBtn.style.display = "";
        document.getElementById("netcore-identity-json").textContent = JSON.stringify(identityData, null, 2);
        const internalIp = deviceData.internal_ip || "";
        document.getElementById("netcore-internal-ip").textContent = internalIp;
        document.getElementById("netcore-app-url").textContent = `http://${internalIp}:8000/signin`;
        const peers = peersData.peers || [];
        if (peers.length > 0) {
            peersBlock.style.display = "";
            document.getElementById("netcore-peer-list").innerHTML = peers.map(p =>
                `<div class="netcore-peer-item">
                    <span class="netcore-peer-dot ${p.connected ? 'online' : 'offline'}"></span>
                    <span>${esc(p.device || p.pub_key_b36?.slice(0, 12) + "...")}</span>
                    <span style="opacity:.4;font-size:11px">${esc(p.internal_ip || "")}</span>
                    <button class="netcore-remove-btn btn-secondary" data-key="${esc(p.pub_key_b36)}">Remove</button>
                </div>`
            ).join("");
            document.querySelectorAll(".netcore-remove-btn").forEach(btn => {
                btn.addEventListener("click", async () => {
                    try {
                        await api(`/netcore/peer-users/${btn.dataset.key}`, { method: "DELETE" });
                        showToast("Peer removed");
                        loadNetcore();
                    } catch { showToast("Failed to remove peer", "error"); }
                });
            });
        } else {
            peersBlock.style.display = "";
            document.getElementById("netcore-peer-list").innerHTML = `<p class="settings-hint">No peers connected yet. Share your identity above to get started.</p>`;
        }
    } catch (e) {
        if (e.message?.includes("503") || e.message?.includes("not running")) {
            status.innerHTML = `<span style="color:var(--red)">Netcore client not running.</span> Start it with <code>./netcore/ncp2p</code> on your server.`;
        } else {
            status.textContent = "Netcore unavailable.";
        }
        identityBlock.style.display = "none";
        peersBlock.style.display = "none";
        addBtn.style.display = "none";
    }
}

document.getElementById("netcore-copy-btn")?.addEventListener("click", () => {
    const json = document.getElementById("netcore-identity-json").textContent;
    navigator.clipboard.writeText(json).then(() => showToast("Copied!"));
});

document.getElementById("netcore-add-btn")?.addEventListener("click", () => {
    document.getElementById("netcore-add-form").style.display = "";
    document.getElementById("netcore-add-btn").style.display = "none";
});

document.getElementById("netcore-peer-cancel-btn")?.addEventListener("click", () => {
    document.getElementById("netcore-add-form").style.display = "none";
    document.getElementById("netcore-add-btn").style.display = "";
});

document.getElementById("netcore-peer-submit-btn")?.addEventListener("click", async () => {
    const raw = document.getElementById("netcore-peer-json").value.trim();
    let parsed;
    try { parsed = JSON.parse(raw); } catch { showToast("Invalid JSON", "error"); return; }
    try {
        await api("/netcore/peer-users", { method: "POST", body: JSON.stringify(parsed) });
        showToast("Peer added — connection establishing");
        document.getElementById("netcore-add-form").style.display = "none";
        document.getElementById("netcore-peer-json").value = "";
        loadNetcore();
    } catch (e) { showToast(e.message || "Failed to add peer", "error"); }
});
document.getElementById("api-key-copy-btn")?.addEventListener("click", () => {
    const key = document.getElementById("api-key-value").textContent;
    navigator.clipboard.writeText(key).then(() => showToast("Copied!"));
});
document.getElementById("api-key-modal-close-btn")?.addEventListener("click", () => {
    document.getElementById("api-key-modal").style.display = "none";
});

// ─── PWA Install Sheet ───────────────────────────────────────────────────────

function isIOS() { return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream; }
function isAndroid() { return /Android/.test(navigator.userAgent); }
function isInStandaloneMode() {
    return window.navigator.standalone === true ||
           window.matchMedia("(display-mode: standalone)").matches;
}

function maybeShowPwaSheet() {
    if (IS_NATIVE) return;
    if (isInStandaloneMode()) return;
    if (!isIOS() && !isAndroid()) return;
    if (localStorage.getItem("pwa_sheet_dismissed")) return;
    const sheet = document.getElementById("pwa-sheet");
    if (isIOS()) {
        document.getElementById("pwa-ios").style.display = "";
    } else if (_deferredInstallPrompt) {
        document.getElementById("pwa-android-prompt").style.display = "";
    } else {
        document.getElementById("pwa-android-manual").style.display = "";
    }
    sheet.style.display = "flex";
}

function dismissPwaSheet() {
    localStorage.setItem("pwa_sheet_dismissed", "1");
    document.getElementById("pwa-sheet").style.display = "none";
}

async function triggerPwaInstall() {
    if (!_deferredInstallPrompt) return;
    _deferredInstallPrompt.prompt();
    const { outcome } = await _deferredInstallPrompt.userChoice;
    _deferredInstallPrompt = null;
    if (outcome === "accepted") {
        localStorage.setItem("pwa_sheet_dismissed", "1");
        document.getElementById("pwa-sheet").style.display = "none";
    }
}

// ─── Push Nudge ──────────────────────────────────────────────────────────────

function maybeShowPushNudge() {
    if (IS_NATIVE) return; // native push handled by registerNativePush
    if (!("Notification" in window)) return;
    const nudge = document.getElementById("push-nudge");
    const textEl = document.getElementById("push-nudge-text");
    const btn = document.getElementById("push-nudge-btn");
    if (Notification.permission === "default") {
        if (localStorage.getItem("push_nudge_dismissed")) return;
        textEl.textContent = "Enable notifications to receive your daily check-in.";
        btn.textContent = "Enable";
        btn.style.display = "";
        nudge.style.display = "flex";
    } else if (Notification.permission === "denied") {
        if (localStorage.getItem("push_denied_dismissed")) return;
        textEl.textContent = "Notifications are blocked. Go to browser Settings → Site Settings to re-enable.";
        btn.style.display = "none";
        nudge.style.display = "flex";
        nudge.classList.add("push-nudge-warn");
    }
}

function dismissPushNudge() {
    const key = Notification.permission === "denied" ? "push_denied_dismissed" : "push_nudge_dismissed";
    localStorage.setItem(key, "1");
    document.getElementById("push-nudge").style.display = "none";
}

async function nudgeRequestPush() {
    const permission = await Notification.requestPermission();
    document.getElementById("push-nudge").style.display = "none";
    if (permission === "granted") {
        showToast("Notifications enabled ✓", "success");
        try {
            const reg = await navigator.serviceWorker.ready;
            const cfg = await getClientConfig();
            if (cfg.vapidKey && !cfg.firebase?.apiKey) {
                const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: cfg.vapidKey });
                await api("/users/web-push-subscribe", { method: "POST", body: JSON.stringify({ subscription: sub.toJSON() }) });
            }
        } catch {}
    } else {
        maybeShowPushNudge();
    }
}

// ─── Onboarding ──────────────────────────────────────────────────────────────

let _obStep = 1;
const OB_TOTAL = 5;

function maybeShowOnboarding() {
    if (localStorage.getItem("onboarding_done")) return;
    const contacts = document.querySelectorAll(".contact-card");
    if (contacts.length > 0) { localStorage.setItem("onboarding_done", "1"); return; }
    _obStep = 1;
    obRender();
    document.getElementById("onboarding-overlay").style.display = "flex";
}

function obRender() {
    document.querySelectorAll(".onboarding-step").forEach(s => s.classList.remove("active"));
    const step = document.querySelector(`.onboarding-step[data-step="${_obStep}"]`);
    if (step) step.classList.add("active");
    const pct = _obStep === 6 ? 100 : Math.round(((_obStep - 1) / OB_TOTAL) * 100);
    document.getElementById("onboarding-progress-bar").style.width = pct + "%";
}

function obNext() {
    _obStep++;
    obRender();
}

function obBack() {
    if (_obStep > 1) { _obStep--; obRender(); }
}

function obSkip() {
    _obStep = 6;
    document.getElementById("ob-done-contact").textContent = "— Add a contact in Settings when ready";
    document.getElementById("ob-done-notif").textContent = "— Enable notifications in Settings when ready";
    obRender();
}

function obSkipContact() {
    document.getElementById("ob-done-contact").textContent = "— Add a contact in Settings when ready";
    _obStep = 4;
    obRender();
}

async function obSaveTime() {
    const timeVal = document.getElementById("ob-checkin-time").value;
    const grace = parseInt(document.getElementById("ob-grace").value);
    try {
        await api("/users/me", {
            method: "PATCH",
            body: JSON.stringify({ checkin_time: timeVal + ":00", grace_minutes: grace }),
        });
        document.getElementById("setting-checkin-time").value = timeVal;
        document.getElementById("setting-grace").value = grace;
        obNext();
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function obSaveContact() {
    const name = document.getElementById("ob-contact-name").value.trim();
    const phone = document.getElementById("ob-contact-phone").value.trim();
    const email = document.getElementById("ob-contact-email").value.trim();
    const errEl = document.getElementById("ob-contact-error");
    if (!name || !phone) { errEl.textContent = "Name and phone are required"; return; }
    errEl.textContent = "";
    try {
        await api("/contacts", {
            method: "POST",
            body: JSON.stringify({ name, phone, email: email || null }),
        });
        document.getElementById("ob-done-contact").textContent = `✓ ${name} added as your emergency contact`;
        await loadContacts();
        _obStep = 4;
        obRender();
    } catch (e) {
        errEl.textContent = e.message;
    }
}

let _obNeNumber = null;

async function obLookupAddress() {
    const city = document.getElementById("ob-city").value.trim();
    const state = document.getElementById("ob-state").value.trim().toUpperCase();
    const address = document.getElementById("ob-address").value.trim();
    const zip = document.getElementById("ob-zip").value.trim();
    const errEl = document.getElementById("ob-address-error");

    if (!city || !state) { errEl.textContent = "City and state are required"; return; }
    errEl.textContent = "";

    try {
        const data = await api("/safety/lookup-non-emergency", {
            method: "POST",
            body: JSON.stringify({ address, city, state, zip_code: zip }),
        });
        if (data.found) {
            _obNeNumber = data.phone;
            document.getElementById("ob-ne-phone").textContent = data.phone;
            document.getElementById("ob-ne-dept").textContent = data.department || "";
            const srcLink = document.getElementById("ob-ne-source");
            if (data.source_url) { srcLink.href = data.source_url; srcLink.style.display = ""; }
            else { srcLink.style.display = "none"; }
            document.getElementById("ob-ne-result").style.display = "";
            document.getElementById("ob-ne-notfound").style.display = "none";
            document.getElementById("ob-ne-manual-group").style.display = "none";
            document.getElementById("ob-ne-lookup-btn").style.display = "none";
            document.getElementById("ob-ne-save-btn").style.display = "";
        } else {
            _obNeNumber = null;
            document.getElementById("ob-ne-result").style.display = "none";
            document.getElementById("ob-ne-notfound").style.display = "";
            document.getElementById("ob-ne-manual-group").style.display = "";
            const searchLink = document.getElementById("ob-ne-search-link");
            if (data.help_links && data.help_links[0]) searchLink.href = data.help_links[0].url;
            document.getElementById("ob-ne-lookup-btn").style.display = "none";
            document.getElementById("ob-ne-save-btn").style.display = "";
        }
    } catch (e) {
        errEl.textContent = e.message || "Lookup failed";
    }
}

async function obSaveAddress() {
    const address = document.getElementById("ob-address").value.trim();
    const city = document.getElementById("ob-city").value.trim();
    const state = document.getElementById("ob-state").value.trim().toUpperCase();
    const zip = document.getElementById("ob-zip").value.trim();
    const manual = document.getElementById("ob-ne-manual").value.trim();
    const errEl = document.getElementById("ob-address-error");

    const phone = _obNeNumber || manual;
    if (!phone) { errEl.textContent = "A non-emergency number is required"; return; }
    if (!phone.startsWith("+")) { errEl.textContent = "Number must start with + (e.g. +1...)"; return; }
    errEl.textContent = "";

    try {
        await api("/safety/save-address", {
            method: "POST",
            body: JSON.stringify({
                address, city, state, zip_code: zip,
                non_emergency_number: phone,
                verified: !!_obNeNumber,
            }),
        });
        obNext();
    } catch (e) {
        errEl.textContent = e.message || "Save failed";
    }
}

async function obRequestNotif() {
    const btn = document.getElementById("ob-notif-btn");
    btn.disabled = true;
    try {
        if (IS_NATIVE) {
            await registerNativePush();
            document.getElementById("ob-notif-state").innerHTML = `<div style="color:#4ecca3;font-size:15px;font-weight:600;padding:12px 0">✓ Notifications enabled</div>`;
            document.getElementById("ob-done-notif").textContent = "✓ Notifications enabled";
            setTimeout(() => obNext(), 800);
            return;
        }
        const permission = await Notification.requestPermission();
        if (permission === "granted") {
            document.getElementById("ob-notif-state").innerHTML = `<div style="color:#4ecca3;font-size:15px;font-weight:600;padding:12px 0">✓ Notifications enabled</div>`;
            document.getElementById("ob-done-notif").textContent = "✓ Notifications enabled";
            try {
                const reg = await navigator.serviceWorker.ready;
                const cfg = await getClientConfig();
                if (cfg.firebase?.apiKey) {
                    const { initializeApp } = await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js");
                    const { getMessaging, getToken } = await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging.js");
                    const fbApp = initializeApp(cfg.firebase);
                    const messaging = getMessaging(fbApp);
                    const token = await getToken(messaging, { vapidKey: cfg.vapidKey, serviceWorkerRegistration: reg });
                    if (token) await api("/users/device-token", { method: "POST", body: JSON.stringify({ token }) });
                } else if (cfg.vapidKey) {
                    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: cfg.vapidKey });
                    await api("/users/web-push-subscribe", { method: "POST", body: JSON.stringify({ subscription: sub.toJSON() }) });
                }
            } catch {}
            setTimeout(() => obNext(), 800);
        } else {
            document.getElementById("ob-notif-state").innerHTML = `<div style="color:#e94560;font-size:14px;padding:8px 0">Notifications blocked. You can enable them in your browser settings later.</div><button class="ob-next-btn" style="margin-top:12px" onclick="obSkip()">Continue anyway →</button>`;
            document.getElementById("ob-done-notif").textContent = "— Enable notifications in browser settings";
        }
    } catch (e) {
        btn.disabled = false;
        showToast("Could not request notification permission", "error");
    }
}

function obFinish() {
    localStorage.setItem("onboarding_done", "1");
    document.getElementById("onboarding-overlay").style.display = "none";
    loadContacts();
    setTimeout(() => maybeShowPwaSheet(), 600);
}

// ─── End Onboarding ───────────────────────────────────────────────────────────

// ─── Activity Timer ────────────────────────────────────────────────────────────

let _activityTimerInterval = null;

function formatTimerCountdown(seconds) {
    if (seconds <= 0) return "00:00:00";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return [hours, minutes, secs]
        .map(v => String(v).padStart(2, '0'))
        .join(':');
}

async function loadActivityTimer() {
    try {
        const data = await api("/checkin/activity-timer");
        const section = document.getElementById("activity-timer-section");
        const display = document.getElementById("activity-timer-display");
        const form = document.getElementById("activity-timer-form");

        if (data.active) {
            document.getElementById("activity-timer-label").textContent = data.timer_label || "Activity";
            display.style.display = "";
            form.style.display = "none";
            section.style.display = "";

            // Start countdown
            if (_activityTimerInterval) clearInterval(_activityTimerInterval);
            function updateCountdown() {
                const remaining = data.time_remaining_seconds - (Date.now() - window._timerStartTime) / 1000;
                if (remaining <= 0) {
                    document.getElementById("activity-timer-countdown").textContent = "00:00:00";
                    clearInterval(_activityTimerInterval);
                } else {
                    document.getElementById("activity-timer-countdown").textContent = formatTimerCountdown(remaining);
                }
            }
            window._timerStartTime = Date.now();
            updateCountdown();
            _activityTimerInterval = setInterval(updateCountdown, 1000);
        } else {
            section.style.display = "";
            display.style.display = "none";
            form.style.display = "";
            document.getElementById("timer-hours").value = "4";
            document.getElementById("timer-label").value = "";
            if (_activityTimerInterval) clearInterval(_activityTimerInterval);
        }
    } catch (e) {
        document.getElementById("activity-timer-section").style.display = "";
    }
}

document.getElementById("start-timer-btn").addEventListener("click", async () => {
    const hours = parseFloat(document.getElementById("timer-hours").value);
    const label = document.getElementById("timer-label").value.trim();

    if (!hours || hours <= 0) {
        showToast("Please enter valid hours", "error");
        return;
    }
    if (!label) {
        showToast("Please enter activity label", "error");
        return;
    }

    try {
        const btn = document.getElementById("start-timer-btn");
        btn.disabled = true;
        await api("/checkin/activity-timer", {
            method: "POST",
            body: JSON.stringify({ hours, label }),
        });
        showToast(`Activity timer started: ${label} in ${hours} hours`, "success");
        await loadActivityTimer();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        document.getElementById("start-timer-btn").disabled = false;
    }
});

document.getElementById("cancel-timer-btn").addEventListener("click", async () => {
    try {
        const btn = document.getElementById("cancel-timer-btn");
        btn.disabled = true;
        await api("/checkin/activity-timer", { method: "DELETE" });
        showToast("Activity timer cancelled", "success");
        await loadActivityTimer();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        document.getElementById("cancel-timer-btn").disabled = false;
    }
});

// ─── Dead Letters ──────────────────────────────────────────────────────────────

let _editingDeadLetterId = null;

async function loadDeadLetters() {
    try {
        const letters = await api("/dead-letters");
        const listDiv = document.getElementById("dead-letters-list");
        listDiv.innerHTML = "";

        if (!letters || letters.length === 0) {
            listDiv.innerHTML = '<p style="opacity:0.6;font-size:13px;margin-bottom:16px">No dead letters yet.</p>';
            return;
        }

        letters.forEach(letter => {
            const card = document.createElement("div");
            card.style.cssText = "margin-bottom:12px;padding:12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:8px";
            const sentStatus = letter.sent_at
                ? `<span style="color:rgba(78,204,163,0.7);font-size:12px">Sent on ${new Date(letter.sent_at).toLocaleDateString()}</span>`
                : `<span style="color:rgba(255,193,7,0.7);font-size:12px">Unsent</span>`;
            const recipientText = letter.recipient_type === "contacts"
                ? "Emergency Contacts"
                : `Email: ${esc(letter.recipient_email || "")}`;
            card.innerHTML = `
                <div style="margin-bottom:8px">
                    <div style="font-weight:600;margin-bottom:4px">${esc(letter.subject)}</div>
                    <div style="font-size:13px;opacity:0.7">${esc(letter.trigger_days)} days without check-in → ${recipientText}</div>
                    ${sentStatus}
                </div>
                <div style="display:flex;gap:8px;font-size:13px">
                    <button class="dead-letter-edit-btn" data-id="${esc(letter.id)}" style="background:rgba(100,150,255,0.2);border:1px solid rgba(100,150,255,0.3);color:#6496ff;padding:6px 12px;border-radius:4px;cursor:pointer;flex:1">Edit</button>
                    <button class="dead-letter-delete-btn" data-id="${esc(letter.id)}" style="background:rgba(255,100,100,0.2);border:1px solid rgba(255,100,100,0.3);color:#ff6464;padding:6px 12px;border-radius:4px;cursor:pointer;flex:1">Delete</button>
                </div>
            `;
            listDiv.appendChild(card);
        });

        // Add event listeners
        document.querySelectorAll(".dead-letter-edit-btn").forEach(btn => {
            btn.addEventListener("click", () => editDeadLetter(btn.dataset.id));
        });
        document.querySelectorAll(".dead-letter-delete-btn").forEach(btn => {
            btn.addEventListener("click", () => deleteDeadLetter(btn.dataset.id));
        });
    } catch (e) {
        console.error("Failed to load dead letters:", e);
    }
}

function showDeadLetterForm(edit = false) {
    const form = document.getElementById("dead-letter-form");
    form.style.display = edit ? "block" : "block";
    if (!edit) {
        document.getElementById("dl-subject").value = "";
        document.getElementById("dl-body").value = "";
        document.getElementById("dl-days").value = "30";
        document.getElementById("dl-recipient-type").value = "contacts";
        document.getElementById("dl-email").value = "";
        document.getElementById("dl-email").style.display = "none";
        _editingDeadLetterId = null;
    }
}

function hideDeadLetterForm() {
    document.getElementById("dead-letter-form").style.display = "none";
    _editingDeadLetterId = null;
}

async function editDeadLetter(id) {
    try {
        const letter = await api(`/dead-letters/${id}`);
        _editingDeadLetterId = id;
        document.getElementById("dl-subject").value = letter.subject;
        document.getElementById("dl-body").value = letter.body;
        document.getElementById("dl-days").value = letter.trigger_days;
        document.getElementById("dl-recipient-type").value = letter.recipient_type;
        if (letter.recipient_type === "email") {
            document.getElementById("dl-email").value = letter.recipient_email || "";
            document.getElementById("dl-email").style.display = "block";
        } else {
            document.getElementById("dl-email").style.display = "none";
        }
        showDeadLetterForm(true);
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function saveDeadLetter() {
    const subject = document.getElementById("dl-subject").value.trim();
    const body = document.getElementById("dl-body").value.trim();
    const days = parseInt(document.getElementById("dl-days").value);
    const recipientType = document.getElementById("dl-recipient-type").value;
    const email = document.getElementById("dl-email").value.trim();

    if (!subject || !body) {
        showToast("Subject and message are required", "error");
        return;
    }
    if (isNaN(days) || days < 7 || days > 365) {
        showToast("Days must be between 7 and 365", "error");
        return;
    }
    if (recipientType === "email" && !email) {
        showToast("Email is required for email recipient type", "error");
        return;
    }

    const payload = {
        subject,
        body,
        trigger_days: days,
        recipient_type: recipientType,
        recipient_email: recipientType === "email" ? email : null,
    };

    try {
        const btn = document.getElementById("dl-save-btn");
        btn.disabled = true;

        if (_editingDeadLetterId) {
            await api(`/dead-letters/${_editingDeadLetterId}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });
            showToast("Dead letter updated", "success");
        } else {
            await api("/dead-letters", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            showToast("Dead letter created", "success");
        }

        hideDeadLetterForm();
        await loadDeadLetters();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        document.getElementById("dl-save-btn").disabled = false;
    }
}

async function deleteDeadLetter(id) {
    if (!confirm("Delete this dead letter?")) return;
    try {
        await api(`/dead-letters/${id}`, { method: "DELETE" });
        showToast("Dead letter deleted", "success");
        await loadDeadLetters();
    } catch (e) {
        showToast(e.message, "error");
    }
}

document.getElementById("add-dead-letter-btn").addEventListener("click", () => {
    showDeadLetterForm(false);
});

document.getElementById("dl-cancel-btn").addEventListener("click", hideDeadLetterForm);

document.getElementById("dl-save-btn").addEventListener("click", saveDeadLetter);

document.getElementById("dl-recipient-type").addEventListener("change", (e) => {
    const emailInput = document.getElementById("dl-email");
    emailInput.style.display = e.target.value === "email" ? "block" : "none";
});

// ─── End Activity Timer ────────────────────────────────────────────────────────

(async function init() {
    if (getToken()) {
        try {
            await loadMain();
        } catch {
            clearToken();
            showScreen("auth");
        }
    } else {
        showScreen("auth");
        const params = new URLSearchParams(window.location.search);
        if (params.get("verified") === "1") {
            window.history.replaceState({}, document.title, "/signin");
            showToast("Email verified! You can now log in.", "success");
        }
    }
})();
