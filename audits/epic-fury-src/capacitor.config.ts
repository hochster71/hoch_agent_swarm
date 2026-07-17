import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.epicfury.dashboard',
  appName: 'Epic Fury 2026',
  // Point to the live Vercel deployment — the app is server-rendered
  // so we use the remote URL rather than a local static export.
  server: {
    url: 'https://epic-fury-2026.vercel.app',
    cleartext: false,
  },
  ios: {
    scheme: 'Epic Fury 2026',
    contentInset: 'automatic',
    backgroundColor: '#09090b',       // matches zinc-950 app background
    preferredContentMode: 'mobile',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#09090b',
      showSpinner: false,
      androidScaleType: 'CENTER_CROP',
      splashFullScreen: true,
      splashImmersive: true,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#09090b',
    },
  },
}

export default config
