importScripts("/sw-config.js");

if (self.__FIREBASE_CONFIG?.apiKey) {
    importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js");
    importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js");
    firebase.initializeApp(self.__FIREBASE_CONFIG);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage((payload) => {
        self.registration.showNotification(payload.notification?.title || "Still Here", {
            body: payload.notification?.body || "",
            icon: "/icons/icon-192.png",
            data: { url: payload.data?.url || "/app" },
            vibrate: [200, 100, 200],
        });
    });
}

self.addEventListener("push", (e) => {
    if (!e.data) return;
    let data = {};
    try { data = e.data.json(); } catch { data = { title: "Still Here", body: e.data.text() }; }
    e.waitUntil(
        self.registration.showNotification(data.title || "Still Here", {
            body: data.body || "",
            icon: "/icons/icon-192.png",
            data: { url: data.url || "/app" },
            vibrate: [200, 100, 200],
        })
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data?.url || "/app"));
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
