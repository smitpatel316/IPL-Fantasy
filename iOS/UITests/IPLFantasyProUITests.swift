import XCTest

final class IPLFantasyProUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    override func tearDownWithError() throws {
    }

    func testLaunchApp() throws {
        let app = XCUIApplication()
        app.launch()
    }
}
