// Generated from checklist component 504 — do not hand-edit the contract block; regenerate.
// Testing Infrastructure · testing layer · control family: testOwnership

import Foundation
import ComponentKit

public struct C0504TestFixtures: AppComponent {
    public static let contract = ComponentContract(
        id: 504,
        name: "Test Fixtures",
        phase: 29,
        phaseName: "Testing Infrastructure",
        layer: "testing",
        purpose: "Test Fixtures: the testing responsibility named by checklist component 504 (Testing Infrastructure).",
        inputs: ["Test Fixtures configuration (typed, validated)", "ComponentContext"],
        outputs: ["Test Fixtures state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "test isolation, deterministic fixtures, coverage, failure injection, CI execution",
        budgets: [QualityBudget(metric: "test isolation", unit: "count", limit: 100.0), QualityBudget(metric: "deterministic fixtures", unit: "count", limit: 250.0), QualityBudget(metric: "coverage", unit: "count", limit: 250.0), QualityBudget(metric: "failure injection", unit: "count", limit: 250.0)],
        family: .testOwnership,
        userVisible: false,
        donors: []
    )

    public static let familyDeclaration = FamilyDeclaration(family: .testOwnership, clauses: [
        FamilyClause(control: 21, statement: "Define what failures Test Fixtures must detect, the ownership of those tests, and the CI stage in which they execute.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Ensure Test Fixtures is deterministic: control time, randomness, locale, network, filesystem, user defaults, keychain, and concurrency inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Design Test Fixtures to produce actionable failure diagnostics without leaking secrets or depending on developer-machine state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Track flaky behavior for Test Fixtures as a defect; quarantine may isolate impact but must not become permanent suppression.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Require representative positive, negative, boundary, concurrency, and regression cases before Test Fixtures is considered complete.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
