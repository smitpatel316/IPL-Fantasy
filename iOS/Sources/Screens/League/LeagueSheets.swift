import SwiftUI

// MARK: - Create League Sheet
struct CreateLeagueSheet: View {
    @ObservedObject var viewModel: LeagueViewModel
    @Environment(\.dismiss) var dismiss
    
    @State private var leagueName = ""
    @State private var maxTeams = 8
    @State private var auctionBudget = 50.0
    @State private var isLoading = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // League Name
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text("League Name")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textSecondary)
                            
                            TextField("Enter league name", text: $leagueName)
                                .textFieldStyle(CustomTextFieldStyle())
                        }
                        
                        // Max Teams
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text("Number of Teams: \(maxTeams)")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textSecondary)
                            
                            Slider(value: Binding(
                                get: { Double(maxTeams) },
                                set: { maxTeams = Int($0) }
                            ), in: 4...20, step: 1)
                            .tint(AppColors.primary)
                        }
                        
                        // Budget
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text("Auction Budget: ₹\(Int(auctionBudget))Cr")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textSecondary)
                            
                            Slider(value: $auctionBudget, in: 20...100, step: 5)
                            .tint(AppColors.primary)
                        }
                        
                        // Create Button
                        Button(action: createLeague) {
                            HStack {
                                if isLoading {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                } else {
                                    Text("Create League")
                                }
                            }
                            .font(AppFonts.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, AppSpacing.md)
                            .background(leagueName.isEmpty ? AppColors.textMuted : AppColors.primary)
                            .cornerRadius(AppCornerRadius.medium)
                        }
                        .disabled(leagueName.isEmpty || isLoading)
                        
                        Spacer()
                    }
                    .padding(AppSpacing.lg)
                }
            }
            .navigationTitle("Create League")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.primary)
                }
            }
        }
    }
    
    private func createLeague() {
        isLoading = true
        // Simulate API call
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            let newLeague = League(
                name: leagueName,
                maxTeams: maxTeams,
                auctionBudget: auctionBudget,
                commissionerId: "currentUser"
            )
            viewModel.leagues.append(newLeague)
            isLoading = false
            dismiss()
        }
    }
}

// MARK: - Join League Sheet
struct JoinLeagueSheet: View {
    @ObservedObject var viewModel: LeagueViewModel
    @Environment(\.dismiss) var dismiss
    
    @State private var leagueCode = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: AppSpacing.xl) {
                    // Icon
                    Image(systemName: "qrcode")
                        .font(.system(size: 60))
                        .foregroundColor(AppColors.primary)
                        .padding(.top, AppSpacing.xxl)
                    
                    // Title
                    Text("Join League")
                        .font(AppFonts.title)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text("Enter the league code shared by your friend")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.textSecondary)
                        .multilineTextAlignment(.center)
                    
                    // Code Input
                    VStack(alignment: .leading, spacing: AppSpacing.sm) {
                        Text("League Code")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textSecondary)
                        
                        TextField("Enter code", text: $leagueCode)
                            .textFieldStyle(CustomTextFieldStyle())
                            .textInputAutocapitalization(.characters)
                            .autocorrectionDisabled()
                    }
                    
                    // Error message
                    if let error = errorMessage {
                        Text(error)
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.error)
                    }
                    
                    // Join Button
                    Button(action: joinLeague) {
                        HStack {
                            if isLoading {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            } else {
                                Text("Join League")
                            }
                        }
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, AppSpacing.md)
                        .background(leagueCode.isEmpty ? AppColors.textMuted : AppColors.primary)
                        .cornerRadius(AppCornerRadius.medium)
                    }
                    .disabled(leagueCode.isEmpty || isLoading)
                    
                    Spacer()
                }
                .padding(AppSpacing.lg)
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.primary)
                }
            }
        }
    }
    
    private func joinLeague() {
        isLoading = true
        errorMessage = nil
        
        // Simulate API call
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            // Find league by code
            if let league = viewModel.leagues.first(where: { $0.code == leagueCode }) {
                // Join success
                dismiss()
            } else {
                errorMessage = "League not found. Check the code and try again."
            }
            isLoading = false
        }
    }
}

// MARK: - Custom Text Field Style
struct CustomTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(AppSpacing.md)
            .background(AppColors.surface)
            .foregroundColor(AppColors.textPrimary)
            .cornerRadius(AppCornerRadius.small)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.small)
                    .stroke(AppColors.textMuted.opacity(0.3), lineWidth: 1)
            )
    }
}
