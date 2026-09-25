// Generated from checklist component 561 — do not hand-edit the contract block; regenerate.
// CI/CD · CI/CD layer · control family: testOwnership

import Foundation
import ComponentKit

public struct C0561TestFlightDeployment: AppComponent {
    public static let contract = ComponentContract(
        id: 561,
        name: "TestFlight Deployment",
        phase: 33,
        phaseName: "CI/CD",
        layer: "CI/CD",
        purpose: "TestFlight Deployment: the CI/CD responsibility named by checklist component 561 (CI/CD).",
        inputs: ["TestFlight Deployment configuration (typed, validated)", "ComponentContext"],
        outputs: ["TestFlight Deployment state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "pipeline integrity, automated evidence, signing/release automation, rollback, auditability",
        budgets: [QualityBudget(metric: "pipeline integrity", unit: "count", limit: 100.0), QualityBudget(metric: "automated evidence", unit: "count", limit: 250.0), QualityBudget(metric: "signing/release automation", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .testOwnership,
        userVisible: false,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-argument-parser", part: "CLI argument parsing (build tooling only)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .testOwnership, clauses: [
        FamilyClause(control: 21, statement: "Define what failures TestFlight Deployment must detect, the ownership of those tests, and the CI stage in which they execute.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Ensure TestFlight Deployment is deterministic: control time, randomness, locale, network, filesystem, user defaults, keychain, and concurrency inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Design TestFlight Deployment to produce actionable failure diagnostics without leaking secrets or depending on developer-machine state.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Track flaky behavior for TestFlight Deployment as a defect; quarantine may isolate impact but must not become permanent suppression.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Require representative positive, negative, boundary, concurrency, and regression cases before TestFlight Deployment is considered complete.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
