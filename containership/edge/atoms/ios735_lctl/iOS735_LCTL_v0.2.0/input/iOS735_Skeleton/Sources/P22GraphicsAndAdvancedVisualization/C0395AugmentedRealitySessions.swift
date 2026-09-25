// Generated from checklist component 395 — do not hand-edit the contract block; regenerate.
// Graphics and Advanced Visualization · graphics/visualization layer · control family: general

import Foundation
import ComponentKit

public struct C0395AugmentedRealitySessions: AppComponent {
    public static let contract = ComponentContract(
        id: 395,
        name: "Augmented Reality Sessions",
        phase: 22,
        phaseName: "Graphics and Advanced Visualization",
        layer: "graphics/visualization",
        purpose: "Augmented Reality Sessions: the graphics/visualization responsibility named by checklist component 395 (Graphics and Advanced Visualization).",
        inputs: ["Augmented Reality Sessions configuration (typed, validated)", "ComponentContext"],
        outputs: ["Augmented Reality Sessions state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Metal", "MetalKit", "RealityKit", "Charts"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "GPU/render pipeline, frame pacing, assets, shader correctness, resource lifetime",
        budgets: [QualityBudget(metric: "GPU/render pipeline", unit: "p95 ms", limit: 100.0), QualityBudget(metric: "frame pacing", unit: "p95 ms", limit: 250.0), QualityBudget(metric: "assets", unit: "count", limit: 250.0), QualityBudget(metric: "shader correctness", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "SwiftUsd-ast-answerer", part: "OpenUSD Swift interop analysis", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-numerics", part: "Real/Complex numerics", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Augmented Reality Sessions, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Augmented Reality Sessions.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Augmented Reality Sessions, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Augmented Reality Sessions.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Augmented Reality Sessions while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
