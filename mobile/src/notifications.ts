import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { Platform } from "react-native";
import type { AlertEvent } from "./types";
import { getAlerts, registerPushToken } from "./api";
import { getDatasetId, getSeenAlerts, getSessionId, setSeenAlerts } from "./storage";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export async function configureNotificationChannel() {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("alerts", {
      name: "Avenlytics alerts",
      importance: Notifications.AndroidImportance.DEFAULT,
      vibrationPattern: [0, 250, 250, 250],
    });
  }
}

export async function registerDeviceForNotifications(): Promise<"registered"|"unsupported"|"denied"|"missing-project"> {
  if (!Device.isDevice) return "unsupported";
  const current = await Notifications.getPermissionsAsync();
  let status = current.status;
  if (status !== Notifications.PermissionStatus.GRANTED) {
    const requested = await Notifications.requestPermissionsAsync();
    status = requested.status;
  }
  if (status !== Notifications.PermissionStatus.GRANTED) return "denied";

  const projectId = Constants.expoConfig?.extra?.eas?.projectId as string | undefined;
  if (!projectId) return "missing-project";
  try {
    const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
    await registerPushToken(token, Platform.OS);
    return "registered";
  } catch {
    return "missing-project";
  }
}

export async function notifyTriggeredAlerts(datasetId: string, sessionId: string): Promise<number> {
  const alerts = await getAlerts(datasetId, sessionId);
  const seen = new Set(await getSeenAlerts());
  const triggered = alerts.events.filter((event: AlertEvent) => event.status === "triggered" && !seen.has(event.event_id));
  for (const event of triggered.slice(0, 3)) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: event.title,
        body: event.message,
        data: { screen: "monitoring", eventId: event.event_id },
      },
      trigger: null,
    });
    seen.add(event.event_id);
  }
  if (triggered.length) await setSeenAlerts([...seen]);
  return triggered.length;
}

export async function syncLocalAlerts() {
  const datasetId = await getDatasetId();
  const sessionId = await getSessionId();
  if (!datasetId || !sessionId) return 0;
  return notifyTriggeredAlerts(datasetId, sessionId);
}
