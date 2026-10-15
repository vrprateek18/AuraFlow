import Foundation

public final class SettingsRepository: @unchecked Sendable {
    private let userDefaults: UserDefaults
    private let settingsKey = "com.auramotion.settings"
    private let calibrationPrefix = "com.auramotion.calibration."

    public init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
    }

    public func loadSettings() -> AppSettings {
        guard let data = userDefaults.data(forKey: settingsKey),
              let saved = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let defaultsData = try? JSONEncoder().encode(AppSettings()),
              var merged = try? JSONSerialization.jsonObject(with: defaultsData) as? [String: Any] else {
            return AppSettings()
        }
        // Older installations have no swipeAction or isPalmSwipeEnabled keys.
        // Fill only missing fields rather than silently discarding every saved setting.
        merged.merge(saved) { _, savedValue in savedValue }
        guard let mergedData = try? JSONSerialization.data(withJSONObject: merged),
              let settings = try? JSONDecoder().decode(AppSettings.self, from: mergedData) else {
            return AppSettings()
        }
        return settings
    }

    public func saveSettings(_ settings: AppSettings) {
        if let data = try? JSONEncoder().encode(settings) {
            userDefaults.set(data, forKey: settingsKey)
        }
    }

    public func loadCalibration(cameraID: String, displayID: UInt32, arrangementHash: Int) -> CalibrationProfile {
        let key = calibrationKey(cameraID: cameraID, displayID: displayID, arrangementHash: arrangementHash)
        guard let data = userDefaults.data(forKey: key),
              let profile = try? JSONDecoder().decode(CalibrationProfile.self, from: data) else {
            return CalibrationProfile(cameraUniqueID: cameraID, displayID: displayID, displayArrangementHash: arrangementHash)
        }
        return profile
    }

    public func saveCalibration(_ profile: CalibrationProfile) {
        let key = calibrationKey(cameraID: profile.cameraUniqueID, displayID: profile.displayID, arrangementHash: profile.displayArrangementHash)
        if let data = try? JSONEncoder().encode(profile) {
            userDefaults.set(data, forKey: key)
        }
    }

    private func calibrationKey(cameraID: String, displayID: UInt32, arrangementHash: Int) -> String {
        return "\(calibrationPrefix)\(cameraID)_\(displayID)_\(arrangementHash)_v\(CalibrationProfile.currentMappingVersion)"
    }
}
