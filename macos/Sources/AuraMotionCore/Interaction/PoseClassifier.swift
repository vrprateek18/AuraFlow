import Foundation
import CoreGraphics

public struct HandPoseFeatures: Sendable, Equatable {
    public let normalizedPinchDistance: CGFloat?
    public let isIndexExtended: Bool
    public let isMiddleExtended: Bool
    public let isRingCurled: Bool
    public let isLittleCurled: Bool
    public let isOpenPalm: Bool
    public let isTwoFingerPointing: Bool
    public let isPinchApproach: Bool
    public let extendedFingerCount: Int
}

public enum PoseClassifier {

    // ──────────────────────────────────────────────────────────────────
    // Gesture → Finger Pose Reference Card (Priority Order)
    // ──────────────────────────────────────────────────────────────────
    //
    //  PRIORITY   GESTURE            FINGER SIGNATURE
    //  ────────   ───────            ────────────────
    //  1 (HIGH)   Pinch / Click      thumbTip–indexTip distance < 0.38 normalized
    //  2          Open Palm          3+ of 5 digits extended AND thumb spread AND !pinching
    //  3          Scroll (V-sign)    index ✓ strongly, middle ✓ strongly, ring ✗, little ✗
    //  4 (LOW)    Pointer / Move     index ✓ (default: any non-palm, non-pinch, non-scroll)
    //
    // ──────────────────────────────────────────────────────────────────

    public static func classify(sample: HandSample, pinchReleaseThreshold: CGFloat = 0.38) -> HandPoseFeatures {
        let scale = sample.scaleReference ?? 0.20

        // ── 1. Pinch Distance ──
        var pinchDist: CGFloat?
        if let thumbTip = sample.joint(.thumbTip, minConfidence: 0.20),
           let indexTip = sample.joint(.indexTip, minConfidence: 0.20) {
            let dx = thumbTip.x - indexTip.x
            let dy = thumbTip.y - indexTip.y
            pinchDist = sqrt(dx * dx + dy * dy) / scale
        }

        let isPinchApproach = (pinchDist ?? 1.0) < max(0.42, pinchReleaseThreshold)
        let isPinching = (pinchDist ?? 1.0) < pinchReleaseThreshold

        // ── 2. Finger Extension (scale-adaptive) ──
        let indexExt = fingerExtension(sample: sample, mcp: .indexMCP, pip: .indexPIP, tip: .indexTip, scale: scale)
        let middleExt = fingerExtension(sample: sample, mcp: .middleMCP, pip: .middlePIP, tip: .middleTip, scale: scale)
        let ringExt = fingerExtension(sample: sample, mcp: .ringMCP, pip: .ringPIP, tip: .ringTip, scale: scale)
        let littleExt = fingerExtension(sample: sample, mcp: .littleMCP, pip: .littlePIP, tip: .littleTip, scale: scale)

        // Use GRADUATED thresholds: a "strongly extended" bar for primary gesture fingers,
        // and a softer bar for supporting fingers (palm detection).
        // stronglyExtended = ratio >= 0.85 (clearly sticking out)
        // extended         = ratio >= 0.50 (noticeable extension)
        let isIndexStrong = indexExt >= 0.85
        let isMiddleStrong = middleExt >= 0.85
        let isRingExtended = ringExt >= 0.50
        let isLittleExtended = littleExt >= 0.50
        let isIndexExtended = indexExt >= 0.50
        let isMiddleExtended = middleExt >= 0.50

        // Thumb extension
        let isThumbExt: Bool = {
            guard let thumbTip = sample.joint(.thumbTip, minConfidence: 0.15) else { return false }
            if let indexMCP = sample.joint(.indexMCP, minConfidence: 0.15) {
                if distance(thumbTip, indexMCP) > (scale * 0.65) { return true }
            }
            if let wrist = sample.joint(.wrist, minConfidence: 0.15) {
                if distance(wrist, thumbTip) > (scale * 0.75) { return true }
            }
            return false
        }()

        // ── 3. Digit count and pose classification ──
        let extCount = (isThumbExt ? 1 : 0) + (isIndexExtended ? 1 : 0) + (isMiddleExtended ? 1 : 0) + (isRingExtended ? 1 : 0) + (isLittleExtended ? 1 : 0)

        // OPEN PALM: 3+ digits extended AND thumb is spread AND not actively pinching
        // Thumb-spread is a strong intentional signal that separates palm from accidental loose fingers
        let extendedNonThumbCount = (isIndexExtended ? 1 : 0) + (isMiddleExtended ? 1 : 0) + (isRingExtended ? 1 : 0) + (isLittleExtended ? 1 : 0)
        let isOpen = (extendedNonThumbCount >= 3) && !isPinching

        // TWO-FINGER SCROLL (V-sign):
        //   - Index AND middle must be STRONGLY extended (clearly sticking out)
        //   - Ring AND little must NOT be extended
        //   - Must NOT be open palm
        //   - This prevents "relaxed pointer with slightly spread middle" from triggering scroll
        let isTwoFinger = isIndexStrong && isMiddleStrong && !isRingExtended && !isLittleExtended && !isOpen

        return HandPoseFeatures(
            normalizedPinchDistance: pinchDist,
            isIndexExtended: isIndexExtended,
            isMiddleExtended: isMiddleExtended,
            isRingCurled: !isRingExtended,
            isLittleCurled: !isLittleExtended,
            isOpenPalm: isOpen,
            isTwoFingerPointing: isTwoFinger,
            isPinchApproach: isPinchApproach,
            extendedFingerCount: extCount
        )
    }

