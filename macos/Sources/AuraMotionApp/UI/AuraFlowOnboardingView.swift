import SwiftUI
import AVFoundation
import AppKit
import AuraMotionCore

public struct AuraFlowOnboardingView: View {
    public var onFinish: (() -> Void)?

    @State private var currentStep: Int = 0
    @State private var tutorialGestureIndex: Int = 0
    @State private var permissionsState: PermissionsState
    @State private var practiceSuccessCount: Int = 0
    @State private var isPracticing: Bool = false
    @State private var practiceHint: String = "Tap or pinch the test circle to practice"

    public init(onFinish: (() -> Void)? = nil) {
        self.onFinish = onFinish
        self._permissionsState = State(initialValue: AppEnvironment.shared.permissionsManager.checkPermissions())
    }

    public var body: some View {
        ZStack {
            // Midnight Navy Background
            Color.auraMidnightNavy
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Top Navigation / Progress Indicator
                topNavBar

                // Main Content View based on currentStep
                Group {
                    switch currentStep {
                    case 0:
                        welcomeStepView
                    case 1:
                        tutorialStepView
                    case 2:
                        setupStepView
                    default:
                        completionStepView
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                // Bottom Navigation Bar
                bottomActionBar
            }
            .padding(.horizontal, 36)
            .padding(.vertical, 24)
        }
        .frame(width: 820, height: 600)
        .onAppear {
            refreshPermissions()
        }
        .onReceive(NotificationCenter.default.publisher(for: .auraMotionPermissionsDidChange)) { notification in
            if let state = notification.object as? PermissionsState {
                self.permissionsState = state
            }
        }
    }

    // MARK: - Top Nav Bar
    private var topNavBar: some View {
        HStack {
            HStack(spacing: 10) {
                AuraFlowLogoView(size: 26, isAnimated: false)
                Text("AuraFlow")
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                Text("PRO")
                    .font(.system(size: 9, weight: .heavy))
                    .foregroundColor(.auraFlowCyan)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.auraFlowCyan.opacity(0.18))
                    .cornerRadius(4)
            }

            Spacer()

            // Step Indicator Dots
            HStack(spacing: 8) {
                ForEach(0..<4) { idx in
                    Capsule()
                        .fill(idx == currentStep ? Color.auraFlowCyan : Color.white.opacity(0.18))
                        .frame(width: idx == currentStep ? 24 : 8, height: 6)
                        .animation(.easeInOut(duration: 0.25), value: currentStep)
                }
            }

            Spacer()

            if currentStep > 0 && currentStep < 3 {
                Button("Skip Setup") {
                    finishOnboarding()
                }
                .buttonStyle(AuraFlowOutlineButtonStyle())
            } else {
                Spacer().frame(width: 80)
            }
        }
        .padding(.bottom, 20)
    }

