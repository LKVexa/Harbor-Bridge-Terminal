// Generated from checklist component 501 — do not hand-edit the contract block; regenerate.
// Testing Infrastructure · testing layer · control family: general

import Foundation
import ComponentKit

public struct C0501FailureInjection: AppComponent {
    public static let contract = ComponentContract(
        id: 501,
        name: "Failure Injection",
        phase: 29,
        phaseName: "Testing Infrastructure",
        layer: "testing",
        purpose: "Failure Injection: the testing responsibility named by checklist component 501 (Testing Infrastructure).",
        inputs: ["Failure Injection configuration (typed, validated)", "ComponentContext"],
        outputs: ["Failure Injection state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "test isolation, deterministic fixtures, coverage, failure injection, CI execution",
        budgets: [QualityBudget(metric: "test isolation", unit: "count", limit: 100.0), QualityBudget(metric: "deterministic fixtures", unit: "count", limit: 250.0), QualityBudget(metric: "coverage", unit: "count", limit: 250.0), QualityBudget(metric: "failure injection", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: []
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Failure Injection, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Failure Injection.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Failure Injection, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Failure Injection.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Failure Injection while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
