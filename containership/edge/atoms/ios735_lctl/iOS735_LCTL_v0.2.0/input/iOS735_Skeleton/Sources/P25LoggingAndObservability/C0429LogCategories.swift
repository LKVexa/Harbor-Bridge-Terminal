// Generated from checklist component 429 — do not hand-edit the contract block; regenerate.
// Logging and Observability · observability layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0429LogCategories: AppComponent {
    public static let contract = ComponentContract(
        id: 429,
        name: "Log Categories",
        phase: 25,
        phaseName: "Logging and Observability",
        layer: "observability",
        purpose: "Log Categories: the observability responsibility named by checklist component 429 (Logging and Observability).",
        inputs: ["Log Categories configuration (typed, validated)", "ComponentContext"],
        outputs: ["Log Categories state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "structured telemetry, privacy-safe diagnostics, metrics, traces, crash evidence",
        budgets: [QualityBudget(metric: "structured telemetry", unit: "count", limit: 100.0), QualityBudget(metric: "privacy-safe diagnostics", unit: "count", limit: 250.0), QualityBudget(metric: "metrics", unit: "count", limit: 250.0), QualityBudget(metric: "traces", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Log Categories must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Log Categories a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Log Categories; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Log Categories during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Log Categories is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
