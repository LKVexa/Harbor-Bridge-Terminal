// Generated from checklist component 308 — do not hand-edit the contract block; regenerate.
// Location and Mapping · location/mapping layer · control family: backgroundMode

import Foundation
import ComponentKit

public struct C0308BackgroundLocationWhereJustified: AppComponent {
    public static let contract = ComponentContract(
        id: 308,
        name: "Background Location, where justified",
        phase: 17,
        phaseName: "Location and Mapping",
        layer: "location/mapping",
        purpose: "Background Location, where justified: the location/mapping responsibility named by checklist component 308 (Location and Mapping).",
        inputs: ["Background Location, where justified configuration (typed, validated)", "ComponentContext"],
        outputs: ["Background Location, where justified state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request location only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["BackgroundTasks", "CoreLocation", "MapKit"],
        capabilities: [.location],
        platform: PlatformSupport(requiresHardware: [.gps], fallback: "hide the feature and explain why when gps is unavailable"),
        budgetDomain: "authorization, precision, background policy, geospatial correctness, map performance",
        budgets: [QualityBudget(metric: "authorization", unit: "count", limit: 100.0), QualityBudget(metric: "precision", unit: "count", limit: 250.0), QualityBudget(metric: "background policy", unit: "count", limit: 250.0), QualityBudget(metric: "geospatial correctness", unit: "count", limit: 250.0)],
        family: .backgroundMode,
        userVisible: false,
        donors: [DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-collections-benchmark", part: "Collection benchmark harness", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .backgroundMode, clauses: [
        FamilyClause(control: 21, statement: "Map Background Location, where justified to Apple-supported background execution modes and document why each entitlement/capability is required.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Persist enough state for Background Location, where justified to resume idempotently after suspension, termination, reboot, expiration, or duplicate scheduling.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Implement expiration/cancellation handling for Background Location, where justified and prove all resources, files, transactions, and tasks are safely finalized.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Measure energy, radio, CPU, memory, and wall-clock cost of Background Location, where justified under realistic background scheduling conditions.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Test Background Location, where justified when execution is delayed or denied; user-visible correctness must not depend on guaranteed background runtime.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
