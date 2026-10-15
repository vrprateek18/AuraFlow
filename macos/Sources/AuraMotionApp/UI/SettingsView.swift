import SwiftUI
import AuraMotionCore

public struct SettingsView: View {
    @State private var settings = AppEnvironment.shared.currentSettings
    @State private var permissions = AppEnvironment.shared.permissionsManager.checkPermissions()

    public init() {}

    public var body: some View {
        Form {
            Section(header: Text("Permissions Status")) {
                HStack {
                    Text("Camera Access:")
                    Spacer()
                    Text(permissions.isCameraAuthorized ? "Granted" : "Denied")
                        .foregroundColor(permissions.isCameraAuthorized ? .green : .red)
                    if !permissions.isCameraAuthorized {
                        Button("Open Settings") {
                            AppEnvironment.shared.permissionsManager.openSystemSettingsCamera()
                        }
                    }
                }
                HStack {
                    Text("Accessibility Control:")
                    Spacer()
                    Text(permissions.isAccessibilityTrusted ? "Granted" : "Denied")
                        .foregroundColor(permissions.isAccessibilityTrusted ? .green : .red)
                    if !permissions.isAccessibilityTrusted {
                        Button("Open Settings") {
                            AppEnvironment.shared.permissionsManager.openSystemSettingsAccessibility()
                        }
                    }
                }
                HStack {
                    Text("Input Event Posting:")
                    Spacer()
                    Text(permissions.isPostEventAuthorized ? "Granted" : "Required")
                        .foregroundColor(permissions.isPostEventAuthorized ? .green : .orange)
                    if !permissions.isPostEventAuthorized {
                        Button("Request") {
                            AppEnvironment.shared.permissionsManager.requestPostEventAccess()
                            refreshPermissions()
                        }
                    }
                }
                HStack {
                    Text("Input Monitoring (optional):")
                    Spacer()
                    Text(permissions.isListenEventAuthorized ? "Granted" : "Not granted")
                        .foregroundColor(permissions.isListenEventAuthorized ? .green : .secondary)
                    if !permissions.isListenEventAuthorized {
                        Button("Request") {
                            AppEnvironment.shared.permissionsManager.requestListenEventAccess()
                            refreshPermissions()
                        }
                    }
                }
            }

            Section(header: Text("Interaction Preferences")) {
                Toggle("Mirror Camera Feed", isOn: $settings.isCameraMirrored)
                Toggle("Enable Engagement Clutch (Ready Pose)", isOn: $settings.isClutchEnabled)
                if settings.isClutchEnabled {
                    HStack {
                        Text("Activation Delay:")
                        Slider(value: $settings.clutchDwellTime, in: 0...0.30, step: 0.01)
                        Text(String(format: "%.0f ms", settings.clutchDwellTime * 1000))
                            .monospacedDigit()
                    }
                }
                Toggle("Enable Scroll Inertia", isOn: $settings.scrollInertiaEnabled)
                Toggle("Enable Palm Swipe Switching", isOn: $settings.isPalmSwipeEnabled)
                if settings.isPalmSwipeEnabled {
                    Picker("Swipe Action:", selection: $settings.swipeAction) {
                        ForEach(SwipeActionType.allCases, id: \.self) { action in
                            Text(action.displayName).tag(action)
                        }
                    }
                }
            }

            Section(header: Text("HUD & Feedback")) {
                Toggle("Show Floating HUD", isOn: $settings.showHUD)
                Toggle("Show Click Feedback Ripples", isOn: $settings.showClickFeedback)
            }

            Section(header: Text("Safety & Arbitration")) {
                HStack {
                    Text("Arbitration Cooldown:")
                    Slider(value: $settings.arbitrationCooldownSeconds, in: 0.5...3.0, step: 0.25)
                    Text(String(format: "%.1fs", settings.arbitrationCooldownSeconds))
                        .monospacedDigit()
                }
            }
        }
        .padding(20)
        .frame(width: 440, height: 460)
        .onChange(of: settings) { _, newSettings in
            AppEnvironment.shared.updateSettings(newSettings)
        }
        .onAppear {
            settings = AppEnvironment.shared.currentSettings
            refreshPermissions()
        }
        .onReceive(NotificationCenter.default.publisher(for: .auraMotionPermissionsDidChange)) { note in
            if let state = note.object as? PermissionsState {
                permissions = state
            } else {
                refreshPermissions()
            }
        }
    }

    private func refreshPermissions() {
        permissions = AppEnvironment.shared.permissionsManager.checkPermissions()
    }
}
