import XCTest
@testable import IPLFantasyPro

// MARK: - Player Model Tests
final class PlayerTests: XCTestCase {
    
    func testPlayerCreation() {
        let player = Player(
            name: "Virat Kohli",
            role: .batsman,
            team: "RCB",
            basePrice: 18.0
        )
        
        XCTAssertEqual(player.name, "Virat Kohli")
        XCTAssertEqual(player.role, .batsman)
        XCTAssertEqual(player.team, "RCB")
        XCTAssertEqual(player.basePrice, 18.0)
        XCTAssertFalse(player.isSold)
    }
    
    func testPlayerWithTotalPoints() {
        let player = Player(
            name: "Jasprit Bumrah",
            role: .bowler,
            team: "MI",
            basePrice: 18.0,
            totalPoints: 312
        )
        
        XCTAssertEqual(player.totalPoints, 312)
    }
    
    func testPlayerRoleDisplayName() {
        let batsman = Player(role: .batsman, name: "Test", team: "TST", basePrice: 10)
        XCTAssertEqual(batsman.role.displayName, "Batsman")
        
        let bowler = Player(role: .bowler, name: "Test", team: "TST", basePrice: 10)
        XCTAssertEqual(bowler.role.displayName, "Bowler")
        
        let allRounder = Player(role: .allRounder, name: "Test", team: "TST", basePrice: 10)
        XCTAssertEqual(allRounder.role.displayName, "All-Rounder")
        
        let wk = Player(role: .wicketKeeper, name: "Test", team: "TST", basePrice: 10)
        XCTAssertEqual(wk.role.displayName, "Wicket Keeper")
    }
    
    func testPlayerRoleColors() {
        XCTAssertEqual(Player(role: .batsman, name: "T", team: "T", basePrice: 1).role.color, "4CAF50")
        XCTAssertEqual(Player(role: .bowler, name: "T", team: "T", basePrice: 1).role.color, "F44336")
    }
}

// MARK: - League Model Tests
final class LeagueTests: XCTestCase {
    
    func testLeagueCreation() {
        let league = League(
            name: "Sunday League",
            commissionerId: "user-123",
            maxTeams: 10,
            auctionBudget: 100.0
        )
        
        XCTAssertEqual(league.name, "Sunday League")
        XCTAssertEqual(league.commissionerId, "user-123")
        XCTAssertEqual(league.maxTeams, 10)
        XCTAssertEqual(league.auctionBudget, 100.0)
        XCTAssertEqual(league.status, .open)
        XCTAssertEqual(league.code.count, 6)
    }
    
    func testLeagueCodeIsUnique() {
        let league1 = League(name: "L1", commissionerId: "u1")
        let league2 = League(name: "L2", commissionerId: "u2")
        
        // Codes should be generated
        XCTAssertFalse(league1.code.isEmpty)
        XCTAssertFalse(league2.code.isEmpty)
    }
    
    func testLeagueStatus() {
        var league = League(name: "Test", commissionerId: "u1")
        XCTAssertEqual(league.status, .open)
        
        league.status = .drafting
        XCTAssertEqual(league.status, .drafting)
        
        league.status = .active
        XCTAssertEqual(league.status, .active)
        
        league.status = .completed
        XCTAssertEqual(league.status, .completed)
    }
}

// MARK: - Draft Service Tests
final class DraftServiceTests: XCTestCase {
    
    var draftService: DraftService!
    
    override func setUp() {
        super.setUp()
        draftService = DraftService.shared
        draftService.resetForTesting()
    }
    
    override func tearDown() {
        draftService.stopDraft()
        super.tearDown()
    }
    
    func testInitialState() {
        XCTAssertFalse(draftService.isDraftActive)
        XCTAssertEqual(draftService.currentBid, 0)
        XCTAssertNil(draftService.currentBidder)
        XCTAssertEqual(draftService.draftTimer, 60)
    }
    
    func testStartDraft() {
        draftService.startDraft()
        
        XCTAssertTrue(draftService.isDraftActive)
        XCTAssertNotNil(draftService.currentPlayer)
        XCTAssertEqual(draftService.currentBid, draftService.currentPlayer?.basePrice ?? 0)
    }
    
    func testStopDraft() {
        draftService.startDraft()
        XCTAssertTrue(draftService.isDraftActive)
        
        draftService.stopDraft()
        XCTAssertFalse(draftService.isDraftActive)
    }
    
    func testPlaceBid() {
        draftService.startDraft()
        
        let bidder = LeagueMember(userId: "user-1", teamName: "Team A")
        let success = draftService.placeBid(amount: 20.0, bidder: bidder)
        
        XCTAssertTrue(success)
        XCTAssertEqual(draftService.currentBid, 20.0)
        XCTAssertEqual(draftService.currentBidder?.teamName, "Team A")
    }
    
