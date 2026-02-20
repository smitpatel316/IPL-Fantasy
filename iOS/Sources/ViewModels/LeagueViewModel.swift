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
    
    func loadLeagues() {
        leagues = leagueService.getLeagues()
    }
    
    func createLeague(commissionerId: String) {
        guard !newLeagueName.isEmpty else {
            errorMessage = "Please enter league name"
            return
        }
        
        isLoading = true
        
        let league = leagueService.createLeague(
            name: newLeagueName,
            commissionerId: commissionerId,
            maxTeams: newLeagueMaxTeams,
            budget: newLeagueBudget
        )
        
        currentLeague = league
        showCreateLeague = false
        clearCreateForm()
        isLoading = false
    }
    
    func joinLeague(user: User) {
        guard !joinCode.isEmpty, !teamName.isEmpty else {
            errorMessage = "Please enter code and team name"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            if let league = try leagueService.joinLeague(code: joinCode, user: user, teamName: teamName) {
                currentLeague = league
            }
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
