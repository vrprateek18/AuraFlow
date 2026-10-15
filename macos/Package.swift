// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AuraFlow",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "AuraFlow", targets: ["AuraMotionApp"]),
        .executable(name: "AuraMotion", targets: ["AuraMotionApp"]),
        .library(name: "AuraMotionCore", targets: ["AuraMotionCore"])
    ],
    targets: [
        // C11 Lock-free Atomics module for event-tap arbitration
        .target(
            name: "AuraAtomics",
            publicHeadersPath: "include"
        ),
        // Core framework: Vision, Tracking, Interaction, Event Synthesis
        .target(
            name: "AuraMotionCore",
            dependencies: [
                "AuraAtomics"
            ]
        ),
        // App executable: Menu Bar, Floating HUD, Diagnostics UI
        .executableTarget(
            name: "AuraMotionApp",
            dependencies: [
                "AuraMotionCore"
            ]
        ),
        // Comprehensive test suite
        .testTarget(
            name: "AuraMotionTests",
            dependencies: [
                "AuraMotionCore",
                "AuraAtomics"
            ],
            resources: [
                .copy("Fixtures")
            ]
        )
    ]
)
