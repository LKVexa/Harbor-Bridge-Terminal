"""Regression tests for UC-2.2.0 ship-layer boundaries.
Unit fault injection is deliberate and separate from the native gate battery.
"""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
import warnings
import zipfile
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ship"))
from unikernel import Refusal, SLOTS, UC_RELEASE
from unikernel import safety as S, berth as BT, engines as E, ucmanifest as M, cli, tif_fabric as TF

class TempCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = mock.patch.object(E, "SHIP", str(self.root)); self.patch.start(); self.addCleanup(self.patch.stop)
    def file(self, rel, value=b"data"):
        p = self.root / rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value.encode() if isinstance(value,str) else value); return p
    def z(self, entries):
        mem = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
                for name, value in entries: z.writestr(name, value)
        mem.seek(0); return zipfile.ZipFile(mem)

class Names(TempCase):
    def test_normal_names(self):
        for n in ("a", "vm_small", "Cargo-1.2", "A"*64): self.assertEqual(S.validate_name(n), n)
    def test_unicode_normalization(self): self.assertEqual(S.portable_key("cafe\u0301"),S.portable_key("caf\u00e9"))
    def test_portable_case(self): self.assertEqual(S.portable_key("Foo/A"),S.portable_key("foo/a"))
    def test_safe_path(self): self.assertEqual(S.contained_path(str(self.root),"a/b"),str(self.root/"a/b"))
    def test_symlink_component(self):
        self.file("outside/a"); (self.root/"link").symlink_to(self.root/"outside",target_is_directory=True)
        with self.assertRaises(Refusal): S.contained_path(str(self.root),"link/a")
    def test_root_symlink(self):
        (self.root/"real").mkdir(); (self.root/"link").symlink_to(self.root/"real",target_is_directory=True)
        with self.assertRaises(Refusal): S.contained_path(str(self.root/"link"),"a")
    def test_path_with_spaces(self): self.assertTrue(S.contained_path(str(self.root),"folder space/a.txt").endswith("folder space/a.txt"))
    def test_alias_is_deterministic(self): self.assertEqual(BT.stored_alias("x/a"),BT.stored_alias("x/a"))
    def test_alias_unsafe_extension_removed(self): self.assertNotIn(":",BT.stored_alias("x.a:b"))
    def test_face_name_bounded(self):
        from unikernel import face_container_name
        self.assertLessEqual(len(face_container_name("a"*64)),64)

for i,n in enumerate(("", "../outside", "a/b", "a\\b", "C:foo", "a\n", "a.", "CON", "nul.txt", "com1", "LPT9.x", "1abc", "a"*65, "\u00e9", "a ")):
    def test(self,n=n):
        with self.assertRaises(Refusal): S.validate_name(n)
    setattr(Names, f"test_rejected_name_{i:02d}",test)
for i,p in enumerate(("", "..", "../x", "/a", "C:/a", "C:a", "a\\b", "a//b", "a/./b", "a/../b", "a\x00b", "a\x7fb", "//host/path")):
    def test(self,p=p):
        with self.assertRaises(Refusal): S.relative_path(p)
    setattr(Names, f"test_rejected_path_{i:02d}",test)

