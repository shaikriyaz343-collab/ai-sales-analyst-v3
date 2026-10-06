# Avenlytics Mobile Release

## Android release path

1. Create an Expo account/project for Avenlytics.
2. In Expo, create an access token and add it to this GitHub repository as the `EXPO_TOKEN` Actions secret.
3. Run **Avenlytics Android EAS Build** from GitHub Actions with the `preview` profile for a phone-installable APK.
4. Test login, workspace selection, Overview, Decisions, Insights, Ask Analyst, Reports, Monitoring, Saved Intelligence, billing status, and notifications on a physical Android device.
5. Run the same workflow with `production` to create the Google Play AAB.

EAS CLI access tokens use the `EXPO_TOKEN` environment variable, and CI builds require the Expo project to be linked before the build runs. The workflow establishes that link on the build worker.

## Push notifications

Android remote notifications require Firebase/FCM credentials associated with the Expo/EAS project.

## Google Play

The production Android build should be an AAB. Google Play release automation additionally requires a Google Play Developer account and a Google service-account credential configured for the Expo project.

Never commit the Expo token, Firebase service-account JSON, or Google Play credentials to the repository.
