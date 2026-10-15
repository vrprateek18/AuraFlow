import AppKit
import SwiftUI
import AuraMotionCore

@MainActor
final class CommandMenuWindowController {
    private let panel: NSPanel
    private var hostingView: NSHostingView<CommandMenuView>?
    init() {
        panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 560, height: 430),
                        styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.level = .floating
        panel.isFloatingPanel = true
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.ignoresMouseEvents = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
    }

    func update(_ menu: CommandMenuSnapshot?) {
        guard let menu else { panel.orderOut(nil); return }
        if !panel.isVisible {
            let height = CGDisplayBounds(CGMainDisplayID()).height
            let point = CGPoint(x: menu.target.x, y: height - menu.target.y)
            if let screen = NSScreen.screens.first(where: { $0.frame.contains(point) }) ?? NSScreen.main {
                let visible = screen.visibleFrame
                panel.setFrameOrigin(CGPoint(x: visible.midX - 280, y: visible.midY - 215))
            }
        }
        if let hostingView {
            hostingView.rootView = CommandMenuView(menu: menu)
        } else {
            let hostingView = NSHostingView(rootView: CommandMenuView(menu: menu))
            self.hostingView = hostingView
            panel.contentView = hostingView
        }
        panel.orderFrontRegardless()
    }
}

private struct CommandMenuView: View {
    let menu: CommandMenuSnapshot
    private let columns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "hand.draw.fill").foregroundStyle(.cyan)
                Text("HAND COMMANDS").font(.system(size: 13, weight: .bold, design: .rounded))
                Spacer()
                Text("Point · Pinch").font(.caption).foregroundStyle(.secondary)
            }
            Text(menu.awaitingPointer ? "Raise your index finger to begin" : "Move your hand to choose. Pinch to confirm.")
                .font(.system(size: 20, weight: .semibold))
            ZStack(alignment: .topLeading) {
                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(GestureCommand.allCases, id: \.self) { command in
                        VStack(spacing: 8) {
                            Image(systemName: command.symbol).font(.system(size: 23))
                            Text(command.title).font(.system(size: 12, weight: .semibold))
                        }
                        .frame(maxWidth: .infinity).frame(height: 72)
                        .foregroundStyle(menu.selected == command ? Color.white : Color.primary)
                        .background(menu.selected == command ? Color.blue : Color.primary.opacity(0.06), in: RoundedRectangle(cornerRadius: 13))
                        .overlay(RoundedRectangle(cornerRadius: 13).stroke(menu.selected == command ? Color.cyan : .clear, lineWidth: 2))
                    }
                }
                if !menu.awaitingPointer {
                    Circle().fill(.white).frame(width: 8, height: 8)
                        .shadow(color: .black.opacity(0.5), radius: 2)
                        .offset(x: menu.pointer.x * 512 - 4, y: menu.pointer.y * 236 - 4)
                        .allowsHitTesting(false)
                }
            }
            Text("Lower or withdraw your hand to dismiss · Closes automatically after 12 seconds")
                .font(.system(size: 11)).foregroundStyle(.secondary)
        }
        .padding(24)
        .frame(width: 560, height: 430)
        .background(.ultraThickMaterial, in: RoundedRectangle(cornerRadius: 24))
        .overlay(RoundedRectangle(cornerRadius: 24).stroke(.white.opacity(0.15)))
    }
}
