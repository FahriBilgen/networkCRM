import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { useNavigation } from '@react-navigation/native';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error } = useAuthStore();
  const navigation = useNavigation<any>();

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Hata', 'Lütfen tüm alanları doldurun.');
      return;
    }
    try {
      await login({ email, password });
    } catch (e) {
      // Error is handled in store
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerSection}>
        <Text style={styles.title}>Network CRM</Text>
        <Text style={styles.subtitle}>Kişilerinizi yönetin, ağınızı güçlendirin</Text>
      </View>

      <View style={styles.formSection}>
        {error && <View style={styles.errorBox}><Text style={styles.error}>{error}</Text></View>}

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Email Adresiniz</Text>
          <TextInput
            style={styles.input}
            placeholder="ornek@sirket.com"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Şifre</Text>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <TouchableOpacity 
          style={[styles.button, isLoading && styles.buttonDisabled]} 
          onPress={handleLogin} 
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Giriş Yap</Text>
          )}
        </TouchableOpacity>
      </View>

      <View style={styles.footerSection}>
        <Text style={styles.footerText}>Hesabın yok mu?</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Register')}>
          <Text style={styles.linkText}>Kayıt Ol</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
    paddingHorizontal: 20,
    paddingVertical: 40,
    justifyContent: 'space-between',
  },
  headerSection: {
    marginBottom: 40,
  },
  title: {
    fontSize: 36,
    fontWeight: '700',
    textAlign: 'center',
    color: '#0f172a',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#64748b',
    fontWeight: '400',
    lineHeight: 22,
  },
  formSection: {
    flex: 1,
    justifyContent: 'center',
  },
  inputGroup: {
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 14,
    borderRadius: 10,
    fontSize: 16,
    backgroundColor: '#fff',
    color: '#0f172a',
  },
  button: {
    backgroundColor: '#0f172a',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 20,
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  errorBox: {
    backgroundColor: '#fee2e2',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#dc2626',
    marginBottom: 20,
  },
  error: {
    color: '#991b1b',
    fontSize: 14,
    fontWeight: '500',
  },
  footerSection: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 4,
  },
  footerText: {
    fontSize: 14,
    color: '#64748b',
  },
  linkText: {
    color: '#0f172a',
    fontSize: 14,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
});
