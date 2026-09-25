// Generated from checklist component 88 — do not hand-edit the contract block; regenerate.
// Accessibility · accessibility layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0088SwitchControlSupport: AppComponent {
    public static let contract = ComponentContract(
        id: 88,
        name: "Switch Control Support",
        phase: 5,
        phaseName: "Accessibility",
        layer: "accessibility",
        purpose: "Switch Control Support: the accessibility responsibility named by checklist component 88 (Accessibility).",
        inputs: ["Switch Control Support configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Switch Control Support state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "assistive technologies, semantic exposure, scalable content, inclusive interaction",
        budgets: [QualityBudget(metric: "assistive technologies", unit: "count", limit: 100.0), QualityBudget(metric: "semantic exposure", unit: "count", limit: 250.0), QualityBudget(metric: "scalable content", unit: "count", limit: 250.0), QualityBudget(metric: "inclusive interaction", unit: "count", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: [DonorPart(car: "swift-issues", part: "Issue tracker content", license: "NONE (no licence file at HEAD)", mode: .patternOnly), DonorPart(car: "swift-distributed-tracing-extras", part: "Tracing semantic conventions", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Switch Control Support with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Switch Control Support at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Switch Control Support does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Switch Control Support with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
