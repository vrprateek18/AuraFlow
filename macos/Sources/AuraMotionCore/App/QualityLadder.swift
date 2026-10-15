import Foundation

public enum ThermalQualityStage: Int, Sendable, Comparable {
    case nominal = 0     // Full quality (60 FPS inference, 30 FPS HUD)
    case throttleVision = 1 // Skip every 2nd frame (30 FPS inference)
    case throttleHUD = 2    // Drop HUD to 15 FPS
    case disablePreview = 3 // Disable video preview completely
    case downscale = 4      // Downscale camera format (applied only when idle/paused)

    public static func < (lhs: ThermalQualityStage, rhs: ThermalQualityStage) -> Bool {
        return lhs.rawValue < rhs.rawValue
    }
}

/// 4-stage non-disruptive thermal quality ladder.
public final class QualityLadder: @unchecked Sendable {
    public private(set) var activeStage: ThermalQualityStage = .nominal
    private var frameCounter: Int = 0

    public init() {}

    public func updateThermalState(_ thermalState: ProcessInfo.ThermalState) {
        switch thermalState {
        case .nominal:
            activeStage = .nominal
        case .fair:
            activeStage = .throttleVision
        case .serious:
            activeStage = .throttleHUD
        case .critical:
            activeStage = .disablePreview
        @unknown default:
            activeStage = .nominal
        }
    }

    /// Determines if the current frame should be processed by Vision under Stage 1 throttling.
    public func shouldProcessVisionFrame() -> Bool {
        if activeStage >= .throttleVision {
            frameCounter += 1
            return (frameCounter % 2 == 0)
        }
        return true
    }

    /// Target HUD refresh rate based on active stage.
    public var targetHUDFrameRate: Int {
        switch activeStage {
        case .nominal, .throttleVision:
            return 30
        case .throttleHUD, .disablePreview, .downscale:
            return 15
        }
    }
}
