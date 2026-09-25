// Generated from checklist component 17 — do not hand-edit the contract block; regenerate.
// Software Architecture · software architecture layer · control family: mlModel

import Foundation
import ComponentKit

public struct C0017ViewModelLayer: AppComponent {
    public static let contract = ComponentContract(
        id: 17,
        name: "View Model Layer",
        phase: 2,
        phaseName: "Software Architecture",
        layer: "software architecture",
        purpose: "View Model Layer: the software architecture responsibility named by checklist component 17 (Software Architecture).",
        inputs: ["View Model Layer configuration (typed, validated)", "ComponentContext"],
        outputs: ["View Model Layer state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["SwiftUI", "CoreML", "Vision", "NaturalLanguage"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "module contracts, dependency direction, state ownership, testable boundaries",
        budgets: [QualityBudget(metric: "module contracts", unit: "count", limit: 100.0), QualityBudget(metric: "dependency direction", unit: "count", limit: 250.0), QualityBudget(metric: "state ownership", unit: "count", limit: 250.0), QualityBudget(metric: "testable boundaries", unit: "count", limit: 250.0)],
        family: .mlModel,
        userVisible: false,
        donors: [DonorPart(car: "swift-numerics", part: "Real/Complex numerics", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swiftui", part: "Working tree holds only .git; contents unread", license: "NONE (no licence file at HEAD)", mode: .patternOnly), DonorPart(car: "swift-openapi-runtime", part: "OpenAPI runtime types and middleware", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mlModel, clauses: [
        FamilyClause(control: 21, statement: "Define model/input/output contracts for View Model Layer, including tensor/feature shapes, normalization, confidence semantics, and unsupported inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Benchmark View Model Layer across representative devices for latency, peak memory, sustained thermal behavior, energy, and accelerator utilization.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Version model artifacts independently and ensure View Model Layer can reject incompatible, corrupted, unsigned, or partially downloaded models.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Evaluate View Model Layer on domain-representative validation sets and record failure modes, confidence calibration, and regression thresholds.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Apply privacy and safety controls so View Model Layer minimizes retained inputs/outputs and handles unsafe or invalid results predictably.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
