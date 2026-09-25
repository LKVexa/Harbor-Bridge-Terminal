// Generated from checklist component 318 — do not hand-edit the contract block; regenerate.
// Location and Mapping · location/mapping layer · control family: locationAuthorization

import Foundation
import ComponentKit

public struct C0318Directions: AppComponent {
    public static let contract = ComponentContract(
        id: 318,
        name: "Directions",
        phase: 17,
        phaseName: "Location and Mapping",
        layer: "location/mapping",
        purpose: "Directions: the location/mapping responsibility named by checklist component 318 (Location and Mapping).",
        inputs: ["Directions configuration (typed, validated)", "ComponentContext"],
        outputs: ["Directions state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authorization, precision, background policy, geospatial correctness, map performance",
        budgets: [QualityBudget(metric: "authorization", unit: "count", limit: 100.0), QualityBudget(metric: "precision", unit: "count", limit: 250.0), QualityBudget(metric: "background policy", unit: "count", limit: 250.0), QualityBudget(metric: "geospatial correctness", unit: "count", limit: 250.0)],
        family: .locationAuthorization,
        userVisible: false,
        donors: [DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-collections-benchmark", part: "Collection benchmark harness", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .locationAuthorization, clauses: [
        FamilyClause(control: 21, statement: "Define authorization and accuracy requirements for Directions, including reduced-accuracy and permission-denied behavior.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Minimize collection by configuring only the update frequency, precision, region monitoring, and background access Directions truly needs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Test Directions with stale coordinates, tunnel/urban-canyon conditions, simulated routes, denied services, and authorization changes.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Treat all external/geocoded content used by Directions as untrusted input and validate before navigation or persistence.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Measure location energy impact and stop updates promptly when Directions no longer requires them.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
