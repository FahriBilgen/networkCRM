# Network CRM Mobile

This is the mobile companion app for Network CRM.

## Setup

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Configure API URL**:
    *   Open `src/services/api.ts`.
    *   For Android Emulator, use `http://10.0.2.2:8080/api`.
    *   For iOS Simulator, use `http://localhost:8080/api`.
    *   For Physical Device, use your computer's local IP (e.g., `http://192.168.1.x:8080/api`).

3.  **Run the App**:
    ```bash
    npx expo start
    ```
    *   Press `a` for Android.
    *   Press `i` for iOS.

## Features

*   **Authentication**: Login and Register.
*   **Home Screen**: List of people in your network.
*   **Search**: Filter by name or sector.
*   **Add Person**: Fast data entry for new contacts.
*   **Person Detail**: View contact info, tags, and notes.

## Architecture

*   **State Management**: Zustand (`src/store`).
*   **Navigation**: React Navigation (`src/navigation`).
*   **API**: Axios with Interceptors (`src/services`).
*   **UI**: React Native Paper / Standard Components.
