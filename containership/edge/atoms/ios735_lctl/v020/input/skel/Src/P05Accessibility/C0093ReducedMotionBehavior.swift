// Generated from checklist component 93 — do not hand-edit the contract block; regenerate.
// Accessibility · accessibility layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0093ReducedMotionBehavior: AppComponent {
    public static let contract = ComponentContract(
        id: 93,
        name: "Reduced Motion Behavior",
        phase: 5,
        phaseName: "Accessibility",
        layer: "accessibility",
        purpose: "Reduced Motion Behavior: the accessibility responsibility named by checklist component 93 (Accessibility).",
        inputs: ["Reduced Motion Behavior configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Reduced Motion Behavior state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request motion only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CoreMotion"],
        capabilities: [.motion],
        platform: PlatformSupport(requiresHardware: [.motion], fallback: "hide the feature and explain why when motion is unavailable"),
        budgetDomain: "assistive technologies, semantic exposure, scalable content, inclusive interaction",
        budgets: [QualityBudget(metric: "assistive technologies", unit: "count", limit: 100.0), QualityBudget(metric: "semantic exposure", unit: "count", limit: 250.0), QualityBudget(metric: "scalable content", unit: "count", limit: 250.0), QualityBudget(metric: "inclusive interaction", unit: "count", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: [DonorPart(car: "swift-distributed-tracing-extras", part: "Tracing semantic conventions", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Reduced Motion Behavior with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Reduced Motion Behavior at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Reduced Motion Behavior does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Reduced Motion Behavior with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
