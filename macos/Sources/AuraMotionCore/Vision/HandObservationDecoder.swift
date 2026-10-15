import Foundation
import Vision
import CoreGraphics

public enum HandObservationDecoder {
    /// Mapping of VNRecognizedPointKey to our HandJointName.
    private static let keyMap: [(VNHumanHandPoseObservation.JointName, HandJointName)] = [
        (.wrist, .wrist),
        (.thumbCMC, .thumbCMC),
        (.thumbMP, .thumbMP),
        (.thumbIP, .thumbIP),
        (.thumbTip, .thumbTip),
        (.indexMCP, .indexMCP),
        (.indexPIP, .indexPIP),
        (.indexDIP, .indexDIP),
        (.indexTip, .indexTip),
        (.middleMCP, .middleMCP),
        (.middlePIP, .middlePIP),
        (.middleDIP, .middleDIP),
        (.middleTip, .middleTip),
        (.ringMCP, .ringMCP),
        (.ringPIP, .ringPIP),
        (.ringDIP, .ringDIP),
        (.ringTip, .ringTip),
        (.littleMCP, .littleMCP),
        (.littlePIP, .littlePIP),
        (.littleDIP, .littleDIP),
        (.littleTip, .littleTip)
    ]

    /// Decodes a Vision observation into a safe HandSample value type.
    public static func decode(
        observation: VNHumanHandPoseObservation,
        hostTimestamp: TimeInterval,
        presentationTime: Double,
        isEstimatedTime: Bool,
        trackingID: Int,
        isMirrored: Bool
    ) -> HandSample {
        var jointsDict: [HandJointName: HandJoint] = [:]
        var totalConfidence: Float = 0.0
        var recognizedCount: Float = 0.0

        for (vnName, domainName) in keyMap {
            if let point = try? observation.recognizedPoint(vnName), point.confidence > 0.1 {
                // Apply camera mirroring if requested: mirror X coordinate in normalized space
                let pos = isMirrored ? CGPoint(x: 1.0 - point.location.x, y: point.location.y) : point.location
                let joint = HandJoint(name: domainName, position: pos, confidence: point.confidence)
                jointsDict[domainName] = joint
                totalConfidence += point.confidence
                recognizedCount += 1.0
            }
        }

        // Vision may intentionally omit occluded or out-of-frame joints. Averaging over
        // all 21 possible landmarks incorrectly turns a clear, partially visible pointing
        // hand into a low-confidence sample and blocks gesture output. Confidence should
        // describe the landmarks Vision actually recognized; individual gesture checks
        // still enforce their own joint-confidence requirements.
        let overallConf = overallConfidence(total: totalConfidence, recognizedCount: recognizedCount)
        let handedness = estimateChirality(joints: jointsDict)

        return HandSample(
            hostTimestamp: hostTimestamp,
            presentationTimeSeconds: presentationTime,
            isPresentationTimeEstimated: isEstimatedTime,
            joints: jointsDict,
            overallConfidence: overallConf,
            estimatedHandedness: handedness,
            trackingID: trackingID
        )
    }

    static func overallConfidence(total: Float, recognizedCount: Float) -> Float {
        guard recognizedCount > 0 else { return 0 }
        return total / recognizedCount
    }

    /// 2D Chirality Heuristic using thumb, index, and pinky spatial arrangement.
    /// Strictly an estimate for UI telemetry; NOT safety critical.
    private static func estimateChirality(joints: [HandJointName: HandJoint]) -> EstimatedHandedness {
        guard let thumb = joints[.thumbTip]?.position,
              let index = joints[.indexMCP]?.position,
              let pinky = joints[.littleMCP]?.position else {
            return .unknown
        }

        // Cross product of (index - pinky) and (thumb - index) in 2D
        let vPinkyToIndex = CGPoint(x: index.x - pinky.x, y: index.y - pinky.y)
        let vIndexToThumb = CGPoint(x: thumb.x - index.x, y: thumb.y - index.y)
        let cross = vPinkyToIndex.x * vIndexToThumb.y - vPinkyToIndex.y * vIndexToThumb.x

        if abs(cross) < 0.005 {
            return .unknown
        }
        return cross > 0 ? .right : .left
    }
}
