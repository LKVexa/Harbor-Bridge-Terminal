// Generated from checklist component 671 — do not hand-edit the contract block; regenerate.
// Reliability Engineering · reliability engineering layer · control family: dataModel

import Foundation
import ComponentKit

public struct C0671SafeDatabaseMigration: AppComponent {
    public static let contract = ComponentContract(
        id: 671,
        name: "Safe Database Migration",
        phase: 40,
        phaseName: "Reliability Engineering",
        layer: "reliability engineering",
        purpose: "Safe Database Migration: the reliability engineering responsibility named by checklist component 671 (Reliability Engineering).",
        inputs: ["Safe Database Migration configuration (typed, validated)", "ComponentContext"],
        outputs: ["Safe Database Migration state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["SwiftData", "CoreData"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "SLOs, recovery, integrity, rollback, diagnostics, post-incident learning",
        budgets: [QualityBudget(metric: "SLOs", unit: "count", limit: 100.0), QualityBudget(metric: "recovery", unit: "count", limit: 250.0), QualityBudget(metric: "integrity", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .dataModel,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .dataModel, clauses: [
        FamilyClause(control: 21, statement: "Define ownership, lifecycle, schema, cardinality, invariants, and persistence guarantees for Safe Database Migration.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Specify migration strategy for Safe Database Migration, including rollback/forward-only constraints and recovery from interrupted migration.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Test Safe Database Migration with corrupted, truncated, stale, oversized, duplicated, conflicting, and partially migrated data.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Document concurrency rules for Safe Database Migration so reads/writes never violate actor, context, transaction, or isolation requirements.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Measure storage growth, I/O latency, cache hit rate, migration duration, and memory amplification attributable to Safe Database Migration.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
