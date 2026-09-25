// Generated from checklist component 567 — do not hand-edit the contract block; regenerate.
// Beta Distribution · beta distribution layer · control family: testOwnership

import Foundation
import ComponentKit

public struct C0567TestFlight: AppComponent {
    public static let contract = ComponentContract(
        id: 567,
        name: "TestFlight",
        phase: 34,
        phaseName: "Beta Distribution",
        layer: "beta distribution",
        purpose: "TestFlight: the beta distribution responsibility named by checklist component 567 (Beta Distribution).",
        inputs: ["TestFlight configuration (typed, validated)", "ComponentContext"],
        outputs: ["TestFlight state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "TestFlight governance, cohorts, diagnostics, feedback, acceptance criteria",
        budgets: [QualityBudget(metric: "TestFlight governance", unit: "count", limit: 100.0), QualityBudget(metric: "cohorts", unit: "count", limit: 250.0), QualityBudget(metric: "diagnostics", unit: "count", limit: 250.0), QualityBudget(metric: "feedback", unit: "count", limit: 250.0)],
        family: .testOwnership,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .testOwnership, clauses: [
        FamilyClause(control: 21, statement: "Define what failures TestFlight must detect, the ownership of those tests, and the CI stage in which they execute.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Ensure TestFlight is deterministic: control time, randomness, locale, network, filesystem, user defaults, keychain, and concurrency inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Design TestFlight to produce actionable failure diagnostics without leaking secrets or depending on developer-machine state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Track flaky behavior for TestFlight as a defect; quarantine may isolate impact but must not become permanent suppression.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Require representative positive, negative, boundary, concurrency, and regression cases before TestFlight is considered complete.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
