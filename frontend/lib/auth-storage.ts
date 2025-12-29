/**
 * Auth token storage utilities using AsyncStorage.
 * Persists authentication tokens across app restarts.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_KEY = 'auth_token';

export const authStorage = {
  /**
   * Store the authentication token
   */
  setToken: async (token: string): Promise<void> => {
    try {
      await AsyncStorage.setItem(TOKEN_KEY, token);
    } catch (error) {
      console.error('Failed to save auth token:', error);
      throw error;
    }
  },

  /**
   * Retrieve the stored authentication token
   */
  getToken: async (): Promise<string | null> => {
    try {
      return await AsyncStorage.getItem(TOKEN_KEY);
    } catch (error) {
      console.error('Failed to get auth token:', error);
      return null;
    }
  },

  /**
   * Remove the stored authentication token (logout)
   */
  clearToken: async (): Promise<void> => {
    try {
      await AsyncStorage.removeItem(TOKEN_KEY);
    } catch (error) {
      console.error('Failed to clear auth token:', error);
      throw error;
    }
  },

  /**
   * Check if a token exists (quick auth check)
   */
  hasToken: async (): Promise<boolean> => {
    const token = await authStorage.getToken();
    return token !== null;
  },
};
