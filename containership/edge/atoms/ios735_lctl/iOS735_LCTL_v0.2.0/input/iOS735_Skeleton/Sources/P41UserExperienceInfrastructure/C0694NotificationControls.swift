// Generated from checklist component 694 — do not hand-edit the contract block; regenerate.
// User Experience Infrastructure · UX infrastructure layer · control family: pushPayload

import Foundation
import ComponentKit

public struct C0694NotificationControls: AppComponent {
    public static let contract = ComponentContract(
        id: 694,
        name: "Notification Controls",
        phase: 41,
        phaseName: "User Experience Infrastructure",
        layer: "UX infrastructure",
        purpose: "Notification Controls: the UX infrastructure responsibility named by checklist component 694 (User Experience Infrastructure).",
        inputs: ["Notification Controls configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Notification Controls state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request notifications only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["UserNotifications"],
        capabilities: [.notifications],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "state clarity, onboarding, recoverability, settings, user control, interaction quality",
        budgets: [QualityBudget(metric: "state clarity", unit: "count", limit: 100.0), QualityBudget(metric: "onboarding", unit: "count", limit: 250.0), QualityBudget(metric: "recoverability", unit: "count", limit: 250.0), QualityBudget(metric: "settings", unit: "count", limit: 250.0)],
        family: .pushPayload,
        userVisible: true,
        donors: [DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .pushPayload, clauses: [
        FamilyClause(control: 21, statement: "Define APNs/local payload schema and versioning for Notification Controls, with strict size, privacy, and backward-compatibility rules.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Verify Notification Controls across authorization states, token rotation, reinstall, device restore, inactive app, foreground app, and terminated app.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Make Notification Controls routing idempotent so duplicate or out-of-order delivery cannot create duplicate actions or corrupt state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Exclude sensitive content from lock-screen-visible Notification Controls payloads unless explicitly justified and user-controlled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument registration, send, receipt/open, routing, and failure stages for Notification Controls without logging notification secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
