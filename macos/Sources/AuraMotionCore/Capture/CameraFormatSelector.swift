import Foundation
@preconcurrency import AVFoundation

public struct CameraSelectionResult: @unchecked Sendable {
    public let device: AVCaptureDevice
    public let format: AVCaptureDevice.Format
    public let targetFrameRate: Double

    public init(device: AVCaptureDevice, format: AVCaptureDevice.Format, targetFrameRate: Double) {
        self.device = device
        self.format = format
        self.targetFrameRate = targetFrameRate
    }
}

public enum CameraFormatSelector {
    /// Discovers available cameras and selects the optimal format.
    public static func selectBestCameraAndFormat() -> CameraSelectionResult? {
        let discoverySession = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera, .external],
            mediaType: .video,
            position: .unspecified
        )

        guard let device = discoverySession.devices.first else {
            return nil
        }

        // Look for 720p or 1080p formats with highest frame rate
        var bestFormat: AVCaptureDevice.Format?
        var maxRate: Double = 0
        var bestPixels: Int32 = .max

        for format in device.formats {
            let dimensions = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
            let width = dimensions.width
            let height = dimensions.height

            // Prefer 1280x720 or 960x540 for ideal balance of Vision precision and speed
            if (width == 1280 && height == 720) || (width == 960 && height == 540) || (width == 1920 && height == 1080) {
                for range in format.videoSupportedFrameRateRanges {
                    let rate = max(range.minFrameRate, min(range.maxFrameRate, 60))
                    let pixels = width * height
                    if rate > maxRate || (rate == maxRate && pixels < bestPixels) {
                        maxRate = rate
                        bestPixels = pixels
                        bestFormat = format
                    }
                }
            }
        }

        let chosenFormat = bestFormat ?? device.activeFormat
        let targetRate = bestFormat != nil ? maxRate : chosenFormat.videoSupportedFrameRateRanges.map {
            max($0.minFrameRate, min($0.maxFrameRate, 60))
        }.max() ?? 30

        return CameraSelectionResult(device: device, format: chosenFormat, targetFrameRate: targetRate)
    }
}
