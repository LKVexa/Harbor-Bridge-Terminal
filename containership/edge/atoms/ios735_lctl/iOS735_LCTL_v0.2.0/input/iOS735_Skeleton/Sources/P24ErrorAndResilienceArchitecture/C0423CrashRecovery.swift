// Generated from checklist component 423 — do not hand-edit the contract block; regenerate.
// Error and Resilience Architecture · resilience layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0423CrashRecovery: AppComponent {
    public static let contract = ComponentContract(
        id: 423,
        name: "Crash Recovery",
        phase: 24,
        phaseName: "Error and Resilience Architecture",
        layer: "resilience",
        purpose: "Crash Recovery: the resilience responsibility named by checklist component 423 (Error and Resilience Architecture).",
        inputs: ["Crash Recovery configuration (typed, validated)", "ComponentContext"],
        outputs: ["Crash Recovery state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "error taxonomy, recovery paths, fallbacks, corruption handling, user-safe degradation",
        budgets: [QualityBudget(metric: "error taxonomy", unit: "count", limit: 100.0), QualityBudget(metric: "recovery paths", unit: "count", limit: 250.0), QualityBudget(metric: "fallbacks", unit: "count", limit: 250.0), QualityBudget(metric: "corruption handling", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Crash Recovery must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Crash Recovery a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Crash Recovery; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Crash Recovery during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Crash Recovery is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
