import SwiftUI

// MARK: - AuraFlow Design System Color Tokens

public extension Color {
    static let auraMidnightNavy = Color(red: 7/255, green: 17/255, blue: 31/255)      // #07111F
    static let auraDeepSurface  = Color(red: 13/255, green: 28/255, blue: 46/255)     // #0D1C2E
    static let auraCardSurface  = Color(red: 18/255, green: 49/255, blue: 73/255)     // #123149
    static let auraFlowCyan     = Color(red: 32/255, green: 191/255, blue: 234/255)   // #20BFEA
    static let auraIceBlue      = Color(red: 140/255, green: 235/255, blue: 255/255)  // #8CEBFF
    static let auraSuccess      = Color(red: 0/255, green: 229/255, blue: 163/255)    // #00E5A3
    static let auraCoralAlert   = Color(red: 255/255, green: 59/255, blue: 92/255)    // #FF3B5C
    static let auraTextMuted    = Color(red: 138/255, green: 155/255, blue: 168/255) // #8A9BA8
}

// MARK: - AuraFlow Vector Logo

public struct AuraFlowLogoView: View {
    public var size: CGFloat
    public var isAnimated: Bool

    @State private var pulsePhase: CGFloat = 0.0

    public init(size: CGFloat = 64, isAnimated: Bool = true) {
        self.size = size
        self.isAnimated = isAnimated
    }

    public var body: some View {
        ZStack {
            // Ripple 1
            Circle()
                .stroke(Color.auraFlowCyan.opacity(0.18 + 0.08 * sin(pulsePhase)), lineWidth: 1.5)
                .frame(width: size * 1.1, height: size * 1.1)

            // Ripple 2
            Circle()
                .stroke(Color.auraFlowCyan.opacity(0.35 + 0.12 * sin(pulsePhase + 1.0)), lineWidth: 2.0)
                .frame(width: size * 0.85, height: size * 0.85)

            // Trajectory Arc
            Circle()
                .trim(from: 0.1, to: 0.75)
                .stroke(
                    LinearGradient(
                        colors: [Color.auraFlowCyan, Color.auraIceBlue],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    style: StrokeStyle(lineWidth: 3.0, lineCap: .round)
                )
                .frame(width: size * 0.62, height: size * 0.62)
                .rotationEffect(.degrees(isAnimated ? (pulsePhase * 30).truncatingRemainder(dividingBy: 360) : 45))

            // Center Core Glow
            Circle()
                .fill(
                    RadialGradient(
                        gradient: Gradient(colors: [Color.auraIceBlue, Color.auraFlowCyan.opacity(0.8)]),
                        center: .center,
                        startRadius: 0,
                        endRadius: size * 0.22
                    )
                )
                .frame(width: size * 0.32, height: size * 0.32)
                .shadow(color: Color.auraFlowCyan.opacity(0.7), radius: 8)

            // Inner Highlight
            Circle()
                .fill(Color.white)
                .frame(width: size * 0.12, height: size * 0.12)
        }
        .frame(width: size * 1.25, height: size * 1.25)
        .onAppear {
            if isAnimated {
                withAnimation(Animation.linear(duration: 4.0).repeatForever(autoreverses: false)) {
                    pulsePhase = .pi * 2
                }
            }
        }
    }
}

// MARK: - AuraFlow Button Styles

public struct AuraFlowPrimaryButtonStyle: ButtonStyle {
    public init() {}
    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .bold))
            .foregroundColor(Color(red: 5/255, green: 11/255, blue: 20/255))
            .padding(.horizontal, 22)
            .padding(.vertical, 10)
            .background(
                LinearGradient(
                    colors: [Color.auraFlowCyan, Color.auraIceBlue],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .cornerRadius(8)
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .shadow(color: Color.auraFlowCyan.opacity(0.35), radius: 6, x: 0, y: 2)
    }
}

public struct AuraFlowSecondaryButtonStyle: ButtonStyle {
    public init() {}
    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .semibold))
            .foregroundColor(.white)
            .padding(.horizontal, 18)
            .padding(.vertical, 9)
            .background(Color.auraCardSurface.opacity(0.8))
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
    }
}

public struct AuraFlowOutlineButtonStyle: ButtonStyle {
    public init() {}
    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .medium))
            .foregroundColor(Color.auraTextMuted)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Color.clear)
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
    }
}
