import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { AuthProvider } from "../src/auth";
import { DataProvider } from "../src/data";
import "../src/background";

export default function RootLayout() {
  return (
    <AuthProvider>
      <DataProvider>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false }} />
      </DataProvider>
    </AuthProvider>
  );
}