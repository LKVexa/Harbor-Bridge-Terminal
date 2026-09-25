// Generated from checklist component 56 — do not hand-edit the contract block; regenerate.
// User Interface Platform · user-interface platform layer · control family: visualStates

import Foundation
import ComponentKit

public struct C0056DynamicTypeSupport: AppComponent {
    public static let contract = ComponentContract(
        id: 56,
        name: "Dynamic Type Support",
        phase: 3,
        phaseName: "User Interface Platform",
        layer: "user-interface platform",
        purpose: "Dynamic Type Support: the user-interface platform responsibility named by checklist component 56 (User Interface Platform).",
        inputs: ["Dynamic Type Support configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Dynamic Type Support state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "SwiftUI/UIKit composition, navigation, layout, rendering, adaptive presentation",
        budgets: [QualityBudget(metric: "SwiftUI/UIKit composition", unit: "count", limit: 100.0), QualityBudget(metric: "navigation", unit: "count", limit: 250.0), QualityBudget(metric: "layout", unit: "count", limit: 250.0), QualityBudget(metric: "rendering", unit: "p95 ms", limit: 250.0)],
        family: .visualStates,
        userVisible: true,
        donors: [DonorPart(car: "swift-issues", part: "Issue tracker content", license: "NONE (no licence file at HEAD)", mode: .patternOnly), DonorPart(car: "swiftui", part: "Working tree holds only .git; contents unread", license: "NONE (no licence file at HEAD)", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .visualStates, clauses: [
        FamilyClause(control: 21, statement: "Define visual states for Dynamic Type Support across loading, empty, success, disabled, selected, error, offline, and restricted conditions.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Validate Dynamic Type Support across supported iPhone/iPad size classes, orientations, safe areas, Dynamic Type sizes, and appearance modes.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Expose correct accessibility semantics, focus order, actions, labels, values, and traits for every interactive Dynamic Type Support state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Measure rendering/update cost for Dynamic Type Support and eliminate unnecessary body recomputation, layout churn, and main-thread blocking.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add snapshot or visual-regression coverage for stable Dynamic Type Support states without coupling tests to incidental implementation details.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
