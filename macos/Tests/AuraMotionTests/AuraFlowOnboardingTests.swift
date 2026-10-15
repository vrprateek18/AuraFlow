import XCTest
import CoreGraphics
import Foundation
@testable import AuraMotionCore

final class AuraFlowOnboardingTests: XCTestCase {

    func testFirstLaunchDefaultValueIsFalse() {
        let settings = AppSettings()
        XCTAssertFalse(settings.firstLaunchCompleted, "Fresh install must require first-launch onboarding")
    }

    func testFirstLaunchCompletionPersistsAcrossSessions() throws {
        let suiteName = "AuraFlow.OnboardingTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let repository = SettingsRepository(userDefaults: defaults)

        // Initial state
        var settings = repository.loadSettings()
        XCTAssertFalse(settings.firstLaunchCompleted)

        // Complete onboarding
        settings.firstLaunchCompleted = true
        repository.saveSettings(settings)

        // Reload in new session
        let reloaded = repository.loadSettings()
        XCTAssertTrue(reloaded.firstLaunchCompleted, "Onboarding completion must persist across app reboots")
    }

    func testLegacyConfigurationsDefaultToFalseWithoutBreakingSettings() throws {
        let suiteName = "AuraFlow.LegacyMigration.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }

        // JSON payload without firstLaunchCompleted key
        let legacyJSON = Data(#"{"isCameraMirrored":true,"showHUD":false,"clutchDwellTime":0.10}"#.utf8)
        defaults.set(legacyJSON, forKey: "com.auramotion.settings")

        let repository = SettingsRepository(userDefaults: defaults)
        let settings = repository.loadSettings()

        // Existing preferences preserved
        XCTAssertTrue(settings.isCameraMirrored)
        XCTAssertFalse(settings.showHUD)
        XCTAssertEqual(settings.clutchDwellTime, 0.10)

        // New field gained safely
        XCTAssertFalse(settings.firstLaunchCompleted, "Legacy configurations must safely gain firstLaunchCompleted=false")
    }

    func testPermissionsStateBlockingLabels() {
        // No camera
        let noCam = PermissionsState(
            isCameraAuthorized: false,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        )
        XCTAssertEqual(noCam.compactStatusLabel, "NO CAMERA")
        XCTAssertEqual(noCam.statusLabel, "Camera access is required")

        // No accessibility
        let noAX = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: false,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        )
        XCTAssertEqual(noAX.compactStatusLabel, "NO ACCESSIBILITY")
        XCTAssertEqual(noAX.inputBlockingReason, "Accessibility control is required")

        // No input post
        let noPost = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: false,
            isListenEventAuthorized: true
        )
        XCTAssertEqual(noPost.compactStatusLabel, "NO INPUT CONTROL")
        XCTAssertEqual(noPost.inputBlockingReason, "Input control permission is required")

        // Fully authorized
        let full = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        )
        XCTAssertNil(full.compactStatusLabel)
        XCTAssertNil(full.statusLabel)
        XCTAssertNil(full.inputBlockingReason)
        XCTAssertTrue(full.canInjectInput)
        XCTAssertTrue(full.canArbitrate)
    }
}
