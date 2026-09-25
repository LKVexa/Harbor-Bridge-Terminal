// Generated from checklist component 408 — do not hand-edit the contract block; regenerate.
// Health and Sensor Domains · health/sensors layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0408FitnessMetrics: AppComponent {
    public static let contract = ComponentContract(
        id: 408,
        name: "Fitness Metrics",
        phase: 23,
        phaseName: "Health and Sensor Domains",
        layer: "health/sensors",
        purpose: "Fitness Metrics: the health/sensors responsibility named by checklist component 408 (Health and Sensor Domains).",
        inputs: ["Fitness Metrics configuration (typed, validated)", "ComponentContext"],
        outputs: ["Fitness Metrics state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["HealthKit", "OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authorization, sensitive data controls, sampling semantics, provenance, privacy",
        budgets: [QualityBudget(metric: "authorization", unit: "count", limit: 100.0), QualityBudget(metric: "sensitive data controls", unit: "count", limit: 250.0), QualityBudget(metric: "sampling semantics", unit: "count", limit: 250.0), QualityBudget(metric: "provenance", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-system-metrics", part: "Process metrics (CPU, memory, fds)", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-homomorphic-encryption", part: "Homomorphic encryption / private information retrieval", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Fitness Metrics must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Fitness Metrics a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Fitness Metrics; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Fitness Metrics during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Fitness Metrics is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
