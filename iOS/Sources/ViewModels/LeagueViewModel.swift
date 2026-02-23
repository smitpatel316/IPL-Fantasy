import Foundation
import Combine

// MARK: - League View Model
@MainActor
class LeagueViewModel: ObservableObject {
    @Published var leagues: [League] = []
    @Published var currentLeague: League?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var showCreateLeague = false
    @Published var showJoinLeague = false
    
    // Create/Join form
    @Published var newLeagueName = ""
    @Published var newLeagueMaxTeams = 10
    @Published var newLeagueBudget = 100.0
    @Published var joinCode = ""
    @Published var teamName = ""
    
    private let leagueService = LeagueService.shared
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        leagueService.$leagues
            .receive(on: DispatchQueue.main)
            .assign(to: &$leagues)
    }
    
    func loadLeagues() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let fetchedLeagues = try await leagueService.fetchLeagues()
            leagues = fetchedLeagues
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func loadLeagueDetails(id: String) async {
        isLoading = true
        errorMessage = nil
        
        do {
            currentLeague = try await leagueService.getLeagueDetails(id: id)
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func createLeague() async {
        guard !newLeagueName.isEmpty else {
            errorMessage = "Please enter league name"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let league = try await leagueService.createLeague(
                name: newLeagueName,
                maxTeams: newLeagueMaxTeams,
                budget: newLeagueBudget
            )
            currentLeague = league
            showCreateLeague = false
            clearCreateForm()
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func joinLeague() async {
        guard !joinCode.isEmpty, !teamName.isEmpty else {
            errorMessage = "Please enter code and team name"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let league = try await leagueService.joinLeague(code: joinCode, teamName: teamName)
            currentLeague = league
            showJoinLeague = false
            clearJoinForm()
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func selectLeague(_ league: League) {
        currentLeague = league
    }
    
    // MARK: - Invite Methods
    
    func validateInviteCode(_ code: String) async throws -> InviteValidationResult {
        try await leagueService.validateInviteCode(code)
    }
    
    func getInviteLink(leagueId: String) async throws -> InviteLink {
        try await leagueService.getInviteLink(leagueId: leagueId)
    }
    
    func regenerateInviteCode(leagueId: String) async throws -> String {
        try await leagueService.regenerateInviteCode(leagueId: leagueId)
    }
    
    private func clearCreateForm() {
        newLeagueName = ""
        newLeagueMaxTeams = 10
        newLeagueBudget = 100.0
    }
    
    private func clearJoinForm() {
        joinCode = ""
        teamName = ""
    }
}
