# Still Here — Mobile App

Native iOS and Android wrapper for Still Here using Capacitor.

## Prerequisites

- Node.js 18+
- For iOS: Xcode 15+ and CocoaPods
- For Android: Android Studio with SDK 34+

## Setup

```bash
# Install dependencies
npm install

# Copy web assets and sync native projects
npm run build

# Add platforms (first time only)
npx cap add ios
npx cap add android
```

## Development

```bash
# Open in Xcode
npm run open:ios

# Open in Android Studio
npm run open:android
```

## Building

```bash
# After any frontend changes:
npm run build

# Then build from Xcode/Android Studio
```

## Architecture

- The app loads from your hosted Still Here instance (set in `capacitor.config.ts`)
- Push notifications use native APIs via `@capacitor/push-notifications`
- The PWA service worker is disabled in native mode (Capacitor handles offline)
- Frontend assets are copied from `../frontend/` via the build script

## Configuration

Edit `capacitor.config.ts` to:
- Change the app name and ID
- Modify the server URL for different environments
- Adjust splash screen, status bar, and other native settings

## Troubleshooting

### iOS build fails with CocoaPods errors
```bash
cd ios
pod install --repo-update
cd ..
```

### Android build fails
```bash
cd android
./gradlew clean
cd ..
npm run build
```

### Assets not updating
```bash
npm run build
npx cap sync
```