    // MARK: - Step 0: Welcome Screen
    private var welcomeStepView: some View {
        VStack(spacing: 22) {
            Spacer()

            AuraFlowLogoView(size: 80, isAnimated: true)

            VStack(spacing: 6) {
                Text("AuraFlow")
                    .font(.system(size: 32, weight: .heavy, design: .rounded))
                    .foregroundColor(.white)
                    .tracking(1.2)

                Text("Move naturally. Control effortlessly.")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.auraFlowCyan)

                Text("Next-generation touchless pointer and gesture control crafted for macOS.")
                    .font(.system(size: 12))
                    .foregroundColor(.auraTextMuted)
                    .multilineTextAlignment(.center)
                    .padding(.top, 2)
            }

            // 3 Feature Cards
            HStack(spacing: 16) {
                featureCard(
                    icon: "hand.point.up.fill",
                    title: "Natural Control",
                    desc: "Point, pinch-to-click, and glide to scroll effortlessly in mid-air."
                )
                featureCard(
                    icon: "bolt.fill",
                    title: "Neural Engine Speed",
                    desc: "Sub-12ms low-latency inference powered by Apple Vision & Neural Engine."
                )
                featureCard(
                    icon: "lock.shield.fill",
                    title: "Safety First",
                    desc: "C11 lock-free atomic arbitration with instant physical mouse priority."
                )
            }
            .padding(.horizontal, 10)

            Spacer()
        }
    }

    private func featureCard(icon: String, title: String, desc: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(.auraFlowCyan)

            Text(title)
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(.white)

            Text(desc)
                .font(.system(size: 11))
                .foregroundColor(.auraTextMuted)
                .lineSpacing(2)

            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .frame(height: 110)
        .padding(14)
        .background(Color.auraCardSurface.opacity(0.6))
        .cornerRadius(10)
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }

    // MARK: - Step 1: Interactive Tutorial & Gestures
    private var tutorialGestures: [(id: String, name: String, badge: String, desc: String, icon: String)] {
        [
            ("point", "1. Cursor Movement", "POINTER", "Extend your index finger and move it naturally. The cursor tracks your index fingertip with smooth 1-Euro filtering.", "hand.point.up"),
            ("click", "2. Pinch to Click", "LEFT CLICK", "Tap your thumb and index fingertip together quickly and release. This generates an instant, crisp left mouse click.", "hand.tap"),
            ("drag", "3. Pinch & Hold Drag", "DRAG & DROP", "Pinch thumb and index together firmly and move your hand to drag items or windows. Separate fingers to drop.", "arrow.up.and.down.and.arrow.left.and.right"),
            ("scroll", "4. Two-Finger Scroll", "SMOOTH SCROLL", "Extend both your index and middle fingers together and glide up or down smoothly to scroll pages.", "arrow.up.and.down"),
            ("swipe", "5. Palm Swipe Space Switch", "SYSTEM SWIPE", "Glide your open palm horizontally across the frame to switch full-screen spaces (Control + Arrow) or applications.", "hand.draw"),
            ("menu", "6. Radial Command Menu", "COMMAND PALETTE", "Hold your open 5-finger hand steady for half a second to invoke the 3x3 radial command menu for rapid shortcuts.", "circle.grid.3x3")
        ]
    }

    private var tutorialStepView: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Interactive Gesture Tutorial")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)

                    Text("Master the natural gestures supported natively by the Apple Vision engine.")
                        .font(.system(size: 12))
                        .foregroundColor(.auraTextMuted)
                }

                Spacer()

                // Gesture step selector
                Text("\(tutorialGestureIndex + 1) of \(tutorialGestures.count)")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundColor(.auraIceBlue)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.auraCardSurface)
                    .cornerRadius(6)
            }

            let g = tutorialGestures[tutorialGestureIndex]

            // Main Active Gesture Card
            HStack(spacing: 20) {
                // Left: Gesture Details
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text(g.badge)
                            .font(.system(size: 9, weight: .heavy))
                            .foregroundColor(.auraFlowCyan)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(Color.auraFlowCyan.opacity(0.18))
                            .cornerRadius(4)

                        Spacer()
                    }

                    Text(g.name)
                        .font(.system(size: 17, weight: .bold))
                        .foregroundColor(.white)

                    Text(g.desc)
                        .font(.system(size: 12))
                        .foregroundColor(.auraTextMuted)
                        .lineSpacing(3)

                    Spacer()

                    // Mini dots for gestures
                    HStack(spacing: 6) {
                        ForEach(0..<tutorialGestures.count, id: \.self) { idx in
                            Circle()
                                .fill(idx == tutorialGestureIndex ? Color.auraFlowCyan : Color.white.opacity(0.2))
                                .frame(width: 7, height: 7)
                                .onTapGesture {
                                    tutorialGestureIndex = idx
                                }
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
                .background(Color.auraCardSurface.opacity(0.6))
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )

                // Right: Interactive Practice Pad
                VStack(spacing: 14) {
                    Text("PRACTICE PAD")
                        .font(.system(size: 10, weight: .heavy))
                        .foregroundColor(.auraIceBlue)

                    ZStack {
                        Circle()
                            .stroke(Color.auraFlowCyan.opacity(0.3), lineWidth: 2)
                            .frame(width: 110, height: 110)

                        Circle()
                            .fill(Color.auraFlowCyan.opacity(isPracticing ? 0.35 : 0.12))
                            .frame(width: 90, height: 90)

                        Image(systemName: g.icon)
                            .font(.system(size: 32))
                            .foregroundColor(.auraIceBlue)
                    }
                    .scaleEffect(isPracticing ? 1.08 : 1.0)
                    .animation(.spring(response: 0.3, dampingFraction: 0.6), value: isPracticing)
                    .onTapGesture {
                        practiceSuccess()
                    }

                    Text(practiceHint)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(practiceSuccessCount > 0 ? .auraSuccess : .auraTextMuted)
                        .multilineTextAlignment(.center)
                        .frame(height: 28)

                    HStack(spacing: 6) {
                        Text("Practice Successes:")
                            .font(.system(size: 10))
                            .foregroundColor(.auraTextMuted)
                        Text("\(practiceSuccessCount)")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(.auraSuccess)
                    }
                }
                .frame(width: 250)
                .padding(20)
                .background(Color.auraDeepSurface)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )
            }
            .frame(maxHeight: 280)

            // Tutorial Carousel Next / Prev Controls
            HStack {
                Button("← Previous Gesture") {
                    if tutorialGestureIndex > 0 {
                        tutorialGestureIndex -= 1
                        practiceSuccessCount = 0
                        practiceHint = "Tap or pinch the test circle to practice"
                    }
                }
                .buttonStyle(AuraFlowOutlineButtonStyle())
                .disabled(tutorialGestureIndex == 0)

                Spacer()

                Button("Skip Tutorial") {
                    currentStep = 2
                }
                .buttonStyle(AuraFlowOutlineButtonStyle())

                Button(tutorialGestureIndex < tutorialGestures.count - 1 ? "Next Gesture →" : "Continue to Setup →") {
                    if tutorialGestureIndex < tutorialGestures.count - 1 {
                        tutorialGestureIndex += 1
                        practiceSuccessCount = 0
                        practiceHint = "Tap or pinch the test circle to practice"
                    } else {
                        currentStep = 2
                    }
                }
                .buttonStyle(AuraFlowSecondaryButtonStyle())
            }
            .padding(.top, 8)
        }
    }

    private func practiceSuccess() {
        isPracticing = true
        practiceSuccessCount += 1
        practiceHint = "Great! Gesture recognized successfully."
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            isPracticing = false
        }
    }

    // MARK: - Step 2: System Setup & Permissions
    private var setupStepView: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("macOS System Setup & Permissions")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)

                    Text("AuraFlow requires Camera access and Input Control to track hand gestures and steer the cursor.")
                        .font(.system(size: 12))
                        .foregroundColor(.auraTextMuted)
                }

                Spacer()

                Button(action: { refreshPermissions() }) {
                    Label("Re-Check", systemImage: "arrow.clockwise")
                }
                .buttonStyle(AuraFlowOutlineButtonStyle())
            }

            VStack(spacing: 12) {
                // 1. Camera Permission Row
                permissionRow(
                    title: "Webcam Access (AVFoundation)",
                    desc: "Required for Apple Vision hand landmark estimation.",
                    isGranted: permissionsState.isCameraAuthorized,
                    grantAction: {
                        AppEnvironment.shared.permissionsManager.requestCameraAccess { _ in
                            refreshPermissions()
                        }
                    },
                    settingsAction: {
                        AppEnvironment.shared.permissionsManager.openSystemSettingsCamera()
                    }
                )

                // 2. Accessibility Trust Row
                permissionRow(
                    title: "Accessibility Control (AXIsProcessTrusted)",
                    desc: "Required to interact with windows and navigate macOS.",
                    isGranted: permissionsState.isAccessibilityTrusted,
                    grantAction: {
                        AppEnvironment.shared.permissionsManager.requestAccessibilityIfNeeded()
                        refreshPermissions()
                    },
                    settingsAction: {
                        AppEnvironment.shared.permissionsManager.openSystemSettingsAccessibility()
                    }
                )

                // 3. Post Event / Input Control Row
                permissionRow(
                    title: "Input Control / Event Posting (CGPreflightPostEventAccess)",
                    desc: "Required to inject synthesized mouse clicks, cursor moves, and scrolls.",
                    isGranted: permissionsState.isPostEventAuthorized,
                    grantAction: {
                        AppEnvironment.shared.permissionsManager.requestPostEventAccess()
                        refreshPermissions()
                    },
                    settingsAction: {
                        AppEnvironment.shared.permissionsManager.openSystemSettingsAccessibility()
                    }
                )

                // 4. Physical Mouse Arbitration Row
                permissionRow(
                    title: "Physical Mouse Arbitration (CGPreflightListenEventAccess)",
                    desc: "Instantly yields gesture control when your hand touches the real physical mouse.",
                    isGranted: permissionsState.isListenEventAuthorized,
                    grantAction: {
                        AppEnvironment.shared.permissionsManager.requestListenEventAccess()
                        refreshPermissions()
                    },
                    settingsAction: {
                        AppEnvironment.shared.permissionsManager.openSystemSettingsAccessibility()
                    }
                )
            }
            .padding(16)
            .background(Color.auraCardSurface.opacity(0.6))
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.white.opacity(0.08), lineWidth: 1)
            )

            // Diagnostic notice
            HStack(spacing: 10) {
                Image(systemName: allPermissionsGranted ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                    .foregroundColor(allPermissionsGranted ? .auraSuccess : .auraCoralAlert)

                Text(allPermissionsGranted ?
                     "All runtime requirements satisfied! You are ready to start gesture control." :
                     "Some permissions are pending. Grant them above or adjust in macOS System Settings.")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(allPermissionsGranted ? .auraSuccess : .white)

                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(allPermissionsGranted ? Color.auraSuccess.opacity(0.12) : Color.auraCoralAlert.opacity(0.12))
            .cornerRadius(8)
        }
    }

    private var allPermissionsGranted: Bool {
        permissionsState.isCameraAuthorized &&
        permissionsState.isAccessibilityTrusted &&
        permissionsState.isPostEventAuthorized
    }

    private func permissionRow(
        title: String,
        desc: String,
        isGranted: Bool,
        grantAction: @escaping () -> Void,
        settingsAction: @escaping () -> Void
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: isGranted ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                .font(.system(size: 18))
                .foregroundColor(isGranted ? .auraSuccess : .auraCoralAlert)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(.white)

                Text(desc)
                    .font(.system(size: 10))
                    .foregroundColor(.auraTextMuted)
            }

            Spacer()

            if isGranted {
                Text("Granted")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.auraSuccess)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.auraSuccess.opacity(0.15))
                    .cornerRadius(6)
            } else {
                HStack(spacing: 8) {
                    Button("Grant") {
                        grantAction()
                    }
                    .buttonStyle(AuraFlowPrimaryButtonStyle())

                    Button("Open Settings ↗") {
                        settingsAction()
                    }
                    .buttonStyle(AuraFlowOutlineButtonStyle())
                }
            }
        }
        .padding(.vertical, 4)
    }

    private func refreshPermissions() {
        permissionsState = AppEnvironment.shared.permissionsManager.checkPermissions()
    }

    // MARK: - Step 3: Ready to Control (Completion)
    private var completionStepView: some View {
        VStack(spacing: 24) {
            Spacer()

            AuraFlowLogoView(size: 70, isAnimated: true)

            VStack(spacing: 8) {
                Text("You're All Set!")
                    .font(.system(size: 26, weight: .heavy, design: .rounded))
                    .foregroundColor(.white)

                Text("AuraFlow Pro is running in your macOS menu bar.")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.auraFlowCyan)

                Text("Look for the hand icon in your menu bar to toggle HUD, adjust calibration, or pause tracking.\nEmergency Stop is active at all times.")
                    .font(.system(size: 12))
                    .foregroundColor(.auraTextMuted)
                    .multilineTextAlignment(.center)
                    .lineSpacing(3)
            }

            HStack(spacing: 16) {
                summaryPill(label: "Engine", value: "Apple Vision + Metal")
                summaryPill(label: "Safety", value: "C11 Mouse Arbitrator")
                summaryPill(label: "Status", value: "Ready to Stream")
            }

            Spacer()
        }
    }

    private func summaryPill(label: String, value: String) -> some View {
        VStack(spacing: 3) {
            Text(label.uppercased())
                .font(.system(size: 9, weight: .bold))
                .foregroundColor(.auraTextMuted)
            Text(value)
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color.auraCardSurface.opacity(0.7))
        .cornerRadius(8)
    }

    // MARK: - Bottom Action Bar
    private var bottomActionBar: some View {
        HStack {
            if currentStep > 0 {
                Button("← Back") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        currentStep -= 1
                    }
                }
                .buttonStyle(AuraFlowOutlineButtonStyle())
            }

            Spacer()

            if currentStep == 0 {
                HStack(spacing: 14) {
                    Button("Skip Setup") {
                        finishOnboarding()
                    }
                    .buttonStyle(AuraFlowOutlineButtonStyle())

                    Button("Get Started →") {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            currentStep = 1
                        }
                    }
                    .buttonStyle(AuraFlowPrimaryButtonStyle())
                }
            } else if currentStep < 3 {
                Button("Next Step →") {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        currentStep += 1
                    }
                }
                .buttonStyle(AuraFlowPrimaryButtonStyle())
            } else {
                Button("Launch AuraFlow Control Center 🚀") {
                    finishOnboarding()
                }
                .buttonStyle(AuraFlowPrimaryButtonStyle())
            }
        }
        .padding(.top, 16)
    }

    private func finishOnboarding() {
        var settings = AppEnvironment.shared.currentSettings
        settings.firstLaunchCompleted = true
        AppEnvironment.shared.updateSettings(settings)
        onFinish?()
    }
}
