// Generated from checklist component 723 — do not hand-edit the contract block; regenerate.
// Documentation · documentation layer · control family: visualStates

import Foundation
import ComponentKit

public struct C0723DesignSystemGuide: AppComponent {
    public static let contract = ComponentContract(
        id: 723,
        name: "Design-System Guide",
        phase: 43,
        phaseName: "Documentation",
        layer: "documentation",
        purpose: "Design-System Guide: the documentation responsibility named by checklist component 723 (Documentation).",
        inputs: ["Design-System Guide configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Design-System Guide state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["SwiftUI"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authoritative technical records, ownership, change control, diagrams, operational usability",
        budgets: [QualityBudget(metric: "authoritative technical records", unit: "count", limit: 100.0), QualityBudget(metric: "ownership", unit: "count", limit: 250.0), QualityBudget(metric: "change control", unit: "count", limit: 250.0), QualityBudget(metric: "diagrams", unit: "count", limit: 250.0)],
        family: .visualStates,
        userVisible: true,
        donors: [DonorPart(car: "swift-system", part: "Typed file-system/syscall wrappers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swiftui", part: "Working tree holds only .git; contents unread", license: "NONE (no licence file at HEAD)", mode: .patternOnly), DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .visualStates, clauses: [
        FamilyClause(control: 21, statement: "Define visual states for Design-System Guide across loading, empty, success, disabled, selected, error, offline, and restricted conditions.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Validate Design-System Guide across supported iPhone/iPad size classes, orientations, safe areas, Dynamic Type sizes, and appearance modes.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Expose correct accessibility semantics, focus order, actions, labels, values, and traits for every interactive Design-System Guide state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Measure rendering/update cost for Design-System Guide and eliminate unnecessary body recomputation, layout churn, and main-thread blocking.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add snapshot or visual-regression coverage for stable Design-System Guide states without coupling tests to incidental implementation details.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
