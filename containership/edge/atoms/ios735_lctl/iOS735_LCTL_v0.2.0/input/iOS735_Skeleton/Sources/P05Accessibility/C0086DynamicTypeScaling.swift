// Generated from checklist component 86 — do not hand-edit the contract block; regenerate.
// Accessibility · accessibility layer · control family: visualStates

import Foundation
import ComponentKit

public struct C0086DynamicTypeScaling: AppComponent {
    public static let contract = ComponentContract(
        id: 86,
        name: "Dynamic Type Scaling",
        phase: 5,
        phaseName: "Accessibility",
        layer: "accessibility",
        purpose: "Dynamic Type Scaling: the accessibility responsibility named by checklist component 86 (Accessibility).",
        inputs: ["Dynamic Type Scaling configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Dynamic Type Scaling state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "assistive technologies, semantic exposure, scalable content, inclusive interaction",
        budgets: [QualityBudget(metric: "assistive technologies", unit: "count", limit: 100.0), QualityBudget(metric: "semantic exposure", unit: "count", limit: 250.0), QualityBudget(metric: "scalable content", unit: "count", limit: 250.0), QualityBudget(metric: "inclusive interaction", unit: "count", limit: 250.0)],
        family: .visualStates,
        userVisible: true,
        donors: [DonorPart(car: "swift-distributed-tracing-extras", part: "Tracing semantic conventions", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .visualStates, clauses: [
        FamilyClause(control: 21, statement: "Define visual states for Dynamic Type Scaling across loading, empty, success, disabled, selected, error, offline, and restricted conditions.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Validate Dynamic Type Scaling across supported iPhone/iPad size classes, orientations, safe areas, Dynamic Type sizes, and appearance modes.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Expose correct accessibility semantics, focus order, actions, labels, values, and traits for every interactive Dynamic Type Scaling state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Measure rendering/update cost for Dynamic Type Scaling and eliminate unnecessary body recomputation, layout churn, and main-thread blocking.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add snapshot or visual-regression coverage for stable Dynamic Type Scaling states without coupling tests to incidental implementation details.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
