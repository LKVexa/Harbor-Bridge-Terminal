// Generated from checklist component 732 — do not hand-edit the contract block; regenerate.
// Documentation · documentation layer · control family: documentationOwnership

import Foundation
import ComponentKit

public struct C0732CodingStandards: AppComponent {
    public static let contract = ComponentContract(
        id: 732,
        name: "Coding Standards",
        phase: 43,
        phaseName: "Documentation",
        layer: "documentation",
        purpose: "Coding Standards: the documentation responsibility named by checklist component 732 (Documentation).",
        inputs: ["Coding Standards configuration (typed, validated)", "ComponentContext"],
        outputs: ["Coding Standards state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authoritative technical records, ownership, change control, diagrams, operational usability",
        budgets: [QualityBudget(metric: "authoritative technical records", unit: "count", limit: 100.0), QualityBudget(metric: "ownership", unit: "count", limit: 250.0), QualityBudget(metric: "change control", unit: "count", limit: 250.0), QualityBudget(metric: "diagrams", unit: "count", limit: 250.0)],
        family: .documentationOwnership,
        userVisible: false,
        donors: [DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency), DonorPart(car: "swift-snippets", part: "DocC snippet tooling", license: "MIT", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .documentationOwnership, clauses: [
        FamilyClause(control: 21, statement: "Assign an owner, review cadence, audience, source of truth, and change trigger for Coding Standards.", evidence: .humanReview),
        FamilyClause(control: 22, statement: "Make Coding Standards reference versioned interfaces, repositories, diagrams, runbooks, or artifacts rather than ambiguous prose.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Add automated link/reference validation where practical so Coding Standards cannot silently drift from the implementation.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Include failure/recovery procedures, known constraints, security/privacy assumptions, and operational caveats relevant to Coding Standards.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Require Coding Standards updates in the same change set when architecture, APIs, release behavior, or operator workflow changes.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
