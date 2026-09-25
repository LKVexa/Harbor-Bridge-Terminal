// Generated from checklist component 702 — do not hand-edit the contract block; regenerate.
// Professional Design System · design system layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0702MotionTokens: AppComponent {
    public static let contract = ComponentContract(
        id: 702,
        name: "Motion Tokens",
        phase: 42,
        phaseName: "Professional Design System",
        layer: "design system",
        purpose: "Motion Tokens: the design system responsibility named by checklist component 702 (Professional Design System).",
        inputs: ["Motion Tokens configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Motion Tokens state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request motion only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CoreMotion"],
        capabilities: [.motion],
        platform: PlatformSupport(requiresHardware: [.motion], fallback: "hide the feature and explain why when motion is unavailable"),
        budgetDomain: "tokens, reusable components, variants, accessibility, consistency, documentation",
        budgets: [QualityBudget(metric: "tokens", unit: "count", limit: 100.0), QualityBudget(metric: "reusable components", unit: "count", limit: 250.0), QualityBudget(metric: "variants", unit: "count", limit: 250.0), QualityBudget(metric: "accessibility", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: true,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Motion Tokens, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Motion Tokens secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Motion Tokens: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Motion Tokens inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Motion Tokens fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
