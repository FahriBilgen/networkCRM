import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Replace with your local IP address for Android Emulator / Physical Device
// localhost works for iOS Simulator, but for Android use 10.0.2.2 or your machine's IP

const api = axios.create({
  baseURL: "http://192.168.0.112:8080/api",
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  async (config) => {
    const token = await SecureStore.getItemAsync('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
