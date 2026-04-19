import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.sahajtech.stillhere',
  appName: 'Still Here',
  webDir: 'www',
  server: {
    // For dev, proxy to local API. For production, set to your domain.
    url: 'https://stillhere.databunker.uk',
    cleartext: false,
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#0a0a14',
      showSpinner: false,
    },
    StatusBar: {
      style: 'dark',
      backgroundColor: '#0a0a14',
    },
  },
};

export default config;
