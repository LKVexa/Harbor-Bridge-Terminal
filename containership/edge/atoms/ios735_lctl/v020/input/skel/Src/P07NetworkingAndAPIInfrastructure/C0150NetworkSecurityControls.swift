// Generated from checklist component 150 — do not hand-edit the contract block; regenerate.
// Networking and API Infrastructure · networking/API layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0150NetworkSecurityControls: AppComponent {
    public static let contract = ComponentContract(
        id: 150,
        name: "Network Security Controls",
        phase: 7,
        phaseName: "Networking and API Infrastructure",
        layer: "networking/API",
        purpose: "Network Security Controls: the networking/API responsibility named by checklist component 150 (Networking and API Infrastructure).",
        inputs: ["Network Security Controls configuration (typed, validated)", "ComponentContext", "network responses"],
        outputs: ["Network Security Controls state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request network only after in-context justification", "network I/O"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation.URLSession", "Network"],
        capabilities: [.network],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "transport correctness, request lifecycle, protocol contracts, resilience, security",
        budgets: [QualityBudget(metric: "transport correctness", unit: "count", limit: 100.0), QualityBudget(metric: "request lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "protocol contracts", unit: "count", limit: 250.0), QualityBudget(metric: "resilience", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-nio-transport-services", part: "NIO on Network.framework (iOS-capable)", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-network-evolution", part: "Networking evolution proposals", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Network Security Controls, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Network Security Controls secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Network Security Controls: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Network Security Controls inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Network Security Controls fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
