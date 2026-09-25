// Generated from checklist component 703 — do not hand-edit the contract block; regenerate.
// Professional Design System · design system layer · control family: renderBudget

import Foundation
import ComponentKit

public struct C0703AnimationCurves: AppComponent {
    public static let contract = ComponentContract(
        id: 703,
        name: "Animation Curves",
        phase: 42,
        phaseName: "Professional Design System",
        layer: "design system",
        purpose: "Animation Curves: the design system responsibility named by checklist component 703 (Professional Design System).",
        inputs: ["Animation Curves configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Animation Curves state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "tokens, reusable components, variants, accessibility, consistency, documentation",
        budgets: [QualityBudget(metric: "tokens", unit: "count", limit: 100.0), QualityBudget(metric: "reusable components", unit: "count", limit: 250.0), QualityBudget(metric: "variants", unit: "count", limit: 250.0), QualityBudget(metric: "accessibility", unit: "count", limit: 250.0)],
        family: .renderBudget,
        userVisible: true,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .renderBudget, clauses: [
        FamilyClause(control: 21, statement: "Define frame-time, memory, resolution, precision, and visual-correctness budgets specifically for Animation Curves.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Validate resource lifetime for Animation Curves so textures, buffers, command resources, display links, and observers are deterministically released.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Profile Animation Curves on lower-tier supported devices for GPU stalls, overdraw, shader compilation, bandwidth pressure, and thermal throttling.", evidence: .deviceRun),
        FamilyClause(control: 24, statement: "Test Animation Curves during rotation, resizing, background/foreground transitions, memory pressure, and device capability fallback.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Provide deterministic reference scenes/data for visual and numerical regression testing of Animation Curves.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
