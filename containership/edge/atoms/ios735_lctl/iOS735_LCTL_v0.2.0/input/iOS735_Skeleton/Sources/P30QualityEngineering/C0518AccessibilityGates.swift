// Generated from checklist component 518 — do not hand-edit the contract block; regenerate.
// Quality Engineering · quality engineering layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0518AccessibilityGates: AppComponent {
    public static let contract = ComponentContract(
        id: 518,
        name: "Accessibility Gates",
        phase: 30,
        phaseName: "Quality Engineering",
        layer: "quality engineering",
        purpose: "Accessibility Gates: the quality engineering responsibility named by checklist component 518 (Quality Engineering).",
        inputs: ["Accessibility Gates configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Accessibility Gates state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "static gates, policy enforcement, dependency hygiene, regression prevention",
        budgets: [QualityBudget(metric: "static gates", unit: "count", limit: 100.0), QualityBudget(metric: "policy enforcement", unit: "count", limit: 250.0), QualityBudget(metric: "dependency hygiene", unit: "count", limit: 250.0), QualityBudget(metric: "regression prevention", unit: "count", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: [DonorPart(car: "swift-collections-benchmark", part: "Collection benchmark harness", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swiftpm-on-llbuild2", part: "SwiftPM on llbuild2", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Accessibility Gates with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Accessibility Gates at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Accessibility Gates does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Accessibility Gates with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
