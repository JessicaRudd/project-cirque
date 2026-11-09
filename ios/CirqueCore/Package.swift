// swift-tools-version: 6.0
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "CirqueCore",
    platforms: [
        .iOS(.v18),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "CirqueCore",
            targets: ["CirqueCore"]
        )
    ],
    dependencies: [],
    targets: [
        .target(
            name: "CirqueCore",
            dependencies: [],
            path: "Sources/CirqueCore",
            swiftSettings: [
                .enableExperimentalFeature("StrictConcurrency")
            ],
            linkerSettings: [
                .linkedLibrary("sqlite3")
            ]
        ),
        .testTarget(
            name: "CirqueCoreTests",
            dependencies: ["CirqueCore"],
            path: "Tests/CirqueCoreTests",
            linkerSettings: [
                .linkedLibrary("sqlite3")
            ]
        )
    ]
)
