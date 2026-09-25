// Generated from checklist component 59 — do not hand-edit the contract block; regenerate.
// User Interface Platform · user-interface platform layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0059ReducedMotionSupport: AppComponent {
    public static let contract = ComponentContract(
        id: 59,
        name: "Reduced Motion Support",
        phase: 3,
        phaseName: "User Interface Platform",
        layer: "user-interface platform",
        purpose: "Reduced Motion Support: the user-interface platform responsibility named by checklist component 59 (User Interface Platform).",
        inputs: ["Reduced Motion Support configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Reduced Motion Support state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request motion only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CoreMotion"],
        capabilities: [.motion],
        platform: PlatformSupport(requiresHardware: [.motion], fallback: "hide the feature and explain why when motion is unavailable"),
        budgetDomain: "SwiftUI/UIKit composition, navigation, layout, rendering, adaptive presentation",
        budgets: [QualityBudget(metric: "SwiftUI/UIKit composition", unit: "count", limit: 100.0), QualityBudget(metric: "navigation", unit: "count", limit: 250.0), QualityBudget(metric: "layout", unit: "count", limit: 250.0), QualityBudget(metric: "rendering", unit: "p95 ms", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: [DonorPart(car: "swift-issues", part: "Issue tracker content", license: "NONE (no licence file at HEAD)", mode: .patternOnly), DonorPart(car: "swiftui", part: "Working tree holds only .git; contents unread", license: "NONE (no licence file at HEAD)", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Reduced Motion Support with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Reduced Motion Support at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Reduced Motion Support does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Reduced Motion Support with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
