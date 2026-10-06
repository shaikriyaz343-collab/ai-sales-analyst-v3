# Avenlytics Mobile Release

## Android release path

1. Create an Expo account/project for Avenlytics.
2. In Expo, create an access token and add it to this GitHub repository as the `EXPO_TOKEN` Actions secret.
3. Run **Avenlytics Android EAS Build** from GitHub Actions with the `preview` profile for a phone-installable APK.
4. Test login, workspace selection, Overview, Decisions, Insights, Ask Analyst, Reports, Monitoring, Saved Intelligence, billing status, and notifications on a physical Android device.
5. Run the same workflow with `production` to create the Google Play AAB.

Expo documents that EAS CLI access tokens use the `EXPO_TOKEN` environment variable, and that a project must be linked before CI builds. The workflow uses `eas init --force --non-interactive` to establish that link on the build worker. citeturn344250search2turn344250search1

## Push notifications

Android remote notifications require Firebase/FCM credentials associated with the Expo/EAS project. Expo's current setup guide documents configuring Android credentials and testing on a physical device. citeturn476503search0turn476503search7

## Google Play

The production Android build should be an AAB. Google Play release automation additionally requires a Google Play Developer account, and automated submissions require a Google service-account credential configured for the Expo project. citeturn476503search12turn476503search9

Never commit the Expo token, Firebase service-account JSON, or Google Play credentials to the repository.
