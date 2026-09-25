# vm_xtra_large -- sort ledger

Berth `vm_xtra_large` (vm), UC-2.1.3. Source: `Xtra_Large.zip` (zip, cea7cb3704c24e89cc95470b721faaf38aa54ac597530a50e5a9ee0700e8d4ca). 5513 scripts sorted by policy 1.0.1 (rules S0-S9, first match wins; see `reports/SORT_POLICY.md`).

| node | scripts | bytes | rules | kinds |
|---|---:|---:|---|---|
| `N_SMALL` (DF_Small) | 3794 | 5576699 | S6:2740, S7:22, S8:1032 | json:2611, markdown:540, text:486, mssl_doc:104, log:25, batch:11, shell:11, grammar:6 |
| `N_MEDIUM` (DF_Medium) | 1418 | 12805475 | S5:652, S6:585, S8:181 | json:623, mssl_doc:334, markdown:261, text:116, sums:78, csv:3, key:2, grammar:1 |
| `N_LARGE` (DF_Large) | 3 | 533608 | S4:1, S6:2 | json:2, make:1 |
| `N_XLARGE` (DF_Xtra_Large) | 298 | 1612821 | S0:138, S2:4, S3:156 | lctlc10:138, lctl:133, python:23, image:3, jar:1 |

| script | node | rule | kind | bytes | lines | band | why |
|---|---|---|---|---:|---:|---|---|
| `APPLIED_26_GATE_REMEDIATION_AUDIT.json` | `N_SMALL` | S6 | json | 1995 | 48 | LOW | json of 1995 bytes (<= 4 KiB) |
| `APPLIED_315_PARTIAL_REMEDIATION_AUDIT.json` | `N_SMALL` | S6 | json | 4026 | 101 | MID | json of 4026 bytes (<= 4 KiB) |
| `ARCHITECTURE.md` | `N_SMALL` | S8 | markdown | 2937 | 31 | MID | markdown of 2937 bytes (<= 8 KiB): teaching-sized |
| `ARCHITECTURE_2.0.0.md` | `N_SMALL` | S8 | markdown | 339 | 3 | LOW | markdown of 339 bytes (<= 8 KiB): teaching-sized |
| `AUDIT_ERRATA.md` | `N_SMALL` | S8 | markdown | 3693 | 51 | MID | markdown of 3693 bytes (<= 8 KiB): teaching-sized |
| `CAPABILITY_MODEL.md` | `N_SMALL` | S8 | markdown | 246 | 3 | LOW | markdown of 246 bytes (<= 8 KiB): teaching-sized |
| `CLAIM_BOUNDARY.md` | `N_SMALL` | S8 | markdown | 1112 | 12 | LOW | markdown of 1112 bytes (<= 8 KiB): teaching-sized |
| `DEEP_COMPUTATIONAL_MODEL.md` | `N_SMALL` | S8 | markdown | 461 | 3 | LOW | markdown of 461 bytes (<= 8 KiB): teaching-sized |
| `EVIDENCE_MODEL.md` | `N_SMALL` | S8 | markdown | 225 | 3 | LOW | markdown of 225 bytes (<= 8 KiB): teaching-sized |
| `GRAPH_MODEL.md` | `N_SMALL` | S8 | markdown | 241 | 3 | LOW | markdown of 241 bytes (<= 8 KiB): teaching-sized |
| `MANIFEST.json` | `N_MEDIUM` | S5 | json | 4984 | 127 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `MIGRATION_MAP.md` | `N_MEDIUM` | S8 | markdown | 14648 | 72 | LOW | markdown of 14648 bytes (<= 128 KiB) |
| `MIGRATION_MAP_2.0.0.md` | `N_SMALL` | S8 | markdown | 276 | 3 | LOW | markdown of 276 bytes (<= 8 KiB): teaching-sized |
| `OPTIMIZATION_MODEL.md` | `N_SMALL` | S8 | markdown | 257 | 3 | LOW | markdown of 257 bytes (<= 8 KiB): teaching-sized |
| `QUALIFICATION_MODEL.md` | `N_SMALL` | S8 | markdown | 1407 | 14 | LOW | markdown of 1407 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_810_ITEM_APPLICATION_REPORT.md` | `N_SMALL` | S8 | markdown | 1021 | 30 | LOW | markdown of 1021 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_RCPW_7_26_BLOCKER_REMEDIATION_REPORT.md` | `N_SMALL` | S8 | markdown | 2030 | 31 | MID | markdown of 2030 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_RCPW_7_315_PARTIAL_REMEDIATION_REPORT.md` | `N_SMALL` | S8 | markdown | 1821 | 32 | LOW | markdown of 1821 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_RCPW_7_APPLICATION_CHANGELOG.md` | `N_SMALL` | S8 | markdown | 1535 | 24 | LOW | markdown of 1535 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_RCPW_7_APPLICATION_REPORT.md` | `N_SMALL` | S8 | markdown | 6251 | 63 | MID | markdown of 6251 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_RCPW_7_APPLICATION_REPORT_PRE_26_REMEDIATION.md` | `N_SMALL` | S8 | markdown | 2600 | 52 | LOW | markdown of 2600 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_REIMAGINATION_REPORT.md` | `N_SMALL` | S8 | markdown | 1548 | 24 | LOW | markdown of 1548 bytes (<= 8 KiB): teaching-sized |
| `QUORUM_VM_APPLICATION_CHANGELOG.md` | `N_SMALL` | S8 | markdown | 599 | 5 | LOW | markdown of 599 bytes (<= 8 KiB): teaching-sized |
| `README_START_HERE.md` | `N_SMALL` | S8 | markdown | 3884 | 40 | MID | markdown of 3884 bytes (<= 8 KiB): teaching-sized |
| `REPLAY_MODEL.md` | `N_SMALL` | S8 | markdown | 167 | 3 | LOW | markdown of 167 bytes (<= 8 KiB): teaching-sized |
| `SECURITY_MODEL.md` | `N_SMALL` | S8 | markdown | 282 | 3 | LOW | markdown of 282 bytes (<= 8 KiB): teaching-sized |
| `SHA256SUMS.txt` | `N_MEDIUM` | S5 | sums | 777633 | 5512 | VERY_HIGH | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `SOURCE_AUTHORITY.md` | `N_MEDIUM` | S5 | markdown | 279 | 8 | LOW | markdown named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `authority/repository.mssl` | `N_SMALL` | S6 | mssl_doc | 2830 | 15 | LOW | mssl_doc of 2830 bytes (<= 4 KiB) |
| `authority/security.mssl` | `N_SMALL` | S6 | mssl_doc | 1672 | 15 | LOW | mssl_doc of 1672 bytes (<= 4 KiB) |
| `evidence/LCTL_VERIFICATION_LEDGER.json` | `N_MEDIUM` | S5 | json | 85417 | 1073 | HIGH | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/LEGACY_IMMUTABILITY_2.0.1.json` | `N_SMALL` | S6 | json | 199 | 6 | LOW | json of 199 bytes (<= 4 KiB) |
| `evidence/LEGACY_IMMUTABILITY_LEDGER.json` | `N_MEDIUM` | S5 | json | 109 | 6 | LOW | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `evidence/verify_batch_000_034.json` | `N_MEDIUM` | S6 | json | 20646 | 274 | MID | json of 20646 bytes (<= 256 KiB) |
| `evidence/verify_batch_034_068.json` | `N_MEDIUM` | S6 | json | 21073 | 274 | MID | json of 21073 bytes (<= 256 KiB) |
| `evidence/verify_batch_068_102.json` | `N_MEDIUM` | S6 | json | 21562 | 274 | MID | json of 21562 bytes (<= 256 KiB) |
| `evidence/verify_batch_102_133.json` | `N_MEDIUM` | S6 | json | 19875 | 250 | MID | json of 19875 bytes (<= 256 KiB) |
| `execution/repository_fanout.lctl` | `N_XLARGE` | S3 | lctl | 6722 | 39 | LOW | a Columned LCTL plan; the QUORUM node hosts the LCTL 1.6.1-RC1 column verifier (JVM) that lowers and verifies plans |
| `execution/repository_fanout.lctlc` | `N_XLARGE` | S0 | lctlc10 | 3506 | 32 | LOW | LCTLC/1.0 is the QUORUM VM profile |
| `legacy/source_repository/ALL_SUITES_REPOSITORY_66_MODULES.md` | `N_SMALL` | S8 | markdown | 8033 | 544 | HIGH | markdown of 8033 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/ALL_SubSuite_Language_Assignment.md` | `N_MEDIUM` | S8 | markdown | 46734 | 1532 | HIGH | markdown of 46734 bytes (<= 128 KiB) |
| `legacy/source_repository/Action Cards/49.10_Action_Cards_Expected_Effects.jaui` | `N_SMALL` | S8 | text | 2091 | 47 | MID | text of 2091 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.11_Action_Cards_Impact.jaui` | `N_SMALL` | S8 | text | 2046 | 47 | MID | text of 2046 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.12_Action_Cards_Rollback.jaui` | `N_SMALL` | S8 | text | 2102 | 47 | MID | text of 2102 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.13_Action_Cards_Unified_Diff.jaui` | `N_SMALL` | S8 | text | 2023 | 47 | MID | text of 2023 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.14_Action_Cards_Review_History.jaui` | `N_SMALL` | S8 | text | 2075 | 47 | MID | text of 2075 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.1_Action_Cards_Risk_Summary.jaui` | `N_SMALL` | S8 | text | 1931 | 47 | MID | text of 1931 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.2_Action_Cards_Evidence_Summary.jaui` | `N_SMALL` | S8 | text | 2075 | 47 | MID | text of 2075 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.3_Action_Cards_Parameter_Summary.jaui` | `N_SMALL` | S8 | text | 2126 | 47 | MID | text of 2126 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.4_Action_Cards_Impact_Summary.jaui` | `N_SMALL` | S8 | text | 2017 | 47 | MID | text of 2017 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.5_Action_Cards_Rollback_Summary.jaui` | `N_SMALL` | S8 | text | 2093 | 47 | MID | text of 2093 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.6_Action_Cards_Hash_Summary.jaui` | `N_SMALL` | S8 | text | 1976 | 47 | MID | text of 1976 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.7_Action_Cards_Capability_Contract.jaui` | `N_SMALL` | S8 | text | 2173 | 47 | MID | text of 2173 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.8_Action_Cards_Parameters.jaui` | `N_SMALL` | S8 | text | 2155 | 47 | MID | text of 2155 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/49.9_Action_Cards_Preconditions.jaui` | `N_SMALL` | S8 | text | 2194 | 47 | MID | text of 2194 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Action Cards/README.md` | `N_MEDIUM` | S8 | markdown | 20023 | 305 | HIGH | markdown of 20023 bytes (<= 128 KiB) |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.10_Air_Gap_Certification_and_Installer_Plane_Installer.jaops` | `N_SMALL` | S8 | text | 1086 | 31 | LOW | text of 1086 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.11_Air_Gap_Certification_and_Installer_Plane_License_System.jaops` | `N_SMALL` | S8 | text | 1103 | 31 | LOW | text of 1103 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.1_Air_Gap_Certification_and_Installer_Plane_Offline_Runtime_Policy.jaops` | `N_SMALL` | S8 | text | 1174 | 31 | LOW | text of 1174 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.2_Air_Gap_Certification_and_Installer_Plane_Certification_Records.jaops` | `N_SMALL` | S8 | text | 1196 | 31 | LOW | text of 1196 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.3_Air_Gap_Certification_and_Installer_Plane_One_Click_Setup_Transaction.jaops` | `N_SMALL` | S8 | text | 1147 | 31 | LOW | text of 1147 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.4_Air_Gap_Certification_and_Installer_Plane_Licensing.jaops` | `N_SMALL` | S8 | text | 1063 | 31 | LOW | text of 1063 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.5_Air_Gap_Certification_and_Installer_Plane_Installer_Integration.jaops` | `N_SMALL` | S8 | text | 1173 | 31 | LOW | text of 1173 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.6_Air_Gap_Certification_and_Installer_Plane_Air_Gap_Runtime.jaops` | `N_SMALL` | S8 | text | 1094 | 31 | LOW | text of 1094 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.7_Air_Gap_Certification_and_Installer_Plane_Certification_Fabric.jaops` | `N_SMALL` | S8 | text | 1120 | 31 | LOW | text of 1120 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.8_Air_Gap_Certification_and_Installer_Plane_One_Click_Setup.jaops` | `N_SMALL` | S8 | text | 1087 | 31 | LOW | text of 1087 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/46.9_Air_Gap_Certification_and_Installer_Plane_Multilingual_Setup.jaops` | `N_SMALL` | S8 | text | 1095 | 31 | LOW | text of 1095 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Air Gap Certification and Installer Plane/README.md` | `N_MEDIUM` | S8 | markdown | 20887 | 258 | HIGH | markdown of 20887 bytes (<= 128 KiB) |
| `legacy/source_repository/Animation VFX Workspace/34.1_Animation_VFX_Workspace_Animation.deepml` | `N_SMALL` | S8 | text | 1503 | 25 | LOW | text of 1503 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Animation VFX Workspace/34.2_Animation_VFX_Workspace_Effects.deepml` | `N_SMALL` | S8 | text | 1522 | 27 | LOW | text of 1522 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Animation VFX Workspace/34.3_Animation_VFX_Workspace_Compositing.deepml` | `N_SMALL` | S8 | text | 1487 | 25 | LOW | text of 1487 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Animation VFX Workspace/34.4_Animation_VFX_Workspace_Inspection.deepml` | `N_SMALL` | S8 | text | 1508 | 25 | LOW | text of 1508 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Animation VFX Workspace/34.5_Animation_VFX_Workspace_Iteration.deepml` | `N_SMALL` | S8 | text | 1577 | 26 | LOW | text of 1577 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Animation VFX Workspace/README.md` | `N_MEDIUM` | S8 | markdown | 13775 | 200 | MID | markdown of 13775 bytes (<= 128 KiB) |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.10_Specialized_Roles_Technical_Coordinator.jaa` | `N_SMALL` | S8 | text | 1679 | 35 | LOW | text of 1679 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.11_Specialized_Roles_Repository_Analyst.jaa` | `N_SMALL` | S8 | text | 1667 | 35 | LOW | text of 1667 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.12_Specialized_Roles_Software_Engineer.jaa` | `N_SMALL` | S8 | text | 1633 | 35 | LOW | text of 1633 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.13_Specialized_Roles_Debugger.jaa` | `N_SMALL` | S8 | text | 1634 | 35 | LOW | text of 1634 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.14_Specialized_Roles_Software_Architect.jaa` | `N_SMALL` | S8 | text | 1743 | 35 | LOW | text of 1743 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.15_Specialized_Roles_Security_Reviewer.jaa` | `N_SMALL` | S8 | text | 1654 | 35 | LOW | text of 1654 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.16_Specialized_Roles_Test_Engineer.jaa` | `N_SMALL` | S8 | text | 1562 | 35 | LOW | text of 1562 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.17_Specialized_Roles_Code_Reviewer.jaa` | `N_SMALL` | S8 | text | 1604 | 35 | LOW | text of 1604 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.18_Specialized_Roles_Operations_Engineer.jaa` | `N_SMALL` | S8 | text | 1670 | 35 | LOW | text of 1670 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.19_Specialized_Roles_Release_Engineer.jaa` | `N_MEDIUM` | S5 | text | 1623 | 35 | LOW | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.1_Answer_Modes_Auto.jaa` | `N_SMALL` | S8 | text | 1537 | 35 | LOW | text of 1537 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.20_Specialized_Roles_Roles.jaa` | `N_SMALL` | S8 | text | 1583 | 35 | LOW | text of 1583 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.21_Specialized_Roles_Documentation_Instructor.jaa` | `N_SMALL` | S8 | text | 1734 | 35 | LOW | text of 1734 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.22_Specialized_Roles_AI_and_Model_Engineer.jaa` | `N_SMALL` | S8 | text | 1686 | 35 | LOW | text of 1686 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.23_Specialized_Roles_Language_Toolchain_Engineer.jaa` | `N_SMALL` | S8 | text | 1753 | 35 | LOW | text of 1753 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.2_Answer_Modes_Concise.jaa` | `N_SMALL` | S8 | text | 1599 | 35 | LOW | text of 1599 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.3_Answer_Modes_Detailed.jaa` | `N_SMALL` | S8 | text | 1636 | 35 | LOW | text of 1636 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.4_Answer_Modes_Tutorial.jaa` | `N_SMALL` | S8 | text | 1550 | 35 | LOW | text of 1550 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.5_Answer_Modes_Code.jaa` | `N_SMALL` | S8 | text | 1514 | 35 | LOW | text of 1514 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.6_Answer_Modes_Debug.jaa` | `N_SMALL` | S8 | text | 1568 | 35 | LOW | text of 1568 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.7_Answer_Modes_Architect.jaa` | `N_SMALL` | S8 | text | 1661 | 35 | LOW | text of 1661 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.8_Answer_Modes_Review.jaa` | `N_SMALL` | S8 | text | 1606 | 35 | LOW | text of 1606 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/48.9_Specialized_Roles_Auto_Coordinator.jaa` | `N_SMALL` | S8 | text | 1557 | 35 | LOW | text of 1557 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Answer Modes and Specialized Roles/README.md` | `N_MEDIUM` | S8 | markdown | 23359 | 378 | HIGH | markdown of 23359 bytes (<= 128 KiB) |
| `legacy/source_repository/Anthology/02_anthology_chronology.jad` | `N_SMALL` | S8 | text | 2424 | 61 | MID | text of 2424 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/02_anthology_immutable_provenance.jad` | `N_MEDIUM` | S5 | text | 2564 | 63 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Anthology/02_anthology_ordered_experience_records.jad` | `N_SMALL` | S8 | text | 2626 | 64 | MID | text of 2626 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/02_anthology_prior_artifacts.jad` | `N_SMALL` | S8 | text | 2639 | 64 | MID | text of 2639 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/MANIFEST.json` | `N_MEDIUM` | S5 | json | 3390 | 101 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Anthology/README.md` | `N_SMALL` | S8 | markdown | 2400 | 58 | MID | markdown of 2400 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/SHA256SUMS.txt` | `N_MEDIUM` | S5 | sums | 1132 | 11 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Anthology/chronology_records.dmk` | `N_SMALL` | S8 | text | 2726 | 69 | MID | text of 2726 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/experience_records.dmk` | `N_SMALL` | S8 | text | 2832 | 72 | MID | text of 2832 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/prior_artifact_records.dmk` | `N_SMALL` | S8 | text | 2847 | 72 | MID | text of 2847 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Anthology/provenance_records.dmk` | `N_MEDIUM` | S5 | text | 2789 | 71 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/App Designer/35.1_App_Designer_Composition.jaui` | `N_SMALL` | S8 | text | 1922 | 47 | LOW | text of 1922 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/App Designer/35.2_App_Designer_Layout.jaui` | `N_SMALL` | S8 | text | 1824 | 47 | LOW | text of 1824 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/App Designer/35.3_App_Designer_Interaction_Design.jaui` | `N_SMALL` | S8 | text | 1967 | 47 | LOW | text of 1967 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/App Designer/35.4_App_Designer_Preview.jaui` | `N_SMALL` | S8 | text | 1849 | 47 | LOW | text of 1849 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/App Designer/35.5_App_Designer_Handoff.jaui` | `N_SMALL` | S8 | text | 1879 | 47 | LOW | text of 1879 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/App Designer/README.md` | `N_MEDIUM` | S8 | markdown | 15106 | 208 | MID | markdown of 15106 bytes (<= 128 KiB) |
| `legacy/source_repository/Archive Ledger/29.1_Archive_Ledger_Feature_Graphs.jad` | `N_MEDIUM` | S5 | text | 2463 | 61 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/29.2_Archive_Ledger_Motion_Plans.jad` | `N_MEDIUM` | S5 | text | 2541 | 62 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/29.3_Archive_Ledger_Training_Ledgers.jad` | `N_MEDIUM` | S5 | text | 2522 | 62 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/29.4_Archive_Ledger_Manifests.jad` | `N_MEDIUM` | S5 | text | 2567 | 64 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/29.5_Archive_Ledger_Provenance.jad` | `N_MEDIUM` | S5 | text | 2498 | 63 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/29.6_Archive_Ledger_Hashes.jad` | `N_MEDIUM` | S5 | text | 2414 | 61 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/README.md` | `N_MEDIUM` | S8 | markdown | 12034 | 168 | MID | markdown of 12034 bytes (<= 128 KiB) |
| `legacy/source_repository/Archive Ledger/archive_ledger_feature_graphs.dmk` | `N_MEDIUM` | S5 | text | 2767 | 72 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/archive_ledger_hashes.dmk` | `N_MEDIUM` | S5 | text | 2723 | 72 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/archive_ledger_manifests.dmk` | `N_MEDIUM` | S5 | text | 2826 | 75 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/archive_ledger_motion_plans.dmk` | `N_MEDIUM` | S5 | text | 2803 | 73 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/archive_ledger_provenance.dmk` | `N_MEDIUM` | S5 | text | 2787 | 74 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Archive Ledger/archive_ledger_training_runs.dmk` | `N_MEDIUM` | S5 | text | 2795 | 73 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Asset Observer/17.1_Asset_Observer_Images.deepml` | `N_SMALL` | S8 | text | 1314 | 38 | LOW | text of 1314 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Asset Observer/17.2_Asset_Observer_Video.deepml` | `N_SMALL` | S8 | text | 1386 | 38 | LOW | text of 1386 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Asset Observer/17.3_Asset_Observer_Archives.deepml` | `N_SMALL` | S8 | text | 1263 | 38 | LOW | text of 1263 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Asset Observer/17.4_Asset_Observer_UI_Assets.deepml` | `N_SMALL` | S8 | text | 1287 | 38 | LOW | text of 1287 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Asset Observer/17.5_Asset_Observer_Code.deepml` | `N_SMALL` | S8 | text | 1250 | 38 | LOW | text of 1250 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Asset Observer/17.6_Asset_Observer_Metadata.deepml` | `N_SMALL` | S8 | text | 1255 | 38 | LOW | text of 1255 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Asset Observer/README.md` | `N_MEDIUM` | S8 | markdown | 9899 | 173 | MID | markdown of 9899 bytes (<= 128 KiB) |
| `legacy/source_repository/Atlas/03_atlas_coordinates.jad` | `N_SMALL` | S8 | text | 2684 | 69 | MID | text of 2684 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/03_atlas_domains.jad` | `N_SMALL` | S8 | text | 2540 | 65 | MID | text of 2540 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/03_atlas_entities.jad` | `N_SMALL` | S8 | text | 2504 | 65 | MID | text of 2504 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/03_atlas_feature_spaces.jad` | `N_SMALL` | S8 | text | 2712 | 68 | MID | text of 2712 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/03_atlas_files.jad` | `N_SMALL` | S8 | text | 2546 | 67 | MID | text of 2546 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/03_atlas_project_structure.jad` | `N_SMALL` | S8 | text | 2668 | 67 | MID | text of 2668 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/MANIFEST.json` | `N_MEDIUM` | S5 | json | 4901 | 147 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Atlas/README.md` | `N_SMALL` | S8 | markdown | 2436 | 58 | MID | markdown of 2436 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/SHA256SUMS.txt` | `N_MEDIUM` | S5 | sums | 1473 | 15 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Atlas/coordinate_records.dmk` | `N_SMALL` | S8 | text | 2879 | 77 | MID | text of 2879 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/domain_records.dmk` | `N_SMALL` | S8 | text | 2779 | 73 | MID | text of 2779 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/entity_records.dmk` | `N_SMALL` | S8 | text | 2761 | 73 | MID | text of 2761 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/feature_space_records.dmk` | `N_SMALL` | S8 | text | 2889 | 76 | MID | text of 2889 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/file_records.dmk` | `N_SMALL` | S8 | text | 2791 | 75 | MID | text of 2791 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Atlas/project_structure_records.dmk` | `N_SMALL` | S8 | text | 2866 | 75 | MID | text of 2866 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/C# Renderer/24.1_CSharp_Renderer_Native_CSharp_Layer.deepml` | `N_SMALL` | S8 | text | 1361 | 25 | LOW | text of 1361 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/C# Renderer/24.2_CSharp_Renderer_Scene_Rendering.deepml` | `N_SMALL` | S8 | text | 1448 | 27 | LOW | text of 1448 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/C# Renderer/24.3_CSharp_Renderer_Frame_State_Rendering.deepml` | `N_SMALL` | S8 | text | 1454 | 25 | LOW | text of 1454 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/C# Renderer/README.md` | `N_MEDIUM` | S8 | markdown | 10904 | 162 | MID | markdown of 10904 bytes (<= 128 KiB) |
| `legacy/source_repository/CROSS_REFERENCE_DIAGNOSTIC.md` | `N_SMALL` | S8 | markdown | 4805 | 53 | LOW | markdown of 4805 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability Manifests and Permissions/55.1_Capabilities.jasec` | `N_SMALL` | S8 | text | 915 | 27 | LOW | text of 915 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability Manifests and Permissions/55.2_Command_Permissions.jasec` | `N_SMALL` | S8 | text | 933 | 27 | LOW | text of 933 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability Manifests and Permissions/55.3_Action_Scope.jasec` | `N_SMALL` | S8 | text | 879 | 27 | LOW | text of 879 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability Manifests and Permissions/55.4_Policy_Bound_Execution_Rights.jasec` | `N_SMALL` | S8 | text | 944 | 27 | LOW | text of 944 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability Manifests and Permissions/README.md` | `N_MEDIUM` | S8 | markdown | 15558 | 344 | HIGH | markdown of 15558 bytes (<= 128 KiB) |
| `legacy/source_repository/Capability and Security Plane/44.1_Capability_and_Security_Plane_Capability_Manifests.jasec` | `N_MEDIUM` | S5 | text | 901 | 27 | LOW | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Capability and Security Plane/44.2_Capability_and_Security_Plane_Permissions.jasec` | `N_SMALL` | S8 | text | 854 | 27 | LOW | text of 854 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.3_Capability_and_Security_Plane_Trust_Boundaries.jasec` | `N_SMALL` | S8 | text | 881 | 27 | LOW | text of 881 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.4_Capability_and_Security_Plane_Approvals.jasec` | `N_SMALL` | S8 | text | 835 | 27 | LOW | text of 835 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.5_Capability_and_Security_Plane_Policy_Enforcement.jasec` | `N_SMALL` | S8 | text | 879 | 27 | LOW | text of 879 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.6_Capability_and_Security_Plane_Capability_Plane.jasec` | `N_SMALL` | S8 | text | 900 | 27 | LOW | text of 900 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.7_Capability_and_Security_Plane_Security.jasec` | `N_SMALL` | S8 | text | 842 | 27 | LOW | text of 842 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.8_Capability_and_Security_Plane_Trust_Plane.jasec` | `N_SMALL` | S8 | text | 857 | 27 | LOW | text of 857 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/44.9_Capability_and_Security_Plane_Evaluation_Suite.jasec` | `N_SMALL` | S8 | text | 913 | 27 | LOW | text of 913 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Capability and Security Plane/README.md` | `N_MEDIUM` | S8 | markdown | 13918 | 198 | MID | markdown of 13918 bytes (<= 128 KiB) |
| `legacy/source_repository/Chair/13_chair_authorization.jasec` | `N_SMALL` | S8 | text | 700 | 21 | LOW | text of 700 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chair/13_chair_deterministic_safety.jasec` | `N_SMALL` | S8 | text | 689 | 21 | LOW | text of 689 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chair/13_chair_no_autorun.jasec` | `N_SMALL` | S8 | text | 640 | 21 | LOW | text of 640 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chair/13_chair_policy_gates.jasec` | `N_SMALL` | S8 | text | 631 | 21 | LOW | text of 631 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chair/13_chair_validation.jasec` | `N_SMALL` | S8 | text | 659 | 21 | LOW | text of 659 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chair/README.md` | `N_SMALL` | S8 | markdown | 1891 | 29 | LOW | markdown of 1891 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/47.1_Chatbot_Explaining.jaa` | `N_SMALL` | S8 | text | 1621 | 35 | LOW | text of 1621 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/47.2_Chatbot_Planning.jaa` | `N_SMALL` | S8 | text | 1563 | 35 | LOW | text of 1563 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/47.3_Chatbot_Debugging.jaa` | `N_SMALL` | S8 | text | 1596 | 35 | LOW | text of 1596 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/47.4_Chatbot_Reviewing.jaa` | `N_SMALL` | S8 | text | 1605 | 35 | LOW | text of 1605 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/47.5_Chatbot_Refactoring.jaa` | `N_SMALL` | S8 | text | 1591 | 35 | LOW | text of 1591 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/47.6_Chatbot_Documenting_Projects.jaa` | `N_SMALL` | S8 | text | 1744 | 35 | LOW | text of 1744 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Chatbot/README.md` | `N_MEDIUM` | S8 | markdown | 13930 | 215 | MID | markdown of 13930 bytes (<= 128 KiB) |
| `legacy/source_repository/Compass/04_compass_direction.deepml` | `N_SMALL` | S8 | text | 2048 | 54 | LOW | text of 2048 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Compass/04_compass_feasibility_paths.deepml` | `N_SMALL` | S8 | text | 2421 | 64 | LOW | text of 2421 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Compass/04_compass_policies.deepml` | `N_SMALL` | S8 | text | 2487 | 59 | LOW | text of 2487 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Compass/04_compass_priorities.deepml` | `N_SMALL` | S8 | text | 2164 | 62 | LOW | text of 2164 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Compass/04_compass_routing_objectives.deepml` | `N_SMALL` | S8 | text | 2317 | 57 | LOW | text of 2317 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Compass/MANIFEST.json` | `N_MEDIUM` | S5 | json | 4329 | 127 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Compass/README.md` | `N_SMALL` | S8 | markdown | 2814 | 72 | LOW | markdown of 2814 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Compass/SHA256SUMS.txt` | `N_MEDIUM` | S5 | sums | 787 | 8 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Core Studio/39.10_Core_Studio_Integrated_Terminal.ja` | `N_SMALL` | S8 | text | 989 | 14 | LOW | text of 989 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.11_Core_Studio_Visual_App_Designer.ja` | `N_SMALL` | S8 | text | 969 | 14 | LOW | text of 969 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.12_Core_Studio_Model.ja` | `N_SMALL` | S8 | text | 851 | 14 | LOW | text of 851 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.13_Core_Studio_Resource_Dashboard.ja` | `N_SMALL` | S8 | text | 972 | 14 | LOW | text of 972 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.14_Core_Studio_Local_Server.ja` | `N_SMALL` | S8 | text | 932 | 14 | LOW | text of 932 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.1_Core_Studio_Files.ja` | `N_SMALL` | S8 | text | 837 | 14 | LOW | text of 837 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.2_Core_Studio_Editors.ja` | `N_SMALL` | S8 | text | 849 | 14 | LOW | text of 849 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.3_Core_Studio_Tabs.ja` | `N_SMALL` | S8 | text | 818 | 14 | LOW | text of 818 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.4_Core_Studio_Sessions.ja` | `N_SMALL` | S8 | text | 882 | 14 | LOW | text of 882 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.5_Core_Studio_Builds.ja` | `N_SMALL` | S8 | text | 846 | 14 | LOW | text of 846 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.6_Core_Studio_Tests.ja` | `N_SMALL` | S8 | text | 848 | 14 | LOW | text of 848 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.7_Core_Studio_Controlled_Integration.ja` | `N_SMALL` | S8 | text | 1027 | 14 | LOW | text of 1027 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.8_Core_Studio_Repository_UI.ja` | `N_SMALL` | S8 | text | 931 | 14 | LOW | text of 931 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/39.9_Core_Studio_Code_Editor.ja` | `N_SMALL` | S8 | text | 888 | 14 | LOW | text of 888 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Core Studio/README.md` | `N_MEDIUM` | S8 | markdown | 24734 | 361 | HIGH | markdown of 24734 bytes (<= 128 KiB) |
| `legacy/source_repository/Cypher/11_cypher_audit_provenance.jasec` | `N_MEDIUM` | S5 | text | 652 | 21 | LOW | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Cypher/11_cypher_fingerprints.jasec` | `N_SMALL` | S8 | text | 682 | 21 | LOW | text of 682 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Cypher/11_cypher_hashes.jasec` | `N_SMALL` | S8 | text | 627 | 21 | LOW | text of 627 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Cypher/11_cypher_signs.jasec` | `N_SMALL` | S8 | text | 622 | 21 | LOW | text of 622 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Cypher/11_cypher_verifies.jasec` | `N_SMALL` | S8 | text | 645 | 21 | LOW | text of 645 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Cypher/README.md` | `N_SMALL` | S8 | markdown | 1990 | 29 | LOW | markdown of 1990 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/50.1_Diff_Patch_and_Review_Bounded_Diff_Production.ja` | `N_SMALL` | S8 | text | 1458 | 14 | LOW | text of 1458 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/50.2_Diff_Patch_and_Review_Bounded_Patch_Construction.ja` | `N_SMALL` | S8 | text | 1496 | 14 | LOW | text of 1496 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/50.3_Diff_Patch_and_Review_Diff_Review.ja` | `N_SMALL` | S8 | text | 1480 | 14 | LOW | text of 1480 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/50.4_Diff_Patch_and_Review_Patch_Review.ja` | `N_SMALL` | S8 | text | 1484 | 14 | LOW | text of 1484 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/50.5_Diff_Patch_and_Review_Human_Approval.ja` | `N_SMALL` | S8 | text | 1539 | 14 | LOW | text of 1539 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/50.6_Diff_Patch_and_Review_Repository_Confinement.ja` | `N_SMALL` | S8 | text | 1669 | 14 | LOW | text of 1669 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Diff Patch and Review/README.md` | `N_MEDIUM` | S8 | markdown | 14945 | 226 | MID | markdown of 14945 bytes (<= 128 KiB) |
| `legacy/source_repository/Equation Operator Bank/20.1_Equation_Operator_Bank_Mathematical_Operators.dmk` | `N_SMALL` | S8 | text | 522 | 19 | LOW | text of 522 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Equation Operator Bank/20.2_Equation_Operator_Bank_MSSL_Operators.dmk` | `N_SMALL` | S8 | text | 498 | 19 | LOW | text of 498 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Equation Operator Bank/20.3_Equation_Operator_Bank_MSSLB_Operators.dmk` | `N_SMALL` | S8 | text | 501 | 19 | LOW | text of 501 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Equation Operator Bank/20.4_Equation_Operator_Bank_MCRT_Operators.dmk` | `N_SMALL` | S8 | text | 498 | 19 | LOW | text of 498 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Equation Operator Bank/20.5_Equation_Operator_Bank_Rendering_Operators.dmk` | `N_SMALL` | S8 | text | 515 | 19 | LOW | text of 515 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Equation Operator Bank/README.md` | `N_MEDIUM` | S8 | markdown | 10104 | 142 | MID | markdown of 10104 bytes (<= 128 KiB) |
| `legacy/source_repository/Evaluation and Content Defense/52.1_Evaluation_and_Content_Defense_Answer_Quality_Evaluation.jasec` | `N_SMALL` | S8 | text | 918 | 27 | LOW | text of 918 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/52.2_Evaluation_and_Content_Defense_Prompt_Injection_Evaluation.jasec` | `N_SMALL` | S8 | text | 935 | 27 | LOW | text of 935 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/52.3_Evaluation_and_Content_Defense_Malicious_Repository_Content_Evaluation.jasec` | `N_SMALL` | S8 | text | 976 | 27 | LOW | text of 976 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/52.4_Evaluation_and_Content_Defense_Fabricated_Evidence_Detection.jasec` | `N_SMALL` | S8 | text | 889 | 27 | LOW | text of 889 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/52.5_Evaluation_and_Content_Defense_Permanent_Evaluation.jasec` | `N_SMALL` | S8 | text | 913 | 27 | LOW | text of 913 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/52.6_Evaluation_and_Content_Defense_Prompt_Injection_Defense.jasec` | `N_SMALL` | S8 | text | 916 | 27 | LOW | text of 916 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/52.7_Evaluation_and_Content_Defense_Repository_Content_Defense.jasec` | `N_SMALL` | S8 | text | 944 | 27 | LOW | text of 944 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Evaluation and Content Defense/README.md` | `N_MEDIUM` | S8 | markdown | 17871 | 240 | HIGH | markdown of 17871 bytes (<= 128 KiB) |
| `legacy/source_repository/Feature Graph/18.1_Feature_Graph_Regions.jad` | `N_SMALL` | S8 | text | 2173 | 56 | MID | text of 2173 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/18.2_Feature_Graph_Contours.jad` | `N_SMALL` | S8 | text | 2282 | 57 | MID | text of 2282 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/18.3_Feature_Graph_Landmarks.jad` | `N_SMALL` | S8 | text | 2267 | 57 | MID | text of 2267 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/18.4_Feature_Graph_Layers.jad` | `N_SMALL` | S8 | text | 2263 | 58 | MID | text of 2263 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/18.5_Feature_Graph_Materials.jad` | `N_SMALL` | S8 | text | 2324 | 58 | MID | text of 2324 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/18.6_Feature_Graph_Relations.jad` | `N_SMALL` | S8 | text | 2298 | 58 | MID | text of 2298 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/README.md` | `N_MEDIUM` | S8 | markdown | 8385 | 140 | MID | markdown of 8385 bytes (<= 128 KiB) |
| `legacy/source_repository/Feature Graph/feature_graph_contours.dmk` | `N_SMALL` | S8 | text | 2638 | 68 | MID | text of 2638 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/feature_graph_landmarks.dmk` | `N_SMALL` | S8 | text | 2634 | 68 | MID | text of 2634 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/feature_graph_layers.dmk` | `N_SMALL` | S8 | text | 2628 | 69 | MID | text of 2628 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/feature_graph_materials.dmk` | `N_SMALL` | S8 | text | 2666 | 69 | MID | text of 2666 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/feature_graph_regions.dmk` | `N_SMALL` | S8 | text | 2582 | 67 | MID | text of 2582 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Feature Graph/feature_graph_relations.dmk` | `N_SMALL` | S8 | text | 2648 | 69 | MID | text of 2648 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/12_filing_cabinet_artifacts.jad` | `N_SMALL` | S8 | text | 2260 | 54 | MID | text of 2260 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/12_filing_cabinet_ledgers.jad` | `N_MEDIUM` | S5 | text | 2192 | 54 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Filing Cabinet/12_filing_cabinet_manifests.jad` | `N_MEDIUM` | S5 | text | 2181 | 54 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Filing Cabinet/12_filing_cabinet_models.jad` | `N_SMALL` | S8 | text | 2142 | 54 | MID | text of 2142 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/12_filing_cabinet_retrieval_pointers.jad` | `N_SMALL` | S8 | text | 2260 | 54 | MID | text of 2260 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/12_filing_cabinet_rollback_records.jad` | `N_SMALL` | S8 | text | 2268 | 55 | MID | text of 2268 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/README.md` | `N_SMALL` | S8 | markdown | 2324 | 30 | LOW | markdown of 2324 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/cabinet_ledger.dmk` | `N_MEDIUM` | S5 | text | 2571 | 65 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Filing Cabinet/canonical_artifacts.dmk` | `N_SMALL` | S8 | text | 2616 | 65 | MID | text of 2616 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/manifests.dmk` | `N_MEDIUM` | S5 | text | 2555 | 65 | MID | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Filing Cabinet/models.dmk` | `N_SMALL` | S8 | text | 2531 | 65 | MID | text of 2531 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/retrieval_pointers.dmk` | `N_SMALL` | S8 | text | 2621 | 65 | MID | text of 2621 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Filing Cabinet/rollback_records.dmk` | `N_SMALL` | S8 | text | 2606 | 66 | MID | text of 2606 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Full Stack UI/26.1_Full_Stack_UI_Interfaces.jaui` | `N_SMALL` | S8 | text | 1734 | 46 | LOW | text of 1734 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Full Stack UI/26.2_Full_Stack_UI_Uploads.jaui` | `N_SMALL` | S8 | text | 1780 | 47 | LOW | text of 1780 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Full Stack UI/26.3_Full_Stack_UI_Dashboards.jaui` | `N_SMALL` | S8 | text | 1764 | 46 | LOW | text of 1764 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Full Stack UI/26.4_Full_Stack_UI_Endpoints.jaui` | `N_SMALL` | S8 | text | 1724 | 46 | LOW | text of 1724 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Full Stack UI/26.5_Full_Stack_UI_Job_Controls.jaui` | `N_SMALL` | S8 | text | 2438 | 67 | MID | text of 2438 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Full Stack UI/README.md` | `N_MEDIUM` | S8 | markdown | 11235 | 177 | MID | markdown of 11235 bytes (<= 128 KiB) |
| `legacy/source_repository/Funnel/09_funnel.jad` | `N_SMALL` | S8 | text | 2302 | 55 | MID | text of 2302 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Funnel/README.md` | `N_SMALL` | S8 | markdown | 1637 | 32 | LOW | markdown of 1637 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Funnel/broad_repository_recall_results.dmk` | `N_SMALL` | S8 | text | 2655 | 66 | MID | text of 2655 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Grinder/07_grinder_candidate_improvement.deepml` | `N_SMALL` | S8 | text | 1544 | 29 | LOW | text of 1544 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Grinder/07_grinder_optimization.deepml` | `N_SMALL` | S8 | text | 1379 | 28 | LOW | text of 1379 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Grinder/07_grinder_reduction.deepml` | `N_SMALL` | S8 | text | 1363 | 28 | LOW | text of 1363 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Grinder/07_grinder_repeated_evaluation.deepml` | `N_SMALL` | S8 | text | 1528 | 30 | LOW | text of 1528 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Grinder/07_grinder_stress_analysis.deepml` | `N_SMALL` | S8 | text | 1641 | 33 | LOW | text of 1641 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Grinder/README.md` | `N_SMALL` | S8 | markdown | 1908 | 29 | LOW | markdown of 1908 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Illuminator/10_illuminator_assumptions.jaui` | `N_SMALL` | S8 | text | 1066 | 26 | LOW | text of 1066 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Illuminator/10_illuminator_diagnostics.jaui` | `N_SMALL` | S8 | text | 1146 | 26 | LOW | text of 1146 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Illuminator/10_illuminator_findings.jaui` | `N_SMALL` | S8 | text | 997 | 26 | LOW | text of 997 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Illuminator/10_illuminator_reports.jaui` | `N_SMALL` | S8 | text | 1039 | 26 | LOW | text of 1039 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Illuminator/README.md` | `N_SMALL` | S8 | markdown | 1870 | 28 | LOW | markdown of 1870 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.10_Resource_Dashboard.jaops` | `N_SMALL` | S8 | text | 1171 | 34 | LOW | text of 1171 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.11_Resource_Usage_Monitor.jaops` | `N_SMALL` | S8 | text | 1128 | 34 | LOW | text of 1128 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.12_Logs_Service.jaops` | `N_SMALL` | S8 | text | 1149 | 34 | LOW | text of 1149 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.13_Learning_Event_Recording.jaops` | `N_SMALL` | S8 | text | 1171 | 34 | LOW | text of 1171 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.1_Repository_Indexing.jaops` | `N_SMALL` | S8 | text | 1124 | 34 | LOW | text of 1124 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.2_Storage.jaops` | `N_SMALL` | S8 | text | 1085 | 34 | LOW | text of 1085 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.3_Resource_Monitoring.jaops` | `N_SMALL` | S8 | text | 1165 | 34 | LOW | text of 1165 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.4_Diagnostics.jaops` | `N_SMALL` | S8 | text | 1142 | 34 | LOW | text of 1142 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.5_Logs.jaops` | `N_SMALL` | S8 | text | 1043 | 34 | LOW | text of 1043 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.6_Retries.jaops` | `N_SMALL` | S8 | text | 1060 | 34 | LOW | text of 1060 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.7_Failure_Handling.jaops` | `N_SMALL` | S8 | text | 1138 | 34 | LOW | text of 1138 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.8_Repository_Indexing_Service.jaops` | `N_SMALL` | S8 | text | 1244 | 34 | LOW | text of 1244 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/58.9_Storage_Manager.jaops` | `N_SMALL` | S8 | text | 1200 | 34 | LOW | text of 1200 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Indexing Storage Resources Logs and Recovery/README.md` | `N_MEDIUM` | S8 | markdown | 20837 | 455 | HIGH | markdown of 20837 bytes (<= 128 KiB) |
| `legacy/source_repository/JA Adapter/30.1_JA_Adapter_Record_Intake.jasp` | `N_SMALL` | S8 | text | 1013 | 37 | LOW | text of 1013 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/JA Adapter/30.2_JA_Adapter_Record_Parser.jasp` | `N_SMALL` | S8 | text | 1037 | 38 | LOW | text of 1037 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/JA Adapter/30.3_JA_Adapter_Record_Normalizer.jasp` | `N_SMALL` | S8 | text | 1059 | 37 | LOW | text of 1059 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/JA Adapter/30.4_JA_Adapter_Reconstruction_Emitter.jasp` | `N_SMALL` | S8 | text | 1166 | 38 | LOW | text of 1166 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/JA Adapter/30.5_JA_Adapter_Rendering_Emitter.jasp` | `N_SMALL` | S8 | text | 1109 | 38 | LOW | text of 1109 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/JA Adapter/30.6_JA_Adapter_Storage_Emitter.jasp` | `N_SMALL` | S8 | text | 1086 | 38 | LOW | text of 1086 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/JA Adapter/README.md` | `N_MEDIUM` | S8 | markdown | 12537 | 171 | MID | markdown of 12537 bytes (<= 128 KiB) |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.1_Deterministic_Queues.jaops` | `N_SMALL` | S8 | text | 1112 | 34 | LOW | text of 1112 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.2_Worker_Management.jaops` | `N_SMALL` | S8 | text | 1113 | 34 | LOW | text of 1113 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.3_Isolated_Sandboxes.jaops` | `N_SMALL` | S8 | text | 1126 | 34 | LOW | text of 1126 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.4_Status_Tracking.jaops` | `N_SMALL` | S8 | text | 1096 | 34 | LOW | text of 1096 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.5_Recovery.jaops` | `N_SMALL` | S8 | text | 1124 | 34 | LOW | text of 1124 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.6_Job_Queue.jaops` | `N_SMALL` | S8 | text | 1028 | 34 | LOW | text of 1028 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.7_Worker_Manager.jaops` | `N_SMALL` | S8 | text | 1106 | 34 | LOW | text of 1106 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.8_Sandboxes.jaops` | `N_SMALL` | S8 | text | 1167 | 34 | LOW | text of 1167 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/56.9_Failures_and_Retries.jaops` | `N_SMALL` | S8 | text | 1105 | 34 | LOW | text of 1105 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Job Queue Workers and Sandboxes/README.md` | `N_MEDIUM` | S8 | markdown | 17748 | 396 | HIGH | markdown of 17748 bytes (<= 128 KiB) |
| `legacy/source_repository/Knowledge Repository/41.10_Knowledge_Repository_Operational_Workflows.jad` | `N_SMALL` | S8 | text | 2720 | 63 | MID | text of 2720 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.1_Knowledge_Repository_Documentation.jad` | `N_SMALL` | S8 | text | 2522 | 62 | MID | text of 2522 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.2_Knowledge_Repository_Architecture_Records.jad` | `N_SMALL` | S8 | text | 2540 | 61 | MID | text of 2540 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.3_Knowledge_Repository_Commands.jad` | `N_SMALL` | S8 | text | 2513 | 62 | MID | text of 2513 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.4_Knowledge_Repository_Workflows.jad` | `N_SMALL` | S8 | text | 2509 | 62 | MID | text of 2509 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.5_Knowledge_Repository_Suite_References.jad` | `N_SMALL` | S8 | text | 2567 | 61 | MID | text of 2567 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.6_Knowledge_Repository_Suite_Documentation.jad` | `N_SMALL` | S8 | text | 2571 | 61 | MID | text of 2571 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.7_Knowledge_Repository_HERMIT_Commands.jad` | `N_SMALL` | S8 | text | 2647 | 63 | MID | text of 2647 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.8_Knowledge_Repository_Language_Anthology.jad` | `N_SMALL` | S8 | text | 2630 | 63 | MID | text of 2630 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/41.9_Knowledge_Repository_Architecture_Catalog.jad` | `N_SMALL` | S8 | text | 2666 | 63 | MID | text of 2666 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/README.md` | `N_MEDIUM` | S8 | markdown | 26536 | 375 | HIGH | markdown of 26536 bytes (<= 128 KiB) |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_architecture_catalog.dmk` | `N_SMALL` | S8 | text | 2873 | 74 | MID | text of 2873 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_architecture_records.dmk` | `N_SMALL` | S8 | text | 2786 | 72 | MID | text of 2786 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_commands.dmk` | `N_SMALL` | S8 | text | 2770 | 73 | MID | text of 2770 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_documentation.dmk` | `N_SMALL` | S8 | text | 2787 | 73 | MID | text of 2787 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_hermit_commands.dmk` | `N_SMALL` | S8 | text | 2849 | 74 | MID | text of 2849 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_language_anthology.dmk` | `N_SMALL` | S8 | text | 2853 | 74 | MID | text of 2853 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_operational_workflows.dmk` | `N_SMALL` | S8 | text | 2895 | 74 | MID | text of 2895 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_suite_documentation.dmk` | `N_SMALL` | S8 | text | 2817 | 72 | MID | text of 2817 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_suite_references.dmk` | `N_SMALL` | S8 | text | 2803 | 72 | MID | text of 2803 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Knowledge Repository/knowledge_repository_workflows.dmk` | `N_SMALL` | S8 | text | 2770 | 73 | MID | text of 2770 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/LANDON Integration and Run All/62.1_Approved_Execution_Integration.jaa` | `N_SMALL` | S8 | text | 1753 | 35 | LOW | text of 1753 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/LANDON Integration and Run All/62.2_Run.jaa` | `N_SMALL` | S8 | text | 1489 | 35 | LOW | text of 1489 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/LANDON Integration and Run All/62.3_Run_All.jaa` | `N_SMALL` | S8 | text | 1478 | 35 | LOW | text of 1478 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/LANDON Integration and Run All/62.4_Result_Reporting.jaa` | `N_SMALL` | S8 | text | 1598 | 35 | LOW | text of 1598 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/LANDON Integration and Run All/README.md` | `N_MEDIUM` | S8 | markdown | 15390 | 353 | HIGH | markdown of 15390 bytes (<= 128 KiB) |
| `legacy/source_repository/Local Model Provider and Health/54.1_Approved_Local_Providers.jasp` | `N_SMALL` | S8 | text | 1259 | 41 | LOW | text of 1259 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.2_Provider_Routing.jasp` | `N_SMALL` | S8 | text | 1286 | 42 | LOW | text of 1286 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.3_Provider_Lifecycle.jasp` | `N_SMALL` | S8 | text | 1274 | 42 | LOW | text of 1274 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.4_Provider_Readiness.jasp` | `N_SMALL` | S8 | text | 1271 | 41 | LOW | text of 1271 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.5_Provider_Health.jasp` | `N_SMALL` | S8 | text | 1287 | 43 | LOW | text of 1287 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.6_Local_Model_Provider_Contract.jasp` | `N_SMALL` | S8 | text | 1362 | 43 | LOW | text of 1362 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.7_Model_Provider_Dashboard.jasp` | `N_SMALL` | S8 | text | 1346 | 44 | LOW | text of 1346 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/54.8_Model_Lifecycle_and_Health.jasp` | `N_SMALL` | S8 | text | 1455 | 45 | LOW | text of 1455 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Local Model Provider and Health/README.md` | `N_MEDIUM` | S8 | markdown | 17395 | 340 | HIGH | markdown of 17395 bytes (<= 128 KiB) |
| `legacy/source_repository/Localization and Large File Plane/45.1_Localization_and_Large_File_Plane_Multilingual_Presentation.jaui` | `N_SMALL` | S8 | text | 2173 | 47 | LOW | text of 2173 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/45.2_Localization_and_Large_File_Plane_Accessibility_Presentation.jaui` | `N_SMALL` | S8 | text | 2272 | 47 | MID | text of 2272 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/45.3_Localization_and_Large_File_Plane_Bounded_Large_File_Windows.jaui` | `N_SMALL` | S8 | text | 2030 | 47 | LOW | text of 2030 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/45.4_Localization_and_Large_File_Plane_Repository_Scale_Navigation.jaui` | `N_SMALL` | S8 | text | 2214 | 47 | LOW | text of 2214 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/45.5_Localization_and_Large_File_Plane_Localization_System.jaui` | `N_SMALL` | S8 | text | 2202 | 47 | LOW | text of 2202 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/45.6_Localization_and_Large_File_Plane_Large_File_System.jaui` | `N_SMALL` | S8 | text | 2160 | 47 | LOW | text of 2160 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/45.7_Localization_and_Large_File_Plane_Accessibility_System.jaui` | `N_SMALL` | S8 | text | 2381 | 47 | LOW | text of 2381 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Localization and Large File Plane/README.md` | `N_MEDIUM` | S8 | markdown | 16681 | 215 | MID | markdown of 16681 bytes (<= 128 KiB) |
| `legacy/source_repository/Media Export/25.1_Media_Export_Frame_Sequence_Encoding.jaops` | `N_SMALL` | S8 | text | 1086 | 31 | LOW | text of 1086 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Media Export/25.2_Media_Export_Audio_Encoding.jaops` | `N_SMALL` | S8 | text | 1056 | 31 | LOW | text of 1056 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Media Export/25.3_Media_Export_AV_Synchronization_Multiplexing.jaops` | `N_SMALL` | S8 | text | 1078 | 31 | LOW | text of 1078 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Media Export/25.4_Media_Export_Delivery_Format_Validation.jaops` | `N_SMALL` | S8 | text | 1238 | 33 | LOW | text of 1238 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Media Export/README.md` | `N_MEDIUM` | S8 | markdown | 12006 | 183 | MID | markdown of 12006 bytes (<= 128 KiB) |
| `legacy/source_repository/Mesh Geometry/19.1_Mesh_Geometry_Geometric_Proxies.deepml` | `N_SMALL` | S8 | text | 1813 | 33 | LOW | text of 1813 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Mesh Geometry/19.2_Mesh_Geometry_Depth_Hypotheses.deepml` | `N_SMALL` | S8 | text | 1788 | 32 | LOW | text of 1788 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Mesh Geometry/19.3_Mesh_Geometry_Topology.deepml` | `N_SMALL` | S8 | text | 1829 | 33 | LOW | text of 1829 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Mesh Geometry/19.4_Mesh_Geometry_Camera_Coordinates.deepml` | `N_SMALL` | S8 | text | 1911 | 34 | LOW | text of 1911 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Mesh Geometry/19.5_Mesh_Geometry_Deformable_Meshes.deepml` | `N_SMALL` | S8 | text | 2017 | 34 | LOW | text of 2017 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Mesh Geometry/README.md` | `N_MEDIUM` | S8 | markdown | 10451 | 164 | MID | markdown of 10451 bytes (<= 128 KiB) |
| `legacy/source_repository/Motion Planner/22.1_Motion_Planner_Transforms.deepml` | `N_SMALL` | S8 | text | 1291 | 26 | LOW | text of 1291 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Motion Planner/22.2_Motion_Planner_Constraints.deepml` | `N_SMALL` | S8 | text | 1453 | 30 | LOW | text of 1453 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Motion Planner/22.3_Motion_Planner_Timing.deepml` | `N_SMALL` | S8 | text | 1293 | 30 | LOW | text of 1293 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Motion Planner/22.4_Motion_Planner_Camera_Motion.deepml` | `N_SMALL` | S8 | text | 1506 | 28 | LOW | text of 1506 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Motion Planner/22.5_Motion_Planner_Continuity.deepml` | `N_SMALL` | S8 | text | 1625 | 35 | LOW | text of 1625 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Motion Planner/README.md` | `N_MEDIUM` | S8 | markdown | 9869 | 163 | MID | markdown of 9869 bytes (<= 128 KiB) |
| `legacy/source_repository/Observer/01_observer_decisions.jaa` | `N_SMALL` | S8 | text | 1915 | 39 | LOW | text of 1915 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/01_observer_errors.jaa` | `N_SMALL` | S8 | text | 1813 | 39 | LOW | text of 1813 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/01_observer_evidence.jaa` | `N_SMALL` | S8 | text | 1899 | 39 | LOW | text of 1899 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/01_observer_prompts.jaa` | `N_SMALL` | S8 | text | 1762 | 38 | LOW | text of 1762 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/01_observer_runtime_events.jaa` | `N_SMALL` | S8 | text | 1914 | 38 | LOW | text of 1914 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/01_observer_uploads.jaa` | `N_SMALL` | S8 | text | 1789 | 38 | LOW | text of 1789 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/MANIFEST.json` | `N_MEDIUM` | S5 | json | 3167 | 101 | MID | json named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Observer/README.md` | `N_SMALL` | S8 | markdown | 1763 | 43 | MID | markdown of 1763 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Observer/SHA256SUMS.txt` | `N_MEDIUM` | S5 | sums | 777 | 8 | LOW | sums named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Operations Plane/53.1_Operations_Plane_AI_Service_Registry.jaops` | `N_SMALL` | S8 | text | 1143 | 34 | LOW | text of 1143 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/53.2_Operations_Plane_Runtime_Resource_Control.jaops` | `N_SMALL` | S8 | text | 1170 | 34 | LOW | text of 1170 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/53.3_Operations_Plane_Job_Scheduling_and_Quotas.jaops` | `N_SMALL` | S8 | text | 1105 | 34 | LOW | text of 1105 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/53.4_Operations_Plane_Health_and_Observability.jaops` | `N_SMALL` | S8 | text | 1174 | 34 | LOW | text of 1174 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/53.5_Operations_Plane_Secrets_and_Configuration.jaops` | `N_SMALL` | S8 | text | 1209 | 34 | LOW | text of 1209 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/53.6_Operations_Plane_Deployment_and_Scaling.jaops` | `N_SMALL` | S8 | text | 1167 | 34 | LOW | text of 1167 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/53.7_Operations_Plane_Upgrade_and_Rollback.jaops` | `N_SMALL` | S8 | text | 1132 | 34 | LOW | text of 1132 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Operations Plane/README.md` | `N_MEDIUM` | S8 | markdown | 11844 | 248 | HIGH | markdown of 11844 bytes (<= 128 KiB) |
| `legacy/source_repository/Orchestrator II/32.1_Orchestrator_II_Reconstruction.jaa` | `N_SMALL` | S8 | text | 1703 | 35 | LOW | text of 1703 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator II/32.2_Orchestrator_II_Rendering.jaa` | `N_SMALL` | S8 | text | 1519 | 35 | LOW | text of 1519 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator II/32.3_Orchestrator_II_Validation.jaa` | `N_SMALL` | S8 | text | 1620 | 35 | LOW | text of 1620 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator II/32.4_Orchestrator_II_Learning_Records.jaa` | `N_SMALL` | S8 | text | 1687 | 35 | LOW | text of 1687 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator II/32.5_Orchestrator_II_Release_Packaging.jaa` | `N_MEDIUM` | S5 | text | 1579 | 35 | LOW | text named like an integrity/contract artifact needs signing, trust chain and independent verification |
| `legacy/source_repository/Orchestrator II/README.md` | `N_MEDIUM` | S8 | markdown | 13491 | 188 | MID | markdown of 13491 bytes (<= 128 KiB) |
| `legacy/source_repository/Orchestrator/15.1_Orchestrator_Suite_Fan_Out.jaa` | `N_SMALL` | S8 | text | 1462 | 36 | LOW | text of 1462 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator/15.2_Orchestrator_Deterministic_Fan_In.jaa` | `N_SMALL` | S8 | text | 1495 | 36 | LOW | text of 1495 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator/15.3_Orchestrator_Load_Order.jaa` | `N_SMALL` | S8 | text | 1483 | 36 | LOW | text of 1483 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator/15.4_Orchestrator_Conflict_Resolution.jaa` | `N_SMALL` | S8 | text | 1559 | 36 | LOW | text of 1559 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator/15.5_Orchestrator_Synthesis.jaa` | `N_SMALL` | S8 | text | 1523 | 36 | LOW | text of 1523 bytes (<= 8 KiB): teaching-sized |
| `legacy/source_repository/Orchestrator/README.md` | `N_MEDIUM` | S8 | markdown | 8592 | 166 | MID | markdown of 8592 bytes (<= 128 KiB) |
| `legacy/source_repository/Pencil Sharpener/06_pencil_sharpener_clarity.ja` | `N_SMALL` | S8 | text | 1288 | 26 | MID | text of 1288 bytes (<= 8 KiB): teaching-sized |
| ... 5113 more in SORT_LEDGER.json | | | | | | | |

**Portable storage.** 1461 script(s) are stored under an alias (`cargo/_alias/<sha256(path)[:16]><ext>`) because their original path cannot exist on every host (a path that differs only by case from another, or a delivered path over 140 characters -- `Unikernel_Containership/berths/vm_xtra_large/<slot>/cargo/<path>` -- which a Windows extraction would refuse); their identity, bytes, node and rule are unchanged. First few:

* `legacy/source_repository/Air Gap Certification and Installer Plane/46.10_Air_Gap_Certification_and_Installer_Plane_Installer.jaops` -> `_alias/8a5fffe9c85b0557.jaops` -- the delivered path would be 190 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.11_Air_Gap_Certification_and_Installer_Plane_License_System.jaops` -> `_alias/c5f2847ad8c1099e.jaops` -- the delivered path would be 195 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.1_Air_Gap_Certification_and_Installer_Plane_Offline_Runtime_Policy.jaops` -> `_alias/58d9089440108f49.jaops` -- the delivered path would be 202 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.2_Air_Gap_Certification_and_Installer_Plane_Certification_Records.jaops` -> `_alias/dfc9214808693b49.jaops` -- the delivered path would be 201 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.3_Air_Gap_Certification_and_Installer_Plane_One_Click_Setup_Transaction.jaops` -> `_alias/d00a3b3a6db68896.jaops` -- the delivered path would be 207 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.4_Air_Gap_Certification_and_Installer_Plane_Licensing.jaops` -> `_alias/73e0b60687bc44f5.jaops` -- the delivered path would be 189 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.5_Air_Gap_Certification_and_Installer_Plane_Installer_Integration.jaops` -> `_alias/abccee960590709d.jaops` -- the delivered path would be 201 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.6_Air_Gap_Certification_and_Installer_Plane_Air_Gap_Runtime.jaops` -> `_alias/90afd56b468826a8.jaops` -- the delivered path would be 195 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.7_Air_Gap_Certification_and_Installer_Plane_Certification_Fabric.jaops` -> `_alias/c8bc06ff40552726.jaops` -- the delivered path would be 200 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.8_Air_Gap_Certification_and_Installer_Plane_One_Click_Setup.jaops` -> `_alias/d1dffe7e8b619c65.jaops` -- the delivered path would be 195 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Air Gap Certification and Installer Plane/46.9_Air_Gap_Certification_and_Installer_Plane_Multilingual_Setup.jaops` -> `_alias/ed3ef70987f6b8e9.jaops` -- the delivered path would be 198 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* `legacy/source_repository/Animation VFX Workspace/34.1_Animation_VFX_Workspace_Animation.deepml` -> `_alias/b41900a40f6917fd.deepml` -- the delivered path would be 154 characters, over the 140-character budget (Windows MAX_PATH is 260 for the whole path, and Explorer's zip extractor does not lift it)
* ... 1449 more in SORT_LEDGER.json (`portable_storage.aliased`)
