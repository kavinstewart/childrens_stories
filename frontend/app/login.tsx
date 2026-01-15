import { View, Text, TextInput, Pressable, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { fontFamily } from '@/lib/fonts';
import { FloatingElement } from '@/components/animations';
import { api } from '@/lib/api';
import { useAuthStore } from '@/features/auth/store';

export default function Login() {
  const router = useRouter();
  const [pin, setPin] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setToken = useAuthStore((state) => state.setToken);

  const canSubmit = pin.trim().length >= 4;

  const handleLogin = async () => {
    if (!canSubmit) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.login({ pin: pin.trim() });
      await setToken(response.access_token);
      router.replace('/');
    } catch (err) {
      console.error('Login failed:', err);
      setError('Invalid PIN. Please try again.');
      setPin('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LinearGradient
      colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']}
      style={{ flex: 1 }}
    >
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} style={{ top: 120, left: 40 }}>
        <Text style={{ fontSize: 32, opacity: 0.3 }}>📚</Text>
      </FloatingElement>
      <FloatingElement delay={1} duration={5} style={{ top: 180, right: 50 }}>
        <Text style={{ fontSize: 28, opacity: 0.25 }}>✨</Text>
      </FloatingElement>
      <FloatingElement delay={2} duration={4.5} style={{ bottom: 200, right: 60 }}>
        <Text style={{ fontSize: 32, opacity: 0.3 }}>🌟</Text>
      </FloatingElement>
      <FloatingElement delay={0.5} duration={5} style={{ bottom: 150, left: 50 }}>
        <Text style={{ fontSize: 28, opacity: 0.25 }}>🔮</Text>
      </FloatingElement>

      <SafeAreaView style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
        {/* Title */}
        <View style={{ alignItems: 'center', marginBottom: 48 }}>
          <Text style={{ fontSize: 48, marginBottom: 16 }}>📖</Text>
          <Text
            style={{
              fontFamily: fontFamily.baloo,
              fontSize: 36,
              color: '#7C3AED',
              textAlign: 'center',
            }}
          >
            Story Time
          </Text>
          <Text
            style={{
              fontFamily: fontFamily.nunito,
              fontSize: 16,
              color: '#6B7280',
              textAlign: 'center',
              marginTop: 8,
            }}
          >
            Enter your PIN to continue
          </Text>
        </View>

        {/* PIN Input Card */}
        <View
          style={{
            backgroundColor: 'rgba(255,255,255,0.9)',
            borderRadius: 24,
            padding: 24,
            marginBottom: 24,
            shadowColor: '#8B5CF6',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.15,
            shadowRadius: 12,
            elevation: 8,
          }}
        >
          <TextInput
            value={pin}
            onChangeText={setPin}
            placeholder="Enter PIN"
            placeholderTextColor="#9CA3AF"
            keyboardType="number-pad"
            secureTextEntry
            maxLength={8}
            autoFocus
            style={{
              fontFamily: fontFamily.nunitoBold,
              fontSize: 32,
              color: '#374151',
              backgroundColor: '#F9FAFB',
              borderRadius: 16,
              padding: 20,
              textAlign: 'center',
              letterSpacing: 8,
            }}
            onSubmitEditing={handleLogin}
          />
        </View>

        {/* Error Message */}
        {error && (
          <View
            style={{
              backgroundColor: '#FEE2E2',
              borderRadius: 16,
              padding: 16,
              marginBottom: 24,
            }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunitoBold,
                color: '#DC2626',
                textAlign: 'center',
              }}
            >
              {error}
            </Text>
          </View>
        )}

        {/* Login Button */}
        <Pressable
          onPress={handleLogin}
          disabled={!canSubmit || isLoading}
        >
          {({ pressed }) => (
            <LinearGradient
              colors={
                canSubmit && !isLoading
                  ? ['#EC4899', '#8B5CF6', '#6366F1']
                  : ['#D1D5DB', '#9CA3AF', '#9CA3AF']
              }
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={{
                paddingVertical: 18,
                borderRadius: 16,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                shadowColor: canSubmit ? '#8B5CF6' : '#9CA3AF',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.3,
                shadowRadius: 8,
                elevation: 8,
                transform: [{ scale: pressed ? 0.98 : 1 }],
              }}
            >
              {isLoading ? (
                <>
                  <ActivityIndicator color="white" />
                  <Text
                    style={{
                      fontFamily: fontFamily.nunitoBold,
                      fontSize: 18,
                      color: 'white',
                    }}
                  >
                    Signing in...
                  </Text>
                </>
              ) : (
                <>
                  <Text style={{ fontSize: 20 }}>🔓</Text>
                  <Text
                    style={{
                      fontFamily: fontFamily.nunitoBold,
                      fontSize: 18,
                      color: 'white',
                    }}
                  >
                    Enter
                  </Text>
                </>
              )}
            </LinearGradient>
          )}
        </Pressable>
      </SafeAreaView>
    </LinearGradient>
  );
}