    /// Returns a 0.0–1.0 "extension ratio" for a finger.
    /// 0.0 = fully curled, 1.0 = fully extended.
    /// Uses multiple geometric checks for robustness.
    private static func fingerExtension(sample: HandSample, mcp: HandJointName, pip: HandJointName, tip: HandJointName, scale: CGFloat) -> CGFloat {
        guard let mcpPt = sample.joint(mcp, minConfidence: 0.15),
              let tipPt = sample.joint(tip, minConfidence: 0.15) else {
            return 0.0
        }

        let dMCPToTip = distance(mcpPt, tipPt)
        if let wrist = sample.joint(.wrist, minConfidence: 0.15),
           distance(wrist, tipPt) < distance(wrist, mcpPt) * 0.95 {
            return 0
        }
        if let pipPt = sample.joint(pip, minConfidence: 0.15),
           distance(mcpPt, tipPt) < distance(mcpPt, pipPt) * 1.05 {
            return 0
        }

        // Fully curled: tip sitting on MCP
        if dMCPToTip < scale * 0.15 {
            return 0.0
        }

        // Scale-relative extension: how much of the expected finger length is visible
        // A fully extended finger at desk distance spans ~45% of scale
        let fullLength = scale * 0.45
        let ratio = min(dMCPToTip / max(fullLength, 0.01), 1.0)

        // Cross-check with wrist distance for foreshortened angles
        if let wrist = sample.joint(.wrist, minConfidence: 0.15) {
            let dWristToTip = distance(wrist, tipPt)
            let dWristToMCP = distance(wrist, mcpPt)
            if dWristToMCP > 0.01 {
                let wristRatio = dWristToTip / dWristToMCP
                // If tip is farther from wrist than MCP, it's extended (even if foreshortened)
                if wristRatio > 1.15 {
                    return max(ratio, 0.85)
                }
            }
        }

        // PIP cross-check: tip should be farther from MCP than PIP is
        if let pipPt = sample.joint(pip, minConfidence: 0.15) {
            let dMCPToPIP = distance(mcpPt, pipPt)
            if dMCPToPIP > 0.01 {
                let pipRatio = dMCPToTip / dMCPToPIP
                // A folded finger can still be far from its knuckle. Its tip
                // returning toward the knuckle is stronger evidence than length.
                if pipRatio < 1.05 { return 0 }
                if pipRatio > 1.15 {
                    return max(ratio, 0.85)
                }
            }
        }

        return ratio
    }

    private static func distance(_ p1: CGPoint, _ p2: CGPoint) -> CGFloat {
        let dx = p1.x - p2.x
        let dy = p1.y - p2.y
        return sqrt(dx * dx + dy * dy)
    }
}
