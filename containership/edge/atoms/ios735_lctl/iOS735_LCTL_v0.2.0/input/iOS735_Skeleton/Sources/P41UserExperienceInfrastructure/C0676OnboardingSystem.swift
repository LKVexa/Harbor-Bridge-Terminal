// Generated from checklist component 676 — do not hand-edit the contract block; regenerate.
// User Experience Infrastructure · UX infrastructure layer · control family: general

import Foundation
import ComponentKit

public struct C0676OnboardingSystem: AppComponent {
    public static let contract = ComponentContract(
        id: 676,
        name: "Onboarding System",
        phase: 41,
        phaseName: "User Experience Infrastructure",
        layer: "UX infrastructure",
        purpose: "Onboarding System: the UX infrastructure responsibility named by checklist component 676 (User Experience Infrastructure).",
        inputs: ["Onboarding System configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Onboarding System state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "state clarity, onboarding, recoverability, settings, user control, interaction quality",
        budgets: [QualityBudget(metric: "state clarity", unit: "count", limit: 100.0), QualityBudget(metric: "onboarding", unit: "count", limit: 250.0), QualityBudget(metric: "recoverability", unit: "count", limit: 250.0), QualityBudget(metric: "settings", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: true,
        donors: [DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency), DonorPart(car: "swift-system", part: "Typed file-system/syscall wrappers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Onboarding System, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Onboarding System.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Onboarding System, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Onboarding System.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Onboarding System while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
