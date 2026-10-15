import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class CommandMenuTests: XCTestCase {
    func testBoundaryTremorDoesNotChangeSelectedTile() {
        let menu = GestureCommandMenu()
        open(menu)
        _ = menu.navigate(index: CGPoint(x: 0.5, y: 0.5), isPointing: true, pinchDistance: 0.7, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.1)
        XCTAssertEqual(menu.snapshot?.selected, .nextApp)
        for frame in 0..<30 {
            let x = frame.isMultiple(of: 2) ? 0.539 : 0.541
            _ = menu.navigate(index: CGPoint(x: x, y: 0.5), isPointing: true, pinchDistance: 0.7, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.2 + Double(frame) / 30)
            XCTAssertEqual(menu.snapshot?.selected, .nextApp)
        }
        for frame in 0..<10 {
            _ = menu.navigate(index: CGPoint(x: 0.58, y: 0.5), isPointing: true, pinchDistance: 0.7, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 12.3 + Double(frame) / 30)
        }
        XCTAssertEqual(menu.snapshot?.selected, .minimize)
    }

    private func open(_ menu: GestureCommandMenu, target: CGPoint = CGPoint(x: 700, y: 400)) {
        for frame in 0...30 {
            menu.observePalm(position: CGPoint(x: 0.5, y: 0.5), timestamp: 10 + Double(frame) / 30, target: target)
            if menu.isOpen { break }
        }
    }

    func testStillPalmOpensButMovingPalmDoesNot() {
        let menu = GestureCommandMenu()
        for frame in 0..<40 {
            XCTAssertFalse(menu.observePalm(position: CGPoint(x: Double(frame) * 0.02, y: 0.5), timestamp: Double(frame) / 30, target: .zero))
        }
        open(menu)
        XCTAssertTrue(menu.isOpen)
        XCTAssertTrue(menu.snapshot?.awaitingPointer == true)
    }

    func testPointThenPinchSelectsOnceAndPreservesOriginalTarget() throws {
        let menu = GestureCommandMenu()
        let target = CGPoint(x: 700, y: 400)
        open(menu, target: target)
        XCTAssertEqual(menu.snapshot?.target, target)
        // First pointer frame establishes the center. Move up-left to Right click.
        XCTAssertNil(menu.navigate(index: CGPoint(x: 0.5, y: 0.5), isPointing: true, pinchDistance: 0.7, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.1))
        XCTAssertNil(menu.navigate(index: CGPoint(x: 0.42, y: 0.58), isPointing: true, pinchDistance: 0.7, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.2))
        XCTAssertEqual(menu.snapshot?.selected, .rightClick)
        XCTAssertNil(menu.navigate(index: CGPoint(x: 0.44, y: 0.56), isPointing: false, pinchDistance: 0.15, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.3))
        XCTAssertEqual(menu.navigate(index: CGPoint(x: 0.46, y: 0.54), isPointing: false, pinchDistance: 0.15, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.4), .rightClick)
        XCTAssertFalse(menu.isOpen)
        XCTAssertTrue(menu.consumeClosingContact(distance: 0.1, releaseThreshold: 0.38))
        XCTAssertTrue(menu.consumeClosingContact(distance: 0.6, releaseThreshold: 0.38))
        XCTAssertFalse(menu.consumeClosingContact(distance: 0.6, releaseThreshold: 0.38))
    }

    func testCancelAndTimeoutCannotExecuteCommands() {
        let menu = GestureCommandMenu()
        open(menu)
        menu.cancel()
        XCTAssertNil(menu.navigate(index: .zero, isPointing: true, pinchDistance: 0.1, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 11.1))
        open(menu)
        XCTAssertNil(menu.navigate(index: .zero, isPointing: true, pinchDistance: 0.1, contactThreshold: 0.28, releaseThreshold: 0.38, timestamp: 30))
        XCTAssertFalse(menu.isOpen)
    }

    func testNineMenuCellsMatchDisplayedOrder() {
        for (index, command) in GestureCommand.allCases.enumerated() {
            let point = CGPoint(x: (Double(index % 3) + 0.5) / 3, y: (Double(index / 3) + 0.5) / 3)
            XCTAssertEqual(GestureCommandMenu.command(at: point), command)
        }
        XCTAssertNil(GestureCommandMenu.command(at: CGPoint(x: -0.1, y: 0)))
    }

    func testNewClickCommandsUseCapturedTargetAndDoNotMoveCursor() {
        let poster = RecordingEventPoster()
        let target = CGPoint(x: 700, y: 400)
        poster.postCommand(.rightClick, at: target)
        poster.postCommand(.doubleClick, at: target)
        XCTAssertEqual(poster.allEvents, [.rightClick(target), .doubleClick(target)])
    }

    func testStaleCommandIsDroppedBeforeValidCommand() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        coordinator.epochProvider = { 2 }
        coordinator.injectionAllowedProvider = { true }
        coordinator.enqueueCommand(.rightClick, at: .zero, epoch: 1)
        coordinator.enqueueCommand(.doubleClick, at: .zero, epoch: 2)
        let done = expectation(description: "Output drained")
        coordinator.enqueueValidatedAction(epoch: 2) { done.fulfill() }
        wait(for: [done], timeout: 1)
        XCTAssertEqual(poster.allEvents, [.doubleClick(.zero)])
    }

    func testWindowHalvesRespectVisibleBoundsAndNegativeDisplayOrigins() {
        let visible = CGRect(x: -1920, y: 25, width: 1920, height: 1025)
        let left = WindowSnapper.frame(in: visible, right: false)
        let right = WindowSnapper.frame(in: visible, right: true)
        XCTAssertEqual(left.union(right), visible)
        XCTAssertEqual(left.maxX, right.minX)
        XCTAssertEqual(left.width, 960)
    }

    func testKeyboardCommandsReleaseModifiers() {
        let poster = RecordingEventPoster()
        for command in [GestureCommand.missionControl, .minimize, .fullScreen] {
            poster.reset()
            poster.postCommand(command, at: .zero)
            XCTAssertEqual(poster.allEvents.count, 2)
            guard case .keyEvent(_, let down, let flags) = poster.allEvents.last else { return XCTFail("Expected key release") }
            XCTAssertFalse(down)
            XCTAssertEqual(flags, 0)
        }
    }
}