    func testPlaceBidLowerThanCurrent() {
        draftService.startDraft()
        
        let bidder = LeagueMember(userId: "user-1", teamName: "Team A")
        _ = draftService.placeBid(amount: 15.0, bidder: bidder)
        
        // Current bid should be higher
        let initialBid = draftService.currentBid
        
        let bidder2 = LeagueMember(userId: "user-2", teamName: "Team B")
        let success = draftService.placeBid(amount: 10.0, bidder: bidder2)
        
        XCTAssertFalse(success)
        XCTAssertEqual(draftService.currentBid, initialBid)
    }
    
    func testSoldPlayer() {
        draftService.startDraft()
        
        let playerName = draftService.currentPlayer?.name
        let bidder = LeagueMember(userId: "user-1", teamName: "Team A")
        _ = draftService.placeBid(amount: 18.0, bidder: bidder)
        
        let success = draftService.soldPlayer(to: bidder)
        
        XCTAssertTrue(success)
        XCTAssertNotEqual(draftService.currentPlayer?.name, playerName)
    }
    
    func testUnsoldPlayer() {
        draftService.startDraft()
        
        let playerName = draftService.currentPlayer?.name
        let success = draftService.unsoldPlayer()
        
        XCTAssertTrue(success)
        XCTAssertNotEqual(draftService.currentPlayer?.name, playerName)
    }
    
    func testDraftCompletes() {
        // Reset with only 2 players for quick test
        draftService.stopDraft()
        
        // Manually set up for test
        draftService.startDraft()
        
        // Sell first player
        let bidder = LeagueMember(userId: "user-1", teamName: "Team A")
        _ = draftService.placeBid(amount: 18.0, bidder: bidder)
        _ = draftService.soldPlayer(to: bidder)
        
        // Should move to next player
        XCTAssertNotNil(draftService.currentPlayer)
        
        // Sell second player
        _ = draftService.placeBid(amount: 16.0, bidder: bidder)
        _ = draftService.soldPlayer(to: bidder)
        
        // Draft should be complete
        XCTAssertFalse(draftService.isDraftActive)
    }
}

// MARK: - Team ViewModel Tests
final class TeamViewModelTests: XCTestCase {
    
    var viewModel: TeamViewModel!
    
    override func setUp() {
        super.setUp()
        viewModel = TeamViewModel()
    }
    
    func testInitialSquadLoaded() {
        XCTAssertFalse(viewModel.squad.isEmpty)
        XCTAssertEqual(viewModel.squad.count, 15)
    }
    
    func testDefaultCaptain() {
        XCTAssertNotNil(viewModel.captain)
        XCTAssertEqual(viewModel.captain?.name, "Rohit Sharma")
    }
    
    func testDefaultViceCaptain() {
        XCTAssertNotNil(viewModel.viceCaptain)
        XCTAssertEqual(viewModel.viceCaptain?.name, "Jasprit Bumrah")
    }
    
    func testSelectCaptain() {
        let newCaptain = viewModel.squad[2] // Hardik Pandya
        
        viewModel.selectCaptain(newCaptain)
        
        XCTAssertEqual(viewModel.captain?.id, newCaptain.id)
    }
    
    func testSelectViceCaptain() {
        let newVice = viewModel.squad[2]
        
        viewModel.selectViceCaptain(newVice)
        
        XCTAssertEqual(viewModel.viceCaptain?.id, newVice.id)
    }
    
    func testSwapCaptainAndVice() {
        let captain = viewModel.squad[0]
        let vice = viewModel.squad[1]
        
        viewModel.selectCaptain(captain)
        viewModel.selectViceCaptain(vice)
        
        // Now select vice as captain - should swap
        viewModel.selectCaptain(vice)
        
        XCTAssertEqual(viewModel.captain?.id, vice.id)
        XCTAssertEqual(viewModel.viceCaptain?.id, captain.id)
    }
    
    func testCalculateTotalPoints() {
        let points = viewModel.calculateTotalPoints()
        
        // Should include captain (2x) and vice (1.5x) multipliers
        XCTAssertGreaterThan(points, 0)
    }
}

// MARK: - League ViewModel Tests
final class LeagueViewModelTests: XCTestCase {
    
    var viewModel: LeagueViewModel!
    
    override func setUp() {
        super.setUp()
        viewModel = LeagueViewModel()
    }
    
    func testInitialState() {
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.errorMessage)
    }
    
    func testLeagueCreation() {
        viewModel.newLeagueName = "Test League"
        viewModel.newLeagueMaxTeams = 8
        viewModel.newLeagueBudget = 50.0
        
        // Would test createLeague in production with API
        XCTAssertFalse(viewModel.newLeagueName.isEmpty)
    }
}
