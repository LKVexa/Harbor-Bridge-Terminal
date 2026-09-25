// Generated from checklist component 396 — do not hand-edit the contract block; regenerate.
// Graphics and Advanced Visualization · graphics/visualization layer · control family: renderBudget

import Foundation
import ComponentKit

public struct C03963DAssetPipeline: AppComponent {
    public static let contract = ComponentContract(
        id: 396,
        name: "3D Asset Pipeline",
        phase: 22,
        phaseName: "Graphics and Advanced Visualization",
        layer: "graphics/visualization",
        purpose: "3D Asset Pipeline: the graphics/visualization responsibility named by checklist component 396 (Graphics and Advanced Visualization).",
        inputs: ["3D Asset Pipeline configuration (typed, validated)", "ComponentContext"],
        outputs: ["3D Asset Pipeline state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Metal", "MetalKit", "RealityKit", "Charts"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "GPU/render pipeline, frame pacing, assets, shader correctness, resource lifetime",
        budgets: [QualityBudget(metric: "GPU/render pipeline", unit: "p95 ms", limit: 100.0), QualityBudget(metric: "frame pacing", unit: "p95 ms", limit: 250.0), QualityBudget(metric: "assets", unit: "count", limit: 250.0), QualityBudget(metric: "shader correctness", unit: "count", limit: 250.0)],
        family: .renderBudget,
        userVisible: false,
        donors: [DonorPart(car: "SwiftUsd-Tests", part: "OpenUSD Swift interop tests", license: "unknown (unverified)", mode: .patternOnly), DonorPart(car: "SwiftUsd-ast-answerer", part: "OpenUSD Swift interop analysis", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-numerics", part: "Real/Complex numerics", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .renderBudget, clauses: [
        FamilyClause(control: 21, statement: "Define frame-time, memory, resolution, precision, and visual-correctness budgets specifically for 3D Asset Pipeline.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Validate resource lifetime for 3D Asset Pipeline so textures, buffers, command resources, display links, and observers are deterministically released.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Profile 3D Asset Pipeline on lower-tier supported devices for GPU stalls, overdraw, shader compilation, bandwidth pressure, and thermal throttling.", evidence: .deviceRun),
        FamilyClause(control: 24, statement: "Test 3D Asset Pipeline during rotation, resizing, background/foreground transitions, memory pressure, and device capability fallback.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Provide deterministic reference scenes/data for visual and numerical regression testing of 3D Asset Pipeline.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
