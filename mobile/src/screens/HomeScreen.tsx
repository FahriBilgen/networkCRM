import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput, ActivityIndicator, RefreshControl, ScrollView } from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/RootNavigator';
import { nodeService } from '../services/nodeService';
import { PersonNode } from '../types';
import { useAuthStore } from '../store/authStore';

type HomeScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Home'>;
type SortOption = 'name' | 'strength';

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const { logout } = useAuthStore();
  const [nodes, setNodes] = useState<PersonNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>('strength');

  const loadNodes = async () => {
    try {
      const data = await nodeService.getAllNodes();
      setNodes(data);
    } catch (error) {
      console.error('Failed to load nodes', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadNodes();
    }, [])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadNodes();
  };

  const sectors = useMemo(() => {
    const uniqueSectors = Array.from(new Set(nodes
      .filter(node => node.type === 'PERSON' && node.sector)
      .map(node => node.sector)
    )).filter(Boolean);
    return uniqueSectors.sort();
  }, [nodes]);

  const filteredAndSortedNodes = useMemo(() => {
    let result = nodes.filter(node => {
      // Only show Person nodes
      if (node.type !== 'PERSON') return false;

      const query = searchQuery.toLowerCase();
      const nameMatch = node.name ? node.name.toLowerCase().includes(query) : false;
      const sectorMatch = node.sector ? node.sector.toLowerCase().includes(query) : false;
      const tagMatch = node.tags ? node.tags.some(tag => tag.toLowerCase().includes(query)) : false;

      const matchesSearch = nameMatch || sectorMatch || tagMatch;
      const matchesSector = selectedSector ? node.sector === selectedSector : true;
      return matchesSearch && matchesSector;
    });

    return result.sort((a, b) => {
      if (sortBy === 'strength') {
        // Higher strength first
        const strengthA = a.relationshipStrength || 0;
        const strengthB = b.relationshipStrength || 0;
        if (strengthA !== strengthB) return strengthB - strengthA;
      }
      // Fallback to name sorting
      return a.name.localeCompare(b.name);
    });
  }, [nodes, searchQuery, selectedSector, sortBy]);

  const renderItem = ({ item }: { item: PersonNode }) => (
    <TouchableOpacity 
      style={styles.card}
      onPress={() => navigation.navigate('NodeDetail', { nodeId: item.id, node: item })}
    >
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{item.name.charAt(0).toUpperCase()}</Text>
      </View>
      <View style={styles.cardContent}>
        <Text style={styles.cardTitle}>{item.name}</Text>
        <Text style={styles.cardSubtitle}>{item.sector}</Text>
      </View>
      {item.relationshipStrength !== undefined && (
        <View style={styles.strengthIndicator}>
          <Text style={styles.strengthValue}>{item.relationshipStrength}</Text>
          <Text style={styles.strengthLabel}>/5</Text>
        </View>
      )}
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <Text style={styles.headerTitle}>Network</Text>
          <Text style={styles.headerSubtitle}>İlişkileri Yönetin</Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutButton}>
          <Text style={styles.logoutText}>Çıkış</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchSection}>
        <TextInput
          style={styles.searchInput}
          placeholder="🔍 Ara (İsim, Sektör, Etiket)..."
          placeholderTextColor="#94a3b8"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      <View style={styles.filtersContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.sectorList}>
          <TouchableOpacity
            style={[styles.sectorChip, !selectedSector && styles.sectorChipActive]}
            onPress={() => setSelectedSector(null)}
          >
            <Text style={[styles.sectorChipText, !selectedSector && styles.sectorChipTextActive]}>Tümü</Text>
          </TouchableOpacity>
          {sectors.map((sector) => (
            <TouchableOpacity
              key={sector}
              style={[styles.sectorChip, selectedSector === sector && styles.sectorChipActive]}
              onPress={() => setSelectedSector(sector)}
            >
              <Text style={[styles.sectorChipText, selectedSector === sector && styles.sectorChipTextActive]}>
                {sector}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        
        <TouchableOpacity 
          style={styles.sortButton} 
          onPress={() => setSortBy(prev => prev === 'name' ? 'strength' : 'name')}
        >
          <Text style={styles.sortButtonText}>
            {sortBy === 'strength' ? '⭐ Güç' : '📝 İsim'}
          </Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#0f172a" />
        </View>
      ) : (
        <FlatList
          data={filteredAndSortedNodes}
          renderItem={renderItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#0f172a" />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyIcon}>👤</Text>
              <Text style={styles.emptyText}>Henüz kimse eklenmemiş.</Text>
              <Text style={styles.emptySubtext}>Sağ alttaki + butonuyla başlayın!</Text>
            </View>
          }
        />
      )}

      <TouchableOpacity 
        style={styles.fab}
        onPress={() => navigation.navigate('AddNode')}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </View>
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  headerContent: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#0f172a',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
    fontWeight: '400',
  },
  logoutButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#fee2e2',
  },
  logoutText: {
    color: '#dc2626',
    fontSize: 13,
    fontWeight: '600',
  },
  searchSection: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
  },
  searchInput: {
    backgroundColor: '#f1f5f9',
    padding: 12,
    borderRadius: 10,
    fontSize: 14,
    color: '#0f172a',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  filtersContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  sectorList: {
    flex: 1,
    marginRight: 10,
  },
  sectorChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 16,
    backgroundColor: '#f1f5f9',
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  sectorChipActive: {
    backgroundColor: '#0f172a',
    borderColor: '#0f172a',
  },
  sectorChipText: {
    fontSize: 13,
    color: '#475569',
    fontWeight: '500',
  },
  sectorChipTextActive: {
    color: '#fff',
    fontWeight: '600',
  },
  sortButton: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
    backgroundColor: '#f1f5f9',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  sortButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#0f172a',
  },
  listContent: {
    padding: 16,
  },
  card: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 2,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#0f172a',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  avatarText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  cardContent: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
  },
  cardSubtitle: {
    fontSize: 13,
    color: '#64748b',
    marginTop: 2,
  },
  strengthIndicator: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: '#fef3c7',
    borderRadius: 8,
    alignItems: 'center',
  },
  strengthValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#92400e',
  },
  strengthLabel: {
    fontSize: 11,
    color: '#b45309',
    fontWeight: '500',
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center',
    marginTop: 40,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyText: {
    color: '#0f172a',
    fontSize: 16,
    fontWeight: '600',
  },
  emptySubtext: {
    color: '#64748b',
    fontSize: 13,
    marginTop: 8,
  },
  fab: {
    position: 'absolute',
    bottom: 30,
    right: 20,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#0f172a',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  fabText: {
    color: '#fff',
    fontSize: 32,
    fontWeight: '300',
    marginBottom: 2,
  },
});
