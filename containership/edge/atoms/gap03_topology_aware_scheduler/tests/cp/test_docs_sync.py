import os
import unittest

from gap03_topology_aware_scheduler.controlplane import specs


class DocsSync(unittest.TestCase):
    def test_component_docs_match_specs(self):
        """docs/components/*.md are generated from controlplane/specs.py and must not drift (regenerate with
        python -m gap03_topology_aware_scheduler.controlplane.specs)."""
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "components")
        for s in specs.SPECS:
            with open(os.path.join(root, f"{s['mc']}.md"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), specs.render(s), s["mc"])
