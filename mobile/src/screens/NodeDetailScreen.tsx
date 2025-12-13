import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity, Linking, Alert } from 'react-native';
import { useRoute, useNavigation, RouteProp, useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { nodeService } from '../services/nodeService';
import { PersonNode } from '../types';
import { RootStackParamList } from '../navigation/RootNavigator';

type NodeDetailRouteProp = RouteProp<RootStackParamList, 'NodeDetail'>;
type NodeDetailNavigationProp = NativeStackNavigationProp<RootStackParamList, 'NodeDetail'>;

export default function NodeDetailScreen() {
  const route = useRoute<NodeDetailRouteProp>();
  const navigation = useNavigation<NodeDetailNavigationProp>();
  const { nodeId, node: initialNode } = route.params;
  
  const [node, setNode] = useState<PersonNode | null>(initialNode || null);
  const [loading, setLoading] = useState(!initialNode);

  const loadNodeDetails = async () => {
    try {
      const data = await nodeService.getNodeById(nodeId);
      setNode(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadNodeDetails();
    }, [nodeId])
  );

  const handleEdit = () => {
    if (node) {
      navigation.navigate('AddNode', { node });
    }
  };

  const handleDelete = () => {
    Alert.alert(
      'Kişiyi Sil',
      'Bu kişiyi silmek istediğinizden emin misiniz?',
      [
        { text: 'İptal', style: 'cancel' },
        { 
          text: 'Sil', 
          style: 'destructive', 
          onPress: async () => {
            try {
              await nodeService.deleteNode(nodeId);
              navigation.goBack();
            } catch (error) {
              Alert.alert('Hata', 'Silme işlemi başarısız oldu.');
            }
          }
        }
      ]
    );
  };

  const handleCall = () => {
    if (node?.contactPhone) {
      Linking.openURL(`tel:${node.contactPhone}`);
    }
  };

  const handleEmail = () => {
    if (node?.contactEmail) {
      Linking.openURL(`mailto:${node.contactEmail}`);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!node) {
    return (
      <View style={styles.center}>
        <Text>Kişi bulunamadı.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.avatarPlaceholder}>
          <Text style={styles.avatarText}>{node.name.charAt(0).toUpperCase()}</Text>
        </View>
        <Text style={styles.name}>{node.name}</Text>
        <Text style={styles.sector}>{node.sector}</Text>
        {node.relationshipStrength !== undefined && (
          <View style={styles.strengthBadge}>
            <Text style={styles.strengthBadgeText}>⭐ İlişki Gücü: {node.relationshipStrength}/5</Text>
          </View>
        )}
      </View>

      {node.contactPhone && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>📞 Telefon</Text>
          <TouchableOpacity onPress={handleCall} style={styles.contactButton}>
            <Text style={styles.contactValue}>{node.contactPhone}</Text>
            <Text style={styles.contactAction}>→ Ara</Text>
          </TouchableOpacity>
        </View>
      )}

      {node.contactEmail && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>📧 E-posta</Text>
          <TouchableOpacity onPress={handleEmail} style={styles.contactButton}>
            <Text style={styles.contactValue}>{node.contactEmail}</Text>
            <Text style={styles.contactAction}>→ Gönder</Text>
          </TouchableOpacity>
        </View>
      )}

      {node.tags && node.tags.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🏷️ Etiketler</Text>
          <View style={styles.tagsContainer}>
            {node.tags.map((tag, index) => (
              <View key={index} style={styles.tag}>
                <Text style={styles.tagText}>{tag}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {node.notes && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>📝 Notlar</Text>
          <View style={styles.notesBox}>
            <Text style={styles.notesText}>{node.notes}</Text>
          </View>
        </View>
      )}

      <View style={styles.actionButtons}>
        <TouchableOpacity style={styles.editButton} onPress={handleEdit}>
          <Text style={styles.editButtonText}>✏️ Düzenle</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.deleteButton} onPress={handleDelete}>
          <Text style={styles.deleteButtonText}>🗑️ Sil</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingVertical: 32,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  avatarPlaceholder: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#0f172a',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarText: {
    color: '#fff',
    fontSize: 32,
    fontWeight: '700',
  },
  name: {
    fontSize: 26,
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: 6,
    textAlign: 'center',
  },
  sector: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 12,
    fontWeight: '500',
  },
  strengthBadge: {
    marginTop: 12,
    backgroundColor: '#fef3c7',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  strengthText: {
    color: '#92400e',
    fontWeight: '600',
    fontSize: 13,
  },
  section: {
    marginTop: 20,
    marginHorizontal: 20,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 12,
    color: '#0f172a',
  },
  contactButton: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  contactValue: {
    color: '#0f172a',
    flex: 1,
    fontWeight: '500',
    fontSize: 14,
  },
  contactAction: {
    color: '#0f172a',
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 8,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  tag: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#bfdbfe',
  },
  tagText: {
    color: '#0369a1',
    fontSize: 12,
    fontWeight: '600',
  },
  notesBox: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  notesText: {
    color: '#475569',
    fontSize: 14,
    lineHeight: 20,
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: 14,
    fontStyle: 'italic',
  },
  actionButtons: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 24,
    gap: 12,
    marginBottom: 20,
  },
  editButton: {
    flex: 1,
    backgroundColor: '#0f172a',
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  editButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  deleteButton: {
    flex: 1,
    backgroundColor: '#fee2e2',
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#fecaca',
  },
  deleteButtonText: {
    color: '#dc2626',
    fontWeight: '600',
    fontSize: 14,
  },
});
