import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class SettingsMigrationTests: XCTestCase {
    func testMigratedSettingsRouteBothSwipeDirectionsToAppSwitching() throws {
        let name = "AuraMotion.MigrationTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        defaults.set(Data(#"{"isCameraMirrored":true}"#.utf8), forKey: "com.auramotion.settings")
        let settings = SettingsRepository(userDefaults: defaults).loadSettings()
        let poster = RecordingEventPoster()
        for direction in [PalmSwipeDirection.left, .right] {
            poster.reset()
            poster.postSwipe(direction: direction, action: settings.swipeAction)
            let flags: CGEventFlags = direction == .left ? [.maskCommand, .maskShift] : .maskCommand
            XCTAssertTrue(poster.allEvents.contains(.keyEvent(virtualKey: 48, keyDown: true, flags: flags.rawValue)))
            XCTAssertEqual(poster.allEvents.last, .keyEvent(virtualKey: 55, keyDown: false, flags: 0))
        }
    }
    func testLegacySettingsPreservePreferencesAndGainSwipeOptions() throws {
        let name = "AuraMotion.MigrationTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        defaults.set(Data(#"{"isCameraMirrored":false,"clutchDwellTime":0.12,"showHUD":false}"#.utf8), forKey: "com.auramotion.settings")
        let settings = SettingsRepository(userDefaults: defaults).loadSettings()
        XCTAssertFalse(settings.isCameraMirrored)
        XCTAssertFalse(settings.showHUD)
        XCTAssertEqual(settings.clutchDwellTime, 0.12)
        XCTAssertTrue(settings.isPalmSwipeEnabled)
        XCTAssertEqual(settings.swipeAction, .switchApp)
    }

    func testExplicitSwipeSelectionSurvivesReload() throws {
        let name = "AuraMotion.MigrationTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let repository = SettingsRepository(userDefaults: defaults)
        for action in SwipeActionType.allCases {
            let settings = AppSettings(swipeAction: action)
            repository.saveSettings(settings)
            XCTAssertEqual(repository.loadSettings(), settings)
        }
    }

    func testFirstLaunchCompletedDefaultsToFalse() {
        let settings = AppSettings()
        XCTAssertFalse(settings.firstLaunchCompleted)
    }

    func testFirstLaunchCompletedSurvivesReload() throws {
        let name = "AuraMotion.MigrationTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let repository = SettingsRepository(userDefaults: defaults)

        var settings = repository.loadSettings()
        XCTAssertFalse(settings.firstLaunchCompleted)

        settings.firstLaunchCompleted = true
        repository.saveSettings(settings)

        let reloaded = repository.loadSettings()
        XCTAssertTrue(reloaded.firstLaunchCompleted)
    }

    func testLegacySettingsDefaultFirstLaunchCompletedToFalse() throws {
        let name = "AuraMotion.MigrationTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        defaults.set(Data(#"{"isCameraMirrored":true,"showHUD":true}"#.utf8), forKey: "com.auramotion.settings")
        let settings = SettingsRepository(userDefaults: defaults).loadSettings()
        XCTAssertFalse(settings.firstLaunchCompleted)
    }
}
