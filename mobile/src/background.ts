import * as BackgroundTask from "expo-background-task";
import * as TaskManager from "expo-task-manager";
import { syncLocalAlerts } from "./notifications";

export const ALERT_BACKGROUND_TASK = "avenlytics-alert-sync";

TaskManager.defineTask(ALERT_BACKGROUND_TASK, async () => {
  try {
    await syncLocalAlerts();
    return BackgroundTask.BackgroundTaskResult.Success;
  } catch {
    return BackgroundTask.BackgroundTaskResult.Failed;
  }
});

export async function registerAlertBackgroundTask() {
  try {
    await BackgroundTask.registerTaskAsync(ALERT_BACKGROUND_TASK, { minimumInterval: 15 });
  } catch {
    // Background execution is best-effort and controlled by the OS.
  }
}
