import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ScrollView, ActivityIndicator } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { useNavigation } from '@react-navigation/native';

export default function RegisterScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [sector, setSector] = useState('');
  const [bio, setBio] = useState('');
  const [phone, setPhone] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  
  const { register, isLoading, error } = useAuthStore();
  const navigation = useNavigation<any>();

  const handleRegister = async () => {
    if (!email || !password || !fullName || !sector) {
      Alert.alert('Hata', 'Lütfen zorunlu alanları doldurun (*)');
      return;
    }
    try {
      await register({
        email,
        password,
        fullName,
        sector,
        bio,
        phone,
        linkedinUrl
      });
    } catch (e) {
      // Error handled in store
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerSection}>
        <Text style={styles.title}>Kayıt Ol</Text>
        <Text style={styles.subtitle}>Network hafızanı oluşturmaya başla</Text>
      </View>

      <View style={styles.formSection}>
        {error && <View style={styles.errorBox}><Text style={styles.error}>{error}</Text></View>}

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Ad Soyad *</Text>
          <TextInput
            style={styles.input}
            value={fullName}
            onChangeText={setFullName}
            placeholder="Ahmet Yılmaz"
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Email *</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="ornek@sirket.com"
            autoCapitalize="none"
            keyboardType="email-address"
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Şifre *</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Sektör *</Text>
          <TextInput
            style={styles.input}
            value={sector}
            onChangeText={setSector}
            placeholder="Yazılım, Finans, vb."
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Hakkında</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            value={bio}
            onChangeText={setBio}
            placeholder="Kısaca hakkında yazın..."
            multiline
            numberOfLines={3}
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Telefon</Text>
          <TextInput
            style={styles.input}
            value={phone}
            onChangeText={setPhone}
            placeholder="+90 555 ..."
            keyboardType="phone-pad"
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>LinkedIn Profili</Text>
          <TextInput
            style={styles.input}
            value={linkedinUrl}
            onChangeText={setLinkedinUrl}
            placeholder="linkedin.com/in/..."
            placeholderTextColor="#cbd5e1"
          />
        </View>

        <TouchableOpacity 
          style={[styles.button, isLoading && styles.buttonDisabled]} 
          onPress={handleRegister}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Kayıt Ol</Text>
          )}
        </TouchableOpacity>

      </View>

      <View style={styles.footerSection}>
        <Text style={styles.footerText}>Zaten hesabın var mı?</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Login')}>
          <Text style={styles.linkText}>Giriş Yap</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#f8fafc',
    paddingHorizontal: 20,
    paddingVertical: 40,
    justifyContent: 'space-between',
  },
  headerSection: {
    marginBottom: 30,
  },
  title: {
    fontSize: 32,
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
  },
  inputGroup: {
    marginBottom: 18,
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
  textArea: {
    height: 90,
    textAlignVertical: 'top',
  },
  button: {
    backgroundColor: '#0f172a',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 24,
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
    marginTop: 20,
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
