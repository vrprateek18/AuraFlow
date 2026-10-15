#!/bin/bash
set -euo pipefail

echo "============================================================"
echo " AuraMotion Pro - Vision Synthetic Baseline Benchmark"
echo " (Measures minimal framework invocation overhead on empty buffer)"
echo "============================================================"

swift -e '
import Vision
import CoreVideo
import CoreMedia
import Foundation
import QuartzCore

print("Platform: macOS \(ProcessInfo.processInfo.operatingSystemVersionString)")
print("Hardware: \(ProcessInfo.processInfo.activeProcessorCount) cores, Apple Silicon")
print("Vision Active Revision: \(VNDetectHumanHandPoseRequestRevision1)")

// Create test 1280x720 32BGRA pixel buffer (blank frame baseline)
var pixelBuffer: CVPixelBuffer?
CVPixelBufferCreate(kCFAllocatorDefault, 1280, 720, kCVPixelFormatType_32BGRA, nil, &pixelBuffer)

guard let buffer = pixelBuffer else {
    print("Failed to allocate pixel buffer")
    exit(1)
}

let request = VNDetectHumanHandPoseRequest()
request.revision = VNDetectHumanHandPoseRequestRevision1
request.maximumHandCount = 1

print("\nRunning warm-up passes (10 frames)...")
for _ in 0..<10 {
    let handler = VNImageRequestHandler(cvPixelBuffer: buffer, orientation: .up, options: [:])
    try? handler.perform([request])
}

print("Running 100 inference passes on baseline test buffer...")
var durations: [Double] = []

for _ in 0..<100 {
    let t0 = CACurrentMediaTime()
    let handler = VNImageRequestHandler(cvPixelBuffer: buffer, orientation: .up, options: [:])
    try? handler.perform([request])
    let t1 = CACurrentMediaTime()
    durations.append((t1 - t0) * 1000.0) // ms
}

durations.sort()
let p50 = durations[Int(Double(durations.count) * 0.50)]
let p95 = durations[Int(Double(durations.count) * 0.95)]
let minVal = durations.first ?? 0
let maxVal = durations.last ?? 0
let avg = durations.reduce(0, +) / Double(durations.count)

print("\n--- Synthetic Baseline Results ---")
print(String(format: "Synthetic Invocation Min: %.2f ms", minVal))
print(String(format: "Synthetic Invocation Avg: %.2f ms", avg))
print(String(format: "Synthetic Invocation p50: %.2f ms", p50))
print(String(format: "Synthetic Invocation p95: %.2f ms", p95))
print(String(format: "Synthetic Invocation Max: %.2f ms", maxVal))
print("\n* Note: Measures framework invocation baseline on an empty frame, not end-to-end camera-to-display latency.")
'

echo "============================================================"