class Archives(TempCase):
    def test_normal(self):
        with self.z([("top/a.txt",b"hello")]) as z:
            mapping,prefix=S.stage_zip(z,str(self.root/"stage"))
        self.assertEqual(prefix,"top"); self.assertEqual(Path(mapping["a.txt"]).read_bytes(),b"hello")
    def test_case_preserved(self):
        with self.z([("p/A.py",b"upper"),("p/a.py",b"lower")]) as z:
            mapping,_=S.stage_zip(z,str(self.root/"stage"))
        self.assertEqual(set(mapping),{"A.py","a.py"}); self.assertNotEqual(mapping["A.py"],mapping["a.py"])
    def test_multiple_roots_preserved(self):
        with self.z([("x/a",b"a"),("y/a",b"b")]) as z:
            mapping,prefix=S.stage_zip(z,str(self.root/"stage"))
        self.assertIsNone(prefix); self.assertEqual(set(mapping),{"x/a","y/a"})
    def test_duplicate(self):
        with self.z([("a",b"1"),("a",b"2")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z)
    def test_file_directory_conflict(self):
        with self.z([("a",b"1"),("a/b",b"2")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z)
    def test_count_limit(self):
        with self.z([("a",b"1"),("b",b"2")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z,S.ArchiveLimits(entries=1))
    def test_member_limit(self):
        with self.z([("a",b"12")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z,S.ArchiveLimits(member_bytes=1))
    def test_total_limit(self):
        with self.z([("a",b"12"),("b",b"34")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z,S.ArchiveLimits(total_bytes=3))
    def test_ratio_limit(self):
        with self.z([("a",b"0"*(1024*1024+1))]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z,S.ArchiveLimits(ratio=2))
    def test_symlink(self):
        zi=zipfile.ZipInfo("link"); zi.create_system=3; zi.external_attr=(stat.S_IFLNK|0o777)<<16
        with self.z([(zi,b"../outside")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z)
    def test_fifo(self):
        zi=zipfile.ZipInfo("pipe"); zi.create_system=3; zi.external_attr=(stat.S_IFIFO|0o600)<<16
        with self.z([(zi,b"")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z)
    def test_null_name(self):
        with self.z([("a",b"x")]) as z:
            z.infolist()[0].orig_filename="a\x00b"
            with self.assertRaises(Refusal): S.inspect_zip(z)
    def test_encrypted_member(self):
        with self.z([("a",b"x")]) as z:
            z.infolist()[0].flag_bits |= 1
            with self.assertRaises(Refusal): S.inspect_zip(z)
    def test_preflight_writes_nothing(self):
        with self.z([("a",b"x"),("../bad",b"y")]) as z:
            with self.assertRaises(Refusal): S.stage_zip(z,str(self.root/"stage"))
        self.assertFalse((self.root/"stage").exists())
for i,name in enumerate(("../bad", "/bad", "C:/bad", "a\\b", "a/../b", "a//b")):
    def test(self,name=name):
        with self.z([(name,b"x")]) as z:
            with self.assertRaises(Refusal): S.inspect_zip(z)
    setattr(Archives,f"test_archive_bad_path_{i}",test)

class Integrity(TempCase):
    def setUp(self):
        super().setUp(); self.file("a.txt",b"a"); M.write_sums(str(self.root),extra=())
    def test_valid_sums(self): self.assertTrue(M.check_sums(str(self.root))["pass"])
    def test_changed_bytes(self):
        self.file("a.txt",b"b"); self.assertFalse(M.check_sums(str(self.root))["pass"])
    def test_unbound(self):
        self.file("b.txt"); self.assertIn("b.txt",M.check_sums(str(self.root))["unbound"])
    def test_missing(self):
        (self.root/"a.txt").unlink(); self.assertIn("a.txt",M.check_sums(str(self.root))["missing"])
    def test_duplicate_sum(self):
        p=self.root/"SHA256SUMS.txt"; p.write_text(p.read_text()*2)
        self.assertTrue(M.check_sums(str(self.root))["errors"])
    def test_malformed_sum(self):
        self.file("SHA256SUMS.txt","x  a.txt\n"); self.assertFalse(M.check_sums(str(self.root))["pass"])
    def test_escape_sum(self):
        self.file("SHA256SUMS.txt","0"*64+"  ../x\n"); self.assertTrue(M.check_sums(str(self.root))["errors"])
    def man(self):
        inv=M.inventory(str(self.root)); return {"files":inv,"file_count":len(inv),"total_bytes":sum(r["bytes"] for r in inv)}
    def test_valid_manifest(self): self.assertTrue(M.check_manifest_inventory(str(self.root),self.man())["pass"])
    def test_manifest_duplicate(self):
        m=self.man(); m["files"]*=2; self.assertFalse(M.check_manifest_inventory(str(self.root),m)["pass"])
    def test_manifest_total(self):
        m=self.man(); m["total_bytes"]+=1; self.assertFalse(M.check_manifest_inventory(str(self.root),m)["pass"])
    def test_manifest_count(self):
        m=self.man(); m["file_count"]+=1; self.assertFalse(M.check_manifest_inventory(str(self.root),m)["pass"])
    def test_manifest_bool_size(self):
        m=self.man(); m["files"][0]["bytes"]=True; self.assertFalse(M.check_manifest_inventory(str(self.root),m)["pass"])
    def test_manifest_escape(self):
        m=self.man(); m["files"][0]["path"]="../a"; self.assertFalse(M.check_manifest_inventory(str(self.root),m)["pass"])
    def test_last_berth_reseal(self):
        self.file("MANIFEST.json",json.dumps({"berths":[{"berth":"old"}],"files":[]}))
        M.reseal(str(self.root),"remove last",berths=[])
        m=json.loads((self.root/"MANIFEST.json").read_text()); self.assertEqual(m["berths"],[]); self.assertEqual(m["uc_release"],UC_RELEASE)
        self.assertTrue(M.check_sums(str(self.root))["pass"])
    def test_hold_missing_pin(self):
        for slot in SLOTS: self.file(f"hold/{slot}.zip",b"zip")
        self.assertFalse(E.hold_state()["pass"])
    def test_hold_missing_pin_blocks_extraction(self):
        with self.assertRaises(Refusal): E.extract_hold()
        self.assertFalse((self.root/"_engines").exists())

class AtomicAndLock(TempCase):
    def test_atomic_write(self):
        p=self.file("a","old"); S.atomic_write(str(p),"new"); self.assertEqual(p.read_text(),"new")
    def test_replace_failure_preserves(self):
        p=self.file("a","old")
        with mock.patch.object(S.os,"replace",side_effect=OSError("injected")):
            with self.assertRaises(OSError): S.atomic_write(str(p),"new")
        self.assertEqual(p.read_text(),"old"); self.assertFalse(list(self.root.glob(".uc-tmp-*")))
    def test_atomic_json_utf8(self):
        p=self.root/"a.json"; S.atomic_json(str(p),{"name":"caf\u00e9"}); self.assertEqual(json.loads(p.read_text())["name"],"caf\u00e9")
    def test_nested_lock(self):
        with S.ship_lock(str(self.root)):
            with S.ship_lock(str(self.root)): pass
    def test_lock_release_after_exception(self):
        with self.assertRaises(RuntimeError):
            with S.ship_lock(str(self.root)): raise RuntimeError("test")
        with S.ship_lock(str(self.root)): pass
    def test_second_process_is_blocked(self):
        code='from unikernel import safety as S, Refusal\nimport sys\ntry:\n with S.ship_lock(sys.argv[1]): pass\nexcept Refusal: sys.exit(3)\n'
        env={**os.environ,"PYTHONPATH":str(ROOT/"ship")}
        with S.ship_lock(str(self.root)):
            r=subprocess.run([sys.executable,"-B","-c",code,str(self.root)],env=env,capture_output=True,timeout=10)
        self.assertEqual(r.returncode,3,r.stderr)
        r=subprocess.run([sys.executable,"-B","-c",code,str(self.root)],env=env,capture_output=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)

class Lifecycle(TempCase):
    def old(self): return self.file("berths/demo/keep.txt","original")
    def builder(self,source,name,kind,dest,**kw):
        p=Path(dest); p.mkdir(parents=True); (p/"new.txt").write_text("new")
        M.write_sums(str(p),extra=()); return {"berth":name}
    def test_unload_traversal_preserves_outside(self):
        p=self.file("outside/keep.txt","safe")
        with self.assertRaises(Refusal): BT.unload("../outside")
        self.assertEqual(p.read_text(),"safe")
    def test_replace_missing_preserves_old(self):
        p=self.old()
        with self.assertRaises(Refusal): BT.load(str(self.root/"missing"),"demo",replace=True)
        self.assertEqual(p.read_text(),"original")
    def test_refuse_replace_without_flag(self):
        self.old()
        with self.assertRaises(Refusal): BT.load("unused","demo")
    def test_stage_exception_preserves_old(self):
        p=self.old()
        with mock.patch.object(BT,"_load_uncommitted",side_effect=RuntimeError("injected")):
            with self.assertRaises(RuntimeError): BT.load("x","demo",replace=True)
        self.assertEqual(p.read_text(),"original")
    def test_replace_keeps_backup(self):
        self.old()
        with mock.patch.object(BT,"_load_uncommitted",side_effect=self.builder): r=BT.load("x","demo",replace=True)
        self.assertEqual((Path(r["replacement_backup"])/"keep.txt").read_text(),"original")
        self.assertEqual((self.root/"berths/demo/new.txt").read_text(),"new")
    def test_commit_failure_rolls_back(self):
        p=self.old(); original=os.replace
        def replace(src,dst):
            if str(src).endswith("/candidate") and str(dst).endswith("/berths/demo"): raise OSError("injected commit failure")
            return original(src,dst)
        with mock.patch.object(BT,"_load_uncommitted",side_effect=self.builder),mock.patch.object(BT.os,"replace",side_effect=replace):
            with self.assertRaises(OSError): BT.load("x","demo",replace=True)
        self.assertEqual(p.read_text(),"original")
    def test_unload_recoverable(self):
        self.old(); r=BT.unload("demo"); self.assertFalse((self.root/"berths/demo").exists())
        self.assertTrue(r["recoverable"]); self.assertEqual((Path(r["backup"])/"keep.txt").read_text(),"original")
    def test_case_collision(self):
        self.old()
        with self.assertRaises(Refusal): BT.load("x","Demo")
    def test_directory_symlink_rejected(self):
        self.file("source/a"); (self.root/"source/link").symlink_to(self.root/"outside",target_is_directory=True)
        with self.assertRaises(Refusal): BT.list_scripts(str(self.root/"source"))
    def test_failed_final_journal_is_retained(self):
        self.old(); real=S.atomic_json
        def inject(p,obj):
            if obj.get("phase")=="COMMITTED": raise OSError("injected journal failure")
            return real(p,obj)
        with mock.patch.object(BT,"_load_uncommitted",side_effect=self.builder),mock.patch.object(S,"atomic_json",side_effect=inject):
            with self.assertRaises(OSError): BT.load("x","demo",replace=True)
        self.assertTrue((self.root/"berths/demo/new.txt").exists())
        self.assertEqual(len(list((self.root/"_runs/transactions").glob("*/journal.json"))),1)

class CLI(TempCase):
    def call(self,args):
        with contextlib.redirect_stdout(io.StringIO()): return cli.main(args)
    def test_bad_name_exit(self): self.assertEqual(self.call(["unload","../outside"]),3)
    def test_zero_ticks_exit(self): self.assertEqual(self.call(["run","demo","--ticks","0"]),3)
    def test_negative_ticks_exit(self): self.assertEqual(self.call(["run","demo","--ticks","-1"]),3)
    def test_nan_interval_exit(self): self.assertEqual(self.call(["run","demo","--interval","nan"]),3)
    def test_inf_interval_exit(self): self.assertEqual(self.call(["run","demo","--interval","inf"]),3)
    def test_programs_whitelist(self): self.assertEqual(self.call(["run","demo","--programs","unknown"]),3)
    def test_scale_bound(self): self.assertEqual(self.call(["fabric","view","demo","--scale","100"]),3)
    def test_step_limit(self): self.assertEqual(self.call(["slot-run","demo","DF_Small","x","--max-steps","0"]),3)
    def test_interruption(self):
        with mock.patch.object(cli,"cmd_status",side_effect=KeyboardInterrupt): self.assertEqual(self.call(["status"]),130)
    def test_uncaught_error_has_log(self):
        with mock.patch.object(cli,"cmd_status",side_effect=RuntimeError("injected")): self.assertEqual(self.call(["status"]),1)
        self.assertEqual(len(list((self.root/"_runs").glob("ERROR_*.log"))),1)
    def test_version(self):
        with contextlib.redirect_stdout(io.StringIO()) as text:
            with self.assertRaises(SystemExit) as exc: cli.main(["--version"])
        self.assertEqual(exc.exception.code,0); self.assertIn(UC_RELEASE,text.getvalue())
    def test_sort_path_traversal_rejected_before_bind(self):
        a=types.SimpleNamespace(name="demo",slot="DF_Small",cargo="../outside",max_steps=None)
        with mock.patch.object(E,"bind") as bind:
            with self.assertRaises(Refusal): cli.cmd_slot_run(a)
            bind.assert_not_called()

class TIFF(TempCase):
    def test_bad_paint_tile(self):
        with self.assertRaises(Refusal): TF.paint("does-not-exist",4,0,1)
    def test_bad_paint_word(self):
        with self.assertRaises(Refusal): TF.paint("does-not-exist",0,64,1)
    def test_file_size_budget(self):
        p=self.file("large.tif",b"0"*16)
        with mock.patch.object(TF,"MAX_TIF_BYTES",8):
            with self.assertRaises(Refusal): TF._validate_tif(str(p))
    def test_wrong_geometry(self):
        from PIL import Image
        p=self.root/"wrong.tif"; Image.new("RGBA",(100,100)).save(p)
        with mock.patch.object(TF,"codec"):
            with self.assertRaises(Refusal): TF._validate_tif(str(p))
    def test_png_not_tiff(self):
        from PIL import Image
        p=self.root/"not.tif"; Image.new("RGBA",(32,16)).save(p,format="PNG")
        with mock.patch.object(TF,"codec"):
            with self.assertRaises(Refusal): TF._validate_tif(str(p))

if __name__ == "__main__": unittest.main()
