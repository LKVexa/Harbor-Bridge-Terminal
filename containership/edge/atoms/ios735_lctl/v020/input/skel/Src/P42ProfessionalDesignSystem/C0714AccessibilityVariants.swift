// Generated from checklist component 714 — do not hand-edit the contract block; regenerate.
// Professional Design System · design system layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0714AccessibilityVariants: AppComponent {
    public static let contract = ComponentContract(
        id: 714,
        name: "Accessibility Variants",
        phase: 42,
        phaseName: "Professional Design System",
        layer: "design system",
        purpose: "Accessibility Variants: the design system responsibility named by checklist component 714 (Professional Design System).",
        inputs: ["Accessibility Variants configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Accessibility Variants state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "tokens, reusable components, variants, accessibility, consistency, documentation",
        budgets: [QualityBudget(metric: "tokens", unit: "count", limit: 100.0), QualityBudget(metric: "reusable components", unit: "count", limit: 250.0), QualityBudget(metric: "variants", unit: "count", limit: 250.0), QualityBudget(metric: "accessibility", unit: "count", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Accessibility Variants with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Accessibility Variants at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Accessibility Variants does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Accessibility Variants with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
