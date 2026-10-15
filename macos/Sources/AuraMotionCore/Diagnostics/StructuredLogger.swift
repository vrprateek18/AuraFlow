import Foundation
import os

public enum StructuredLogger {
    public static let capture = Logger(subsystem: "com.auramotion.mac", category: "Capture")
    public static let vision = Logger(subsystem: "com.auramotion.mac", category: "Vision")
    public static let tracking = Logger(subsystem: "com.auramotion.mac", category: "Tracking")
    public static let output = Logger(subsystem: "com.auramotion.mac", category: "Output")
    public static let arbitration = Logger(subsystem: "com.auramotion.mac", category: "Arbitration")
    public static let safety = Logger(subsystem: "com.auramotion.mac", category: "Safety")
}
