// Generated from checklist component 382 — do not hand-edit the contract block; regenerate.
// AI, ML and Intelligent Processing · AI/ML layer · control family: mlModel

import Foundation
import ComponentKit

public struct C0382OCRTextRecognition: AppComponent {
    public static let contract = ComponentContract(
        id: 382,
        name: "OCR / Text Recognition",
        phase: 21,
        phaseName: "AI, ML and Intelligent Processing",
        layer: "AI/ML",
        purpose: "OCR / Text Recognition: the AI/ML responsibility named by checklist component 382 (AI, ML and Intelligent Processing).",
        inputs: ["OCR / Text Recognition configuration (typed, validated)", "ComponentContext"],
        outputs: ["OCR / Text Recognition state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "model lifecycle, inference correctness, memory/compute budgets, privacy, safety validation",
        budgets: [QualityBudget(metric: "model lifecycle", unit: "count", limit: 100.0), QualityBudget(metric: "inference correctness", unit: "count", limit: 250.0), QualityBudget(metric: "memory/compute budgets", unit: "count", limit: 250.0), QualityBudget(metric: "privacy", unit: "count", limit: 250.0)],
        family: .mlModel,
        userVisible: false,
        donors: [DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency), DonorPart(car: "swift-string-processing-benchmarks", part: "Regex/string benchmarks", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mlModel, clauses: [
        FamilyClause(control: 21, statement: "Define model/input/output contracts for OCR / Text Recognition, including tensor/feature shapes, normalization, confidence semantics, and unsupported inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Benchmark OCR / Text Recognition across representative devices for latency, peak memory, sustained thermal behavior, energy, and accelerator utilization.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Version model artifacts independently and ensure OCR / Text Recognition can reject incompatible, corrupted, unsigned, or partially downloaded models.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Evaluate OCR / Text Recognition on domain-representative validation sets and record failure modes, confidence calibration, and regression thresholds.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Apply privacy and safety controls so OCR / Text Recognition minimizes retained inputs/outputs and handles unsafe or invalid results predictably.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
