import AppKit
import SwiftUI
import AuraMotionCore

@MainActor
public final class StatusItemController: NSObject {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private var hudWindow: FloatingHUDWindow?
    private var diagnosticsWindow: NSWindow?
    private var settingsWindow: NSWindow?
    private var calibrationWindow: NSWindow?
    private var movementCalibrationWindow: NSWindow?
    private var onboardingWindow: NSWindow?

    public init(hudWindow: FloatingHUDWindow) {
        self.hudWindow = hudWindow
        super.init()
        setupMenu()
    }

    private func setupMenu() {
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "hand.point.up.fill", accessibilityDescription: "AuraFlow Pro")
        }

        let menu = NSMenu()

        menu.addItem(NSMenuItem(title: "AuraFlow Pro", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())

        let pauseItem = NSMenuItem(title: "Pause Gesture Control", action: #selector(togglePause), keyEquivalent: "p")
        pauseItem.target = self
        menu.addItem(pauseItem)

        let hudItem = NSMenuItem(title: "Toggle Floating HUD", action: #selector(toggleHUD), keyEquivalent: "h")
        hudItem.target = self
        menu.addItem(hudItem)

        menu.addItem(NSMenuItem.separator())

        let onboardingItem = NSMenuItem(title: "AuraFlow Onboarding & Tutorial...", action: #selector(openOnboarding), keyEquivalent: "o")
        onboardingItem.target = self
        menu.addItem(onboardingItem)

        let diagItem = NSMenuItem(title: "Diagnostics & Telemetry...", action: #selector(openDiagnostics), keyEquivalent: "d")
        diagItem.target = self
        menu.addItem(diagItem)

        let calItem = NSMenuItem(title: "Calibration...", action: #selector(openCalibration), keyEquivalent: "c")
        calItem.target = self
        menu.addItem(calItem)
        let movementItem = NSMenuItem(title: "Movement Calibration...", action: #selector(openMovementCalibration), keyEquivalent: "")
        movementItem.target = self
        menu.addItem(movementItem)

        let settingsItem = NSMenuItem(title: "Settings...", action: #selector(openSettings), keyEquivalent: ",")
        settingsItem.target = self
        menu.addItem(settingsItem)

        menu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "Quit AuraFlow", action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    @objc private func togglePause() {
        AppEnvironment.shared.togglePause()
    }

    @objc private func toggleHUD() {
        var settings = AppEnvironment.shared.currentSettings
        settings.showHUD.toggle()
        AppEnvironment.shared.updateSettings(settings)
    }

    @objc private func openDiagnostics() {
        if diagnosticsWindow == nil {
            let win = NSWindow(
                contentRect: NSRect(x: 100, y: 100, width: 420, height: 640),
                styleMask: [.titled, .closable],
                backing: .buffered,
                defer: false
            )
            win.title = "AuraFlow Diagnostics"
            win.contentView = NSHostingView(rootView: DiagnosticsView())
            diagnosticsWindow = win
        }
        diagnosticsWindow?.makeKeyAndOrderFront(nil)
    }

    @objc private func openSettings() {
        if settingsWindow == nil {
            let win = NSWindow(
                contentRect: NSRect(x: 150, y: 150, width: 440, height: 460),
                styleMask: [.titled, .closable],
                backing: .buffered,
                defer: false
            )
            win.title = "AuraFlow Settings"
            win.contentView = NSHostingView(rootView: SettingsView())
            settingsWindow = win
        }
        settingsWindow?.makeKeyAndOrderFront(nil)
    }

    @objc private func openCalibration() {
        movementCalibrationWindow?.close()
        if calibrationWindow == nil {
            let win = NSWindow(
                contentRect: NSRect(x: 200, y: 200, width: 420, height: 560),
                styleMask: [.titled, .closable],
                backing: .buffered,
                defer: false
            )
            win.title = "AuraFlow Calibration"
            win.contentView = NSHostingView(rootView: CalibrationView())
            calibrationWindow = win
        }
        calibrationWindow?.makeKeyAndOrderFront(nil)
    }

    @objc private func quitApp() {
        NSApplication.shared.terminate(nil)
    }

    @objc private func openMovementCalibration() {
        calibrationWindow?.close()
        if movementCalibrationWindow == nil {
            let window = NSWindow(contentRect: NSRect(x: 200, y: 200, width: 440, height: 390),
                                  styleMask: [.titled, .closable], backing: .buffered, defer: false)
            window.title = "AuraFlow Movement Calibration"
            window.isReleasedWhenClosed = false
            window.contentView = NSHostingView(rootView: MovementCalibrationView())
            movementCalibrationWindow = window
        }
        movementCalibrationWindow?.makeKeyAndOrderFront(nil)
    }

    @objc private func openOnboarding() {
        if onboardingWindow == nil {
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 820, height: 600),
                styleMask: [.titled, .closable, .miniaturizable],
                backing: .buffered,
                defer: false
            )
            window.title = "AuraFlow — Move naturally. Control effortlessly."
            window.center()
            window.isReleasedWhenClosed = false
            let onboardingView = AuraFlowOnboardingView { [weak self, weak window] in
                window?.close()
                self?.onboardingWindow = nil
            }
            window.contentView = NSHostingView(rootView: onboardingView)
            onboardingWindow = window
        }
        onboardingWindow?.makeKeyAndOrderFront(nil)
        NSApplication.shared.activate(ignoringOtherApps: true)
    }
}
