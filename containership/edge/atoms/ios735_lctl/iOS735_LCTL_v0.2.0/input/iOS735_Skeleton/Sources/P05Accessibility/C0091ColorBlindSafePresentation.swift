// Generated from checklist component 91 — do not hand-edit the contract block; regenerate.
// Accessibility · accessibility layer · control family: visualStates

import Foundation
import ComponentKit

public struct C0091ColorBlindSafePresentation: AppComponent {
    public static let contract = ComponentContract(
        id: 91,
        name: "Color-Blind-Safe Presentation",
        phase: 5,
        phaseName: "Accessibility",
        layer: "accessibility",
        purpose: "Color-Blind-Safe Presentation: the accessibility responsibility named by checklist component 91 (Accessibility).",
        inputs: ["Color-Blind-Safe Presentation configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Color-Blind-Safe Presentation state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["SwiftUI"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "assistive technologies, semantic exposure, scalable content, inclusive interaction",
        budgets: [QualityBudget(metric: "assistive technologies", unit: "count", limit: 100.0), QualityBudget(metric: "semantic exposure", unit: "count", limit: 250.0), QualityBudget(metric: "scalable content", unit: "count", limit: 250.0), QualityBudget(metric: "inclusive interaction", unit: "count", limit: 250.0)],
        family: .visualStates,
        userVisible: true,
        donors: [DonorPart(car: "swift-distributed-tracing-extras", part: "Tracing semantic conventions", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .visualStates, clauses: [
        FamilyClause(control: 21, statement: "Define visual states for Color-Blind-Safe Presentation across loading, empty, success, disabled, selected, error, offline, and restricted conditions.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Validate Color-Blind-Safe Presentation across supported iPhone/iPad size classes, orientations, safe areas, Dynamic Type sizes, and appearance modes.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Expose correct accessibility semantics, focus order, actions, labels, values, and traits for every interactive Color-Blind-Safe Presentation state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Measure rendering/update cost for Color-Blind-Safe Presentation and eliminate unnecessary body recomputation, layout churn, and main-thread blocking.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add snapshot or visual-regression coverage for stable Color-Blind-Safe Presentation states without coupling tests to incidental implementation details.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
