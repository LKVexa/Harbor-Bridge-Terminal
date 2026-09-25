// Generated from checklist component 678 — do not hand-edit the contract block; regenerate.
// User Experience Infrastructure · UX infrastructure layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0678AuthenticationUX: AppComponent {
    public static let contract = ComponentContract(
        id: 678,
        name: "Authentication UX",
        phase: 41,
        phaseName: "User Experience Infrastructure",
        layer: "UX infrastructure",
        purpose: "Authentication UX: the UX infrastructure responsibility named by checklist component 678 (User Experience Infrastructure).",
        inputs: ["Authentication UX configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Authentication UX state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Security", "LocalAuthentication", "AuthenticationServices"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "state clarity, onboarding, recoverability, settings, user control, interaction quality",
        budgets: [QualityBudget(metric: "state clarity", unit: "count", limit: 100.0), QualityBudget(metric: "onboarding", unit: "count", limit: 250.0), QualityBudget(metric: "recoverability", unit: "count", limit: 250.0), QualityBudget(metric: "settings", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: true,
        donors: [DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Authentication UX, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Authentication UX secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Authentication UX: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Authentication UX inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Authentication UX fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
