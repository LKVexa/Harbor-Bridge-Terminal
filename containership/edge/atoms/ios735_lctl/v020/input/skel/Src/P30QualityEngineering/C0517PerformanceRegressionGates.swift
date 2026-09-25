// Generated from checklist component 517 — do not hand-edit the contract block; regenerate.
// Quality Engineering · quality engineering layer · control family: testOwnership

import Foundation
import ComponentKit

public struct C0517PerformanceRegressionGates: AppComponent {
    public static let contract = ComponentContract(
        id: 517,
        name: "Performance Regression Gates",
        phase: 30,
        phaseName: "Quality Engineering",
        layer: "quality engineering",
        purpose: "Performance Regression Gates: the quality engineering responsibility named by checklist component 517 (Quality Engineering).",
        inputs: ["Performance Regression Gates configuration (typed, validated)", "ComponentContext"],
        outputs: ["Performance Regression Gates state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "static gates, policy enforcement, dependency hygiene, regression prevention",
        budgets: [QualityBudget(metric: "static gates", unit: "count", limit: 100.0), QualityBudget(metric: "policy enforcement", unit: "count", limit: 250.0), QualityBudget(metric: "dependency hygiene", unit: "count", limit: 250.0), QualityBudget(metric: "regression prevention", unit: "count", limit: 250.0)],
        family: .testOwnership,
        userVisible: false,
        donors: [DonorPart(car: "swift-collections-benchmark", part: "Collection benchmark harness", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .testOwnership, clauses: [
        FamilyClause(control: 21, statement: "Define what failures Performance Regression Gates must detect, the ownership of those tests, and the CI stage in which they execute.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Ensure Performance Regression Gates is deterministic: control time, randomness, locale, network, filesystem, user defaults, keychain, and concurrency inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Design Performance Regression Gates to produce actionable failure diagnostics without leaking secrets or depending on developer-machine state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Track flaky behavior for Performance Regression Gates as a defect; quarantine may isolate impact but must not become permanent suppression.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Require representative positive, negative, boundary, concurrency, and regression cases before Performance Regression Gates is considered complete.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
