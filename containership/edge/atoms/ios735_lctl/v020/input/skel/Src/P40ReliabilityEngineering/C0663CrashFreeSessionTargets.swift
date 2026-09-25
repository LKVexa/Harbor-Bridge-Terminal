// Generated from checklist component 663 — do not hand-edit the contract block; regenerate.
// Reliability Engineering · reliability engineering layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0663CrashFreeSessionTargets: AppComponent {
    public static let contract = ComponentContract(
        id: 663,
        name: "Crash-Free Session Targets",
        phase: 40,
        phaseName: "Reliability Engineering",
        layer: "reliability engineering",
        purpose: "Crash-Free Session Targets: the reliability engineering responsibility named by checklist component 663 (Reliability Engineering).",
        inputs: ["Crash-Free Session Targets configuration (typed, validated)", "ComponentContext"],
        outputs: ["Crash-Free Session Targets state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "SLOs, recovery, integrity, rollback, diagnostics, post-incident learning",
        budgets: [QualityBudget(metric: "SLOs", unit: "count", limit: 100.0), QualityBudget(metric: "recovery", unit: "count", limit: 250.0), QualityBudget(metric: "integrity", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Crash-Free Session Targets must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Crash-Free Session Targets a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Crash-Free Session Targets; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Crash-Free Session Targets during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Crash-Free Session Targets is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
