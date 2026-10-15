import Foundation
import CoreGraphics

/// Versioned, display-specific calibration profile.
public struct CalibrationProfile: Sendable, Codable, Equatable {
    public static let currentMappingVersion: Int = 1

    public let cameraUniqueID: String
    public let displayID: UInt32
    public let displayArrangementHash: Int
    public let mappingVersion: Int

    /// Active interaction box in normalized Vision coordinates [0, 1] x [0, 1]
    public var activeRegion: CGRect

    /// Target display global bounds in Quartz coordinates (from CGDisplayBounds)
    public var displayBounds: CGRect

    /// Cursor tracking gain / speed multiplier
    public var cursorGain: Double

    /// Normalized pinch thresholds (scaled by scaleReference)
    public var pinchStartThreshold: CGFloat
    public var pinchReleaseThreshold: CGFloat

    /// Motion deadbands
    public var dragDeadbandPoints: CGFloat
    public var scrollDeadbandPoints: CGFloat
    // Optional fields preserve compatibility with existing saved profiles.
    public var copyContactThreshold: CGFloat?
    public var copyReleaseThreshold: CGFloat?
    public var pasteContactThreshold: CGFloat?
    public var pasteReleaseThreshold: CGFloat?
    public var cursorRestRadius: CGFloat?
    public var cursorMinCutoff: Double?
    public var cursorMotionBeta: Double?

    public init(
        cameraUniqueID: String = "default",
        displayID: UInt32 = 0,
        displayArrangementHash: Int = 0,
        mappingVersion: Int = currentMappingVersion,
        activeRegion: CGRect = CGRect(x: 0.15, y: 0.15, width: 0.70, height: 0.70),
        displayBounds: CGRect = CGRect(x: 0, y: 0, width: 1920, height: 1080),
        cursorGain: Double = 1.0,
        pinchStartThreshold: CGFloat = 0.28,
        pinchReleaseThreshold: CGFloat = 0.38,
        dragDeadbandPoints: CGFloat = 20.0,
        scrollDeadbandPoints: CGFloat = 8.0
    ) {
        self.cameraUniqueID = cameraUniqueID
        self.displayID = displayID
        self.displayArrangementHash = displayArrangementHash
        self.mappingVersion = mappingVersion
        self.activeRegion = activeRegion
        self.displayBounds = displayBounds
        self.cursorGain = cursorGain
        self.pinchStartThreshold = pinchStartThreshold
        self.pinchReleaseThreshold = pinchReleaseThreshold
        self.dragDeadbandPoints = dragDeadbandPoints
        self.scrollDeadbandPoints = scrollDeadbandPoints
    }
}
