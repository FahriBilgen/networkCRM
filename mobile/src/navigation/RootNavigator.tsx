import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ActivityIndicator, View } from 'react-native';
import { useAuthStore } from '../store/authStore';
import AuthNavigator from './AuthNavigator';
import HomeScreen from '../screens/HomeScreen';
import AddNodeScreen from '../screens/AddNodeScreen';
import NodeDetailScreen from '../screens/NodeDetailScreen';
import { PersonNode } from '../types';

export type RootStackParamList = {
  Home: undefined;
  AddNode: { node?: PersonNode } | undefined;
  NodeDetail: { nodeId: string; node?: PersonNode };
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const RootStack = createNativeStackNavigator();

function LoadingScreen() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <ActivityIndicator size="large" color="#0f172a" />
    </View>
  );
}

function MainNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen 
        name="Home" 
        component={HomeScreen} 
        options={{ headerShown: false }} 
      />
      <Stack.Screen 
        name="AddNode" 
        component={AddNodeScreen} 
        options={{ title: 'Yeni Kişi Ekle' }} 
      />
      <Stack.Screen 
        name="NodeDetail" 
        component={NodeDetailScreen} 
        options={{ title: 'Kişi Detayı' }} 
      />
    </Stack.Navigator>
  );
}

export default function RootNavigator() {
  const { user, token, isLoading, loadUser } = useAuthStore();

  useEffect(() => {
    loadUser();
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <NavigationContainer>
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        {token ? (
          <RootStack.Screen name="Main" component={MainNavigator} />
        ) : (
          <RootStack.Screen name="Auth" component={AuthNavigator} />
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  );
}
