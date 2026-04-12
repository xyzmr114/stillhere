importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js");

firebase.initializeApp({
    apiKey: "AIzaSyCHw-TesG0QM1y8OXgf634c2y4xHCzZsB0",
    authDomain: "still-here-64e9c.firebaseapp.com",
    projectId: "still-here-64e9c",
    storageBucket: "still-here-64e9c.firebasestorage.app",
    messagingSenderId: "497581151762",
    appId: "1:497581151762:web:55c68f60130077a3beaacb",
    measurementId: "G-RGG52ZK2ER",
});

const messaging = firebase.messaging();
messaging.onBackgroundMessage((payload) => {
    const title = payload.notification?.title || "Still Here";
    self.registration.showNotification(title, {
        body: payload.notification?.body || "You have a new notification",
        icon: "/manifest.json",
        data: { url: payload.data?.url || "/" },
        vibrate: [200, 100, 200],
    });
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data?.url || "/"));
});

const CACHE = "stillhere-v1";
const ASSETS = ["/", "/style.css", "/app.js", "/manifest.json"];

self.addEventListener("install", (e) => {
    e.waitUntil(
        caches.open(CACHE).then((c) => c.addAll(ASSETS))
    );
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
            if (e.request.mode === "navigate") {
                return caches.match("/");
            }
        })
    );
});
