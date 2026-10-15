import AppKit
import SwiftUI
import AuraMotionCore

@MainActor
public final class AppDelegate: NSObject, NSApplicationDelegate, AppEnvironmentObserver {
    private var statusItemController: StatusItemController?
    private var hudWindow: FloatingHUDWindow?
    private var onboardingWindow: NSWindow?
    private let commandMenuWindow = CommandMenuWindowController()
    private let clickFeedback = ClickFeedbackWindowController()
    private var lastFeedbackID: UInt64 = 0

    public func applicationDidFinishLaunching(_ notification: Notification) {
        // 1. Create Floating HUD Panel
        let screenRect = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let hudRect = NSRect(x: screenRect.maxX - 240, y: screenRect.maxY - 220, width: 220, height: 200)
        let hud = FloatingHUDWindow(contentRect: hudRect)
        hud.contentView = NSHostingView(rootView: HUDView())
        if AppEnvironment.shared.currentSettings.showHUD { hud.orderFrontRegardless() }
        self.hudWindow = hud

        // 2. Create Status Item
        self.statusItemController = StatusItemController(hudWindow: hud)

        // 3. Register environment observer
        let env = AppEnvironment.shared
        env.observer = self

        // 4. Register Sleep/Wake notifications for honest safety guarantees
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(handleWillSleep),
            name: NSWorkspace.willSleepNotification,
            object: nil
        )
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(handleDidWake),
            name: NSWorkspace.didWakeNotification,
            object: nil
        )

        // 5. Start environment
        env.start()

        // 6. Check first-launch onboarding requirement
        if !env.currentSettings.firstLaunchCompleted {
            showOnboardingWindow()
        }
    }

    public func showOnboardingWindow() {
        if onboardingWindow == nil {
            let win = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 820, height: 600),
                styleMask: [.titled, .closable, .miniaturizable],
                backing: .buffered,
                defer: false
            )
            win.title = "AuraFlow — Move naturally. Control effortlessly."
            win.center()
            win.isReleasedWhenClosed = false
            let onboardingView = AuraFlowOnboardingView { [weak self, weak win] in
                win?.close()
                self?.onboardingWindow = nil
            }
            win.contentView = NSHostingView(rootView: onboardingView)
            self.onboardingWindow = win
        }
        onboardingWindow?.makeKeyAndOrderFront(nil)
        NSApplication.shared.activate(ignoringOtherApps: true)
    }

    public func applicationWillTerminate(_ notification: Notification) {
        AppEnvironment.shared.stop()
    }

    @objc private func handleWillSleep() {
        AppEnvironment.shared.outputCoordinator.emergencyRelease()
        let env = AppEnvironment.shared
        env.interactionQueue.async { env.stateMachine.transition(to: .trackingLost) }
    }

    @objc private func handleDidWake() {
        let env = AppEnvironment.shared
        env.interactionQueue.async { env.stateMachine.transition(to: .idle) }
    }

    // MARK: - AppEnvironmentObserver

    nonisolated public func environmentDidUpdateHUDSnapshot(_ snapshot: HUDSnapshot) {
        NotificationCenter.default.post(name: NSNotification.Name("HUDSnapshotUpdated"), object: snapshot)
        Task { @MainActor [weak self] in
            guard let self else { return }
            self.commandMenuWindow.update(snapshot.commandMenu)
            if snapshot.showHUD {
                if self.hudWindow?.isVisible == false { self.hudWindow?.orderFrontRegardless() }
            } else { self.hudWindow?.orderOut(nil) }
            if snapshot.clickFeedbackID != self.lastFeedbackID {
                self.lastFeedbackID = snapshot.clickFeedbackID
                if let point = snapshot.clickFeedbackLocation { self.clickFeedback.show(at: point) }
            }
            if snapshot.clickFeedbackLocation == nil { self.clickFeedback.hide() }
        }
    }
}
