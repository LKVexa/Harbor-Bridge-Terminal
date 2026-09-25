// Generated from checklist component 384 — do not hand-edit the contract block; regenerate.
// AI, ML and Intelligent Processing · AI/ML layer · control family: mlModel

import Foundation
import ComponentKit

public struct C0384SpeechRecognition: AppComponent {
    public static let contract = ComponentContract(
        id: 384,
        name: "Speech Recognition",
        phase: 21,
        phaseName: "AI, ML and Intelligent Processing",
        layer: "AI/ML",
        purpose: "Speech Recognition: the AI/ML responsibility named by checklist component 384 (AI, ML and Intelligent Processing).",
        inputs: ["Speech Recognition configuration (typed, validated)", "ComponentContext"],
        outputs: ["Speech Recognition state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request microphone only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CoreML", "Vision", "NaturalLanguage"],
        capabilities: [.microphone],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "model lifecycle, inference correctness, memory/compute budgets, privacy, safety validation",
        budgets: [QualityBudget(metric: "model lifecycle", unit: "count", limit: 100.0), QualityBudget(metric: "inference correctness", unit: "count", limit: 250.0), QualityBudget(metric: "memory/compute budgets", unit: "count", limit: 250.0), QualityBudget(metric: "privacy", unit: "count", limit: 250.0)],
        family: .mlModel,
        userVisible: false,
        donors: [DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-numerics", part: "Real/Complex numerics", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-binary-parsing", part: "Safe binary parsing", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mlModel, clauses: [
        FamilyClause(control: 21, statement: "Define model/input/output contracts for Speech Recognition, including tensor/feature shapes, normalization, confidence semantics, and unsupported inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Benchmark Speech Recognition across representative devices for latency, peak memory, sustained thermal behavior, energy, and accelerator utilization.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Version model artifacts independently and ensure Speech Recognition can reject incompatible, corrupted, unsigned, or partially downloaded models.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Evaluate Speech Recognition on domain-representative validation sets and record failure modes, confidence calibration, and regression thresholds.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Apply privacy and safety controls so Speech Recognition minimizes retained inputs/outputs and handles unsafe or invalid results predictably.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
