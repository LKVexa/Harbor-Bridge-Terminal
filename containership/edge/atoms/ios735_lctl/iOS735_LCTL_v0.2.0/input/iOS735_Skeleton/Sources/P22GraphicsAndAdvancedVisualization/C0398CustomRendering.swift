// Generated from checklist component 398 — do not hand-edit the contract block; regenerate.
// Graphics and Advanced Visualization · graphics/visualization layer · control family: renderBudget

import Foundation
import ComponentKit

public struct C0398CustomRendering: AppComponent {
    public static let contract = ComponentContract(
        id: 398,
        name: "Custom Rendering",
        phase: 22,
        phaseName: "Graphics and Advanced Visualization",
        layer: "graphics/visualization",
        purpose: "Custom Rendering: the graphics/visualization responsibility named by checklist component 398 (Graphics and Advanced Visualization).",
        inputs: ["Custom Rendering configuration (typed, validated)", "ComponentContext"],
        outputs: ["Custom Rendering state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Metal", "MetalKit", "RealityKit", "Charts"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "GPU/render pipeline, frame pacing, assets, shader correctness, resource lifetime",
        budgets: [QualityBudget(metric: "GPU/render pipeline", unit: "p95 ms", limit: 100.0), QualityBudget(metric: "frame pacing", unit: "p95 ms", limit: 250.0), QualityBudget(metric: "assets", unit: "count", limit: 250.0), QualityBudget(metric: "shader correctness", unit: "count", limit: 250.0)],
        family: .renderBudget,
        userVisible: false,
        donors: [DonorPart(car: "swift-numerics", part: "Real/Complex numerics", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "SwiftUsd-Tests", part: "OpenUSD Swift interop tests", license: "unknown (unverified)", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .renderBudget, clauses: [
        FamilyClause(control: 21, statement: "Define frame-time, memory, resolution, precision, and visual-correctness budgets specifically for Custom Rendering.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Validate resource lifetime for Custom Rendering so textures, buffers, command resources, display links, and observers are deterministically released.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Profile Custom Rendering on lower-tier supported devices for GPU stalls, overdraw, shader compilation, bandwidth pressure, and thermal throttling.", evidence: .deviceRun),
        FamilyClause(control: 24, statement: "Test Custom Rendering during rotation, resizing, background/foreground transitions, memory pressure, and device capability fallback.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Provide deterministic reference scenes/data for visual and numerical regression testing of Custom Rendering.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
