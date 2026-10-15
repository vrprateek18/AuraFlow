import AppKit
import SwiftUI

@MainActor
final class ClickFeedbackWindowController {
    private let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 64, height: 64),
        styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
    private var dismissal: Task<Void, Never>?

    init() {
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.ignoresMouseEvents = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
    }

    func show(at point: CGPoint) {
        dismissal?.cancel()
        let height = CGDisplayBounds(CGMainDisplayID()).height
        panel.setFrameOrigin(CGPoint(x: point.x - 32, y: height - point.y - 32))
        panel.contentView = NSHostingView(rootView: ClickRipple().id(UUID()))
        panel.orderFrontRegardless()
        dismissal = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled else { return }
            self?.panel.orderOut(nil)
        }
    }

    func hide() { dismissal?.cancel(); panel.orderOut(nil) }
}

private struct ClickRipple: View {
    @State private var expanded = false
    var body: some View {
        Circle().stroke(Color.cyan, lineWidth: 2)
            .frame(width: 48, height: 48)
            .scaleEffect(expanded ? 1 : 0.25)
            .opacity(expanded ? 0 : 1)
            .frame(width: 64, height: 64)
            .onAppear { withAnimation(.easeOut(duration: 0.38)) { expanded = true } }
    }
}
