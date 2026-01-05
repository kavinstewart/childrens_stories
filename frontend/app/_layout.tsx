import '../global.css';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClientProvider } from '@tanstack/react-query';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import { View, ActivityIndicator } from 'react-native';
import { useEffect, useState } from 'react';
import { fonts } from '@/lib/fonts';
import { queryClient } from '@/lib/query-client';
import { useAuthStore } from '@/features/auth/store';
import { StoryCacheManager } from '@/lib/story-cache';
import { migrateFromAsyncStorage } from '@/lib/cache-storage';
import { remoteLogger } from '@/lib/remote-logger';
import { CacheSync } from '@/lib/cache-sync';

function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const segments = useSegments();
  const { isAuthenticated, isHydrated, hydrate } = useAuthStore();
  const [cacheReady, setCacheReady] = useState(false);

  // Hydrate auth state on mount
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  // Initialize cache on mount
  useEffect(() => {
    const initCache = async () => {
      try {
        // Migrate any existing AsyncStorage data to SQLite (one-time, idempotent)
        await migrateFromAsyncStorage();
        await StoryCacheManager.verifyCacheIntegrity();
        // Note: We intentionally don't call hydrateQueryClient() here.
        // React Query should only contain server URLs. Cached file:// URLs
        // are computed at render time using isCached + getSpreadPath().
      } catch (error) {
        console.error('Failed to initialize cache:', error);
      } finally {
        setCacheReady(true);
      }
    };

    initCache();
  }, []);

  // Initialize remote logger when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      remoteLogger.init();
    }
  }, [isAuthenticated]);

  // Start automatic cache sync when authenticated and cache is ready
  useEffect(() => {
    if (!isAuthenticated || !cacheReady) return;

    const unsubscribe = CacheSync.startAutoSync();
    return unsubscribe;
  }, [isAuthenticated, cacheReady]);

  // Handle auth routing
  useEffect(() => {
    if (!isHydrated) return;

    const isOnLoginPage = segments[0] === 'login';

    if (!isAuthenticated && !isOnLoginPage) {
      // Not authenticated and not on login page - redirect to login
      router.replace('/login');
    } else if (isAuthenticated && isOnLoginPage) {
      // Authenticated but on login page - redirect to home
      router.replace('/');
    }
  }, [isAuthenticated, isHydrated, segments, router]);

  // Show loading while hydrating auth or cache
  if (!isHydrated || !cacheReady) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#E0E7FF' }}>
        <ActivityIndicator size="large" color="#8B5CF6" />
      </View>
    );
  }

  return <>{children}</>;
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts(fonts);

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color="#8B5CF6" />
      </View>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <AuthGate>
          <Stack
            screenOptions={{
              headerShown: false,
              animation: 'fade',
            }}
          >
            <Stack.Screen
              name="edit-prompt"
              options={{
                presentation: 'fullScreenModal',
                animation: 'slide_from_bottom',
              }}
            />
          </Stack>
        </AuthGate>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
