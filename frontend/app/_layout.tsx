import '../global.css';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import { View, ActivityIndicator } from 'react-native';
import { useEffect } from 'react';
import { fonts } from '@/lib/fonts';
import { useAuthStore } from '@/features/auth/store';

const queryClient = new QueryClient();

function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const segments = useSegments();
  const { isAuthenticated, isHydrated, hydrate } = useAuthStore();

  // Hydrate auth state on mount
  useEffect(() => {
    hydrate();
  }, [hydrate]);

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

  // Show loading while hydrating
  if (!isHydrated) {
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
          />
        </AuthGate>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
