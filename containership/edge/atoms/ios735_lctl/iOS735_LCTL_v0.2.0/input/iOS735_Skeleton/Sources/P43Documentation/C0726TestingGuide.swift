// Generated from checklist component 726 — do not hand-edit the contract block; regenerate.
// Documentation · documentation layer · control family: testOwnership

import Foundation
import ComponentKit

public struct C0726TestingGuide: AppComponent {
    public static let contract = ComponentContract(
        id: 726,
        name: "Testing Guide",
        phase: 43,
        phaseName: "Documentation",
        layer: "documentation",
        purpose: "Testing Guide: the documentation responsibility named by checklist component 726 (Documentation).",
        inputs: ["Testing Guide configuration (typed, validated)", "ComponentContext"],
        outputs: ["Testing Guide state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authoritative technical records, ownership, change control, diagrams, operational usability",
        budgets: [QualityBudget(metric: "authoritative technical records", unit: "count", limit: 100.0), QualityBudget(metric: "ownership", unit: "count", limit: 250.0), QualityBudget(metric: "change control", unit: "count", limit: 250.0), QualityBudget(metric: "diagrams", unit: "count", limit: 250.0)],
        family: .testOwnership,
        userVisible: false,
        donors: [DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency), DonorPart(car: "swift-snippets", part: "DocC snippet tooling", license: "MIT", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .testOwnership, clauses: [
        FamilyClause(control: 21, statement: "Define what failures Testing Guide must detect, the ownership of those tests, and the CI stage in which they execute.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Ensure Testing Guide is deterministic: control time, randomness, locale, network, filesystem, user defaults, keychain, and concurrency inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Design Testing Guide to produce actionable failure diagnostics without leaking secrets or depending on developer-machine state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Track flaky behavior for Testing Guide as a defect; quarantine may isolate impact but must not become permanent suppression.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Require representative positive, negative, boundary, concurrency, and regression cases before Testing Guide is considered complete.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
