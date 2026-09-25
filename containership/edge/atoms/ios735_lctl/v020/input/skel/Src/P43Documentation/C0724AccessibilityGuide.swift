// Generated from checklist component 724 — do not hand-edit the contract block; regenerate.
// Documentation · documentation layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0724AccessibilityGuide: AppComponent {
    public static let contract = ComponentContract(
        id: 724,
        name: "Accessibility Guide",
        phase: 43,
        phaseName: "Documentation",
        layer: "documentation",
        purpose: "Accessibility Guide: the documentation responsibility named by checklist component 724 (Documentation).",
        inputs: ["Accessibility Guide configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Accessibility Guide state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authoritative technical records, ownership, change control, diagrams, operational usability",
        budgets: [QualityBudget(metric: "authoritative technical records", unit: "count", limit: 100.0), QualityBudget(metric: "ownership", unit: "count", limit: 250.0), QualityBudget(metric: "change control", unit: "count", limit: 250.0), QualityBudget(metric: "diagrams", unit: "count", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: [DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency), DonorPart(car: "swift-snippets", part: "DocC snippet tooling", license: "MIT", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Accessibility Guide with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Accessibility Guide at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Accessibility Guide does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Accessibility Guide with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
