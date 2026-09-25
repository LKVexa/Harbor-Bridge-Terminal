// Generated from checklist component 572 — do not hand-edit the contract block; regenerate.
// Beta Distribution · beta distribution layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0572CrashMonitoring: AppComponent {
    public static let contract = ComponentContract(
        id: 572,
        name: "Crash Monitoring",
        phase: 34,
        phaseName: "Beta Distribution",
        layer: "beta distribution",
        purpose: "Crash Monitoring: the beta distribution responsibility named by checklist component 572 (Beta Distribution).",
        inputs: ["Crash Monitoring configuration (typed, validated)", "ComponentContext"],
        outputs: ["Crash Monitoring state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "TestFlight governance, cohorts, diagnostics, feedback, acceptance criteria",
        budgets: [QualityBudget(metric: "TestFlight governance", unit: "count", limit: 100.0), QualityBudget(metric: "cohorts", unit: "count", limit: 250.0), QualityBudget(metric: "diagnostics", unit: "count", limit: 250.0), QualityBudget(metric: "feedback", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Crash Monitoring must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Crash Monitoring a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Crash Monitoring; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Crash Monitoring during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Crash Monitoring is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
