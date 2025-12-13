import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { nodeService } from '../services/nodeService';
import { CreatePersonRequest } from '../types';
import { RootStackParamList } from '../navigation/RootNavigator';

type AddNodeRouteProp = RouteProp<RootStackParamList, 'AddNode'>;

export default function AddNodeScreen() {
  const navigation = useNavigation();
  const route = useRoute<AddNodeRouteProp>();
  const editingNode = route.params?.node;

  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<Omit<CreatePersonRequest, 'type'>>({
    name: editingNode?.name || '',
    sector: editingNode?.sector || '',
    tags: editingNode?.tags || [],
    notes: editingNode?.notes || '',
    relationshipStrength: editingNode?.relationshipStrength || 1,
    phone: editingNode?.contactPhone || '',
    email: editingNode?.contactEmail || '',
  });
  const [tagsInput, setTagsInput] = useState(editingNode?.tags?.join(', ') || '');

  useEffect(() => {
    navigation.setOptions({
      title: editingNode ? 'Kişiyi Düzenle' : 'Yeni Kişi Ekle',
    });
  }, [editingNode]);

  const handleSave = async () => {
    if (!formData.name || !formData.sector) {
      Alert.alert('Hata', 'İsim ve Sektör alanları zorunludur.');
      return;
    }

    setLoading(true);
    try {
      const tagsArray = tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
      
      const dataToSave: CreatePersonRequest = {
        ...formData,
        type: 'PERSON',
        tags: tagsArray
      };

      if (editingNode) {
        await nodeService.updateNode(editingNode.id, dataToSave);
        Alert.alert('Başarılı', 'Kişi güncellendi.', [
          { text: 'Tamam', onPress: () => navigation.goBack() }
        ]);
      } else {
        await nodeService.createNode(dataToSave);
        Alert.alert('Başarılı', 'Kişi başarıyla eklendi.', [
          { text: 'Tamam', onPress: () => navigation.goBack() }
        ]);
      }
    } catch (error) {
      console.error(error);
      Alert.alert('Hata', 'İşlem sırasında bir sorun oluştu.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.headerSection}>
        <Text style={styles.headerTitle}>Yeni Kişi Ekle</Text>
        <Text style={styles.headerSubtitle}>Ağınızı genişletmeye başlayın</Text>
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>Ad Soyad *</Text>
        <TextInput
          style={styles.input}
          value={formData.name}
          onChangeText={(text) => setFormData({ ...formData, name: text })}
          placeholder="Ahmet Yılmaz"
          placeholderTextColor="#cbd5e1"
        />
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>Sektör *</Text>
        <TextInput
          style={styles.input}
          value={formData.sector}
          onChangeText={(text) => setFormData({ ...formData, sector: text })}
          placeholder="Yazılım, Finans, Pazarlama..."
          placeholderTextColor="#cbd5e1"
        />
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>İlişki Gücü (1-5)</Text>
        <View style={styles.strengthContainer}>
          {[1, 2, 3, 4, 5].map((level) => (
            <TouchableOpacity
              key={level}
              style={[
                styles.strengthButton,
                formData.relationshipStrength === level && styles.strengthButtonActive
              ]}
              onPress={() => setFormData({ ...formData, relationshipStrength: level })}
            >
              <Text style={[
                styles.strengthText,
                formData.relationshipStrength === level && styles.strengthTextActive
              ]}>
                {level}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={styles.strengthHint}>1 = Zayıf, 5 = Çok Güçlü</Text>
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>Etiketler</Text>
        <TextInput
          style={styles.input}
          value={tagsInput}
          onChangeText={setTagsInput}
          placeholder="CEO, Yatırımcı, Mentor (virgülle ayırın)"
          placeholderTextColor="#cbd5e1"
        />
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>Telefon</Text>
        <TextInput
          style={styles.input}
          value={formData.phone}
          onChangeText={(text) => setFormData({ ...formData, phone: text })}
          keyboardType="phone-pad"
          placeholder="+90 555 123 45 67"
          placeholderTextColor="#cbd5e1"
        />
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>E-posta</Text>
        <TextInput
          style={styles.input}
          value={formData.email}
          onChangeText={(text) => setFormData({ ...formData, email: text })}
          keyboardType="email-address"
          autoCapitalize="none"
          placeholder="ornek@sirket.com"
          placeholderTextColor="#cbd5e1"
        />
      </View>

      <View style={styles.formGroup}>
        <Text style={styles.label}>Notlar</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          value={formData.notes}
          onChangeText={(text) => setFormData({ ...formData, notes: text })}
          multiline
          numberOfLines={4}
          placeholder="Kişi hakkında notlar, son konuşma konusu, vb."
          placeholderTextColor="#cbd5e1"
        />
      </View>

      <TouchableOpacity 
        style={[styles.button, loading && styles.buttonDisabled]} 
        onPress={handleSave}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>✓ Kaydet</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity 
        style={styles.cancelButton}
        onPress={() => navigation.goBack()}
        disabled={loading}
      >
        <Text style={styles.cancelButtonText}>İptal</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 40,
    backgroundColor: '#f8fafc',
  },
  headerSection: {
    marginBottom: 32,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '400',
  },
  formGroup: {
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
    color: '#0f172a',
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
    height: 100,
    textAlignVertical: 'top',
  },
  button: {
    backgroundColor: '#0f172a',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
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
  cancelButton: {
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  cancelButtonText: {
    color: '#64748b',
    fontSize: 14,
    fontWeight: '500',
  },
  strengthContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  strengthButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  strengthButtonActive: {
    backgroundColor: '#fef3c7',
    borderColor: '#f59e0b',
  },
  strengthText: {
    fontSize: 18,
    color: '#94a3b8',
    fontWeight: '700',
  },
  strengthTextActive: {
    color: '#92400e',
  },
  strengthHint: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 8,
    fontStyle: 'italic',
  },
});
