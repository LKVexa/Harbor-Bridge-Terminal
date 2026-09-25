// Generated from checklist component 497 — do not hand-edit the contract block; regenerate.
// Testing Infrastructure · testing layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0497SecurityTesting: AppComponent {
    public static let contract = ComponentContract(
        id: 497,
        name: "Security Testing",
        phase: 29,
        phaseName: "Testing Infrastructure",
        layer: "testing",
        purpose: "Security Testing: the testing responsibility named by checklist component 497 (Testing Infrastructure).",
        inputs: ["Security Testing configuration (typed, validated)", "ComponentContext"],
        outputs: ["Security Testing state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "test isolation, deterministic fixtures, coverage, failure injection, CI execution",
        budgets: [QualityBudget(metric: "test isolation", unit: "count", limit: 100.0), QualityBudget(metric: "deterministic fixtures", unit: "count", limit: 250.0), QualityBudget(metric: "coverage", unit: "count", limit: 250.0), QualityBudget(metric: "failure injection", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: []
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Security Testing, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Security Testing secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Security Testing: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Security Testing inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Security Testing fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
