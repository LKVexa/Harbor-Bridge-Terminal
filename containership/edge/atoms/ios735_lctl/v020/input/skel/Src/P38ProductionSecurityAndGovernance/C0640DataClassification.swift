// Generated from checklist component 640 — do not hand-edit the contract block; regenerate.
// Production Security and Governance · security/governance layer · control family: mlModel

import Foundation
import ComponentKit

public struct C0640DataClassification: AppComponent {
    public static let contract = ComponentContract(
        id: 640,
        name: "Data Classification",
        phase: 38,
        phaseName: "Production Security and Governance",
        layer: "security/governance",
        purpose: "Data Classification: the security/governance responsibility named by checklist component 640 (Production Security and Governance).",
        inputs: ["Data Classification configuration (typed, validated)", "ComponentContext"],
        outputs: ["Data Classification state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CoreML", "Vision", "NaturalLanguage"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "secure SDLC, supply chain, access control, incident response, compliance evidence",
        budgets: [QualityBudget(metric: "secure SDLC", unit: "count", limit: 100.0), QualityBudget(metric: "supply chain", unit: "count", limit: 250.0), QualityBudget(metric: "access control", unit: "count", limit: 250.0), QualityBudget(metric: "incident response", unit: "count", limit: 250.0)],
        family: .mlModel,
        userVisible: false,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-http-types", part: "Currency HTTP request/response types", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mlModel, clauses: [
        FamilyClause(control: 21, statement: "Define model/input/output contracts for Data Classification, including tensor/feature shapes, normalization, confidence semantics, and unsupported inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Benchmark Data Classification across representative devices for latency, peak memory, sustained thermal behavior, energy, and accelerator utilization.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Version model artifacts independently and ensure Data Classification can reject incompatible, corrupted, unsigned, or partially downloaded models.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Evaluate Data Classification on domain-representative validation sets and record failure modes, confidence calibration, and regression thresholds.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Apply privacy and safety controls so Data Classification minimizes retained inputs/outputs and handles unsafe or invalid results predictably.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
