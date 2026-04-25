importScripts("/sw-config.js");

if (self.__FIREBASE_CONFIG?.apiKey) {
    importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js");
    importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js");
    firebase.initializeApp(self.__FIREBASE_CONFIG);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage((payload) => {
        const actions = payload.data?.quick_checkin_token ? [
            { action: "checkin", title: "I'm OK" }
        ] : [];
        self.registration.showNotification(payload.notification?.title || "Still Here", {
            body: payload.notification?.body || "",
            icon: "/icons/icon-192.png",
            data: {
                url: payload.data?.url || "/signin",
                quick_checkin_token: payload.data?.quick_checkin_token
            },
            vibrate: [200, 100, 200],
            actions: actions,
        });
    });
}

self.addEventListener("push", (e) => {
    if (!e.data) return;
    let data = {};
    try { data = e.data.json(); } catch { data = { title: "Still Here", body: e.data.text() }; }
    const actions = data.quick_checkin_token ? [
        { action: "checkin", title: "I'm OK" }
    ] : [];
    e.waitUntil(
        self.registration.showNotification(data.title || "Still Here", {
            body: data.body || "",
            icon: "/icons/icon-192.png",
            data: {
                url: data.url || "/signin",
                quick_checkin_token: data.quick_checkin_token
            },
            vibrate: [200, 100, 200],
            actions: actions,
        })
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.action === "checkin") {
        // Handle "I'm OK" button tap
        const token = event.notification.data?.quick_checkin_token;
        if (token) {
            event.waitUntil(
                fetch("/checkin/quick", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token })
                }).then(r => {
                    if (r.ok) {
                        self.registration.showNotification("Still Here ✓", {
                            body: "Check-in confirmed!",
                            icon: "/icons/icon-192.png",
                        });
                    }
                }).catch(() => {})
            );
        }
    } else {
        event.waitUntil(clients.openWindow(event.notification.data?.url || "/signin"));
    }
});

const CACHE = "stillhere-v2";
const ASSETS = ["/", "/style.css", "/app.js", "/manifest.json"];

self.addEventListener("install", (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
    self.skipWaiting();
});

self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (e) => {
    e.respondWith(
        caches.match(e.request).then((cached) => {
            if (cached) return cached;
            return fetch(e.request).then((response) => {
                if (response.ok && e.request.method === "GET") {
                    const clone = response.clone();
                    caches.open(CACHE).then((c) => c.put(e.request, clone));
                }
                return response;
            });
        }).catch(() => {
            if (e.request.mode === "navigate") return caches.match("/");
        })
    );
});
