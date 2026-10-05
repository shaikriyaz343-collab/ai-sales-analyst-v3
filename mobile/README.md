# Avenlytics Mobile

React Native / Expo client for the Avenlytics AI Sales Analyst.

## v1 scope

- Sign in and sign up
- Workspace selector
- Overview
- Decisions
- Insights
- Ask Analyst
- Reports
- Monitoring and device notifications
- Saved intelligence
- Account and billing status
- No in-app purchasing in v1

The mobile app uses the same Avenlytics API and organization/workspace data as the web product.

## Local development

```bash
cd mobile
npm install
npx expo start
```

For Android device testing:

```bash
npx expo start --android
```

For remote push notification testing, link the app to an Expo EAS project and create a development or preview build. Expo documents that remote push notifications require a development build rather than Expo Go on Android.

## Production builds

Use EAS Build after linking an Expo project:

```bash
eas build --platform android --profile preview
eas build --platform android --profile production
eas build --platform ios --profile production
```

The current app intentionally keeps subscriptions and billing management web-based. Mobile displays the organization's current entitlement state.
