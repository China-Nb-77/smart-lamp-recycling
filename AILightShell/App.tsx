import React from 'react';
import {NavigationContainer, DefaultTheme} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {StatusBar} from 'react-native';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import NetworkBanner from './src/components/NetworkBanner';
import {shellTheme} from './src/config/theme';
import CheckoutScreen from './src/screens/CheckoutScreen';
import HybridWebScreen from './src/screens/HybridWebScreen';
import UploadCenterScreen from './src/screens/UploadCenterScreen';

export type RootStackParamList = {
  Assistant: {routePath?: string} | undefined;
  UploadCenter: undefined;
  Checkout: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar
        backgroundColor={shellTheme.colors.background}
        barStyle="dark-content"
      />
      <NavigationContainer
        theme={{
          ...DefaultTheme,
          colors: {
            ...DefaultTheme.colors,
            background: shellTheme.colors.background,
            card: shellTheme.colors.surface,
            primary: shellTheme.colors.primary,
            text: shellTheme.colors.text,
            border: 'transparent',
          },
        }}>
        <NetworkBanner />
        <Stack.Navigator
          screenOptions={{
            headerShadowVisible: false,
            headerStyle: {backgroundColor: shellTheme.colors.surface},
            headerTintColor: shellTheme.colors.text,
            contentStyle: {backgroundColor: shellTheme.colors.background},
          }}>
          <Stack.Screen
            component={HybridWebScreen}
            initialParams={{routePath: '/'}}
            name="Assistant"
            options={{headerShown: false}}
          />
          <Stack.Screen
            component={UploadCenterScreen}
            name="UploadCenter"
            options={{title: '上传中心'}}
          />
          <Stack.Screen
            component={CheckoutScreen}
            name="Checkout"
            options={{title: '订单与支付主链路'}}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
