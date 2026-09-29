"""Offline behavior tests. No B2 account, credentials, or network required."""

from contextlib import redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import assets


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.uploads = 0
        self.downloads = 0
        self.on_upload = lambda: None
        self.on_download = lambda: None
        self.corrupt = False

    def ensure(self, path, expected):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest == expected["sha256"]
        if digest not in self.objects:
            self.objects[digest] = data
            self.uploads += 1
        self.on_upload()
        return {**expected, "bucket": "test-bucket", "key": f"sha256/{digest}", "file_id": digest}

    def download(self, entry, destination):
        self.downloads += 1
        destination.write_bytes(b"corrupt" if self.corrupt else self.objects[entry["file_id"]])
        self.on_download()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.config = {"version": 1, "bucket": "test-bucket", "prefix": "test", "patterns": ["*.blend", "*.png"]}
        assets.write_json(self.root / assets.CONFIG, self.config)
        assets.write_json(self.root / assets.MANIFEST, {"version": 1, "files": {}})
        self.store = MemoryStore()
        self.output = io.StringIO()
        self.capture = redirect_stdout(self.output)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)
        self.run_command("ignore")

    def write(self, name, data=b"version one"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def manifest(self):
        return assets.read_json(self.root / assets.MANIFEST)

    def run_command(self, name, *args):
        project = assets.Project(self.root)
        with project.locked():
            if name in {"push", "pull"}:
                return getattr(project, name)(lambda config: self.store)
            return getattr(project, name)(*args)

    def test_nested_paths_spaces_unicode_and_deduplication(self):
        self.write("模型 源文件.blend")
        self.write("deep/anywhere/copy.blend")
        self.write("deep/script.py", b"print('keep in Git')")
        self.run_command("push")
        self.assertEqual(self.store.uploads, 1)
        self.assertEqual(set(self.manifest()["files"]), {"模型 源文件.blend", "deep/anywhere/copy.blend"})
        self.assertEqual(assets.Project(self.root).status(check=True), 0)
        self.run_command("push")
        self.assertEqual(self.store.uploads, 1)

    def test_git_switch_restores_exact_old_content_and_back_again(self):
        path = self.write("nested/model.blend")
        self.run_command("push")
        old = self.manifest()
        path.write_bytes(b"version two")
        self.run_command("push")
        new = self.manifest()
        assets.write_json(self.root / assets.MANIFEST, old)
        self.assertEqual(assets.Project(self.root).status(check=True), 1)
        self.assertIn("NEEDS_PULL", self.output.getvalue())
        with self.assertRaisesRegex(assets.AssetError, "Run pull"):
            self.run_command("push")
        self.run_command("pull")
        self.assertEqual(path.read_bytes(), b"version one")
        assets.write_json(self.root / assets.MANIFEST, new)
        self.run_command("pull")
        self.assertEqual(path.read_bytes(), b"version two")

    def test_fresh_clone_without_local_state(self):
        path = self.write("nested/model.blend")
        self.run_command("push")
        path.unlink()
        (self.root / assets.LOCAL / "state.json").unlink()
        self.run_command("pull")
        self.assertEqual(path.read_bytes(), b"version one")

    def test_unknown_and_unpublished_changes_block_all_downloads(self):
        path = self.write("a.blend")
        other = self.write("b.blend")
        self.run_command("push")
        other.unlink()
        path.write_bytes(b"unsaved to cloud")
        for keep_state in (True, False):
            if not keep_state:
                (self.root / assets.LOCAL / "state.json").unlink()
            with self.assertRaisesRegex(assets.AssetError, "local changes"):
                self.run_command("pull")
            self.assertEqual(self.store.downloads, 0)
            self.assertEqual(path.read_bytes(), b"unsaved to cloud")
            self.assertFalse(other.exists())

    def test_missing_and_excluded_references_require_explicit_forget(self):
        path = self.write("a.blend")
        self.run_command("push")
        before = self.manifest()
        path.unlink()
        with self.assertRaisesRegex(assets.AssetError, "Missing/excluded"):
            self.run_command("push")
        self.assertEqual(self.manifest(), before)
        self.run_command("forget", ["a.blend"])
        self.assertEqual(self.manifest()["files"], {})
        self.assertEqual(len(self.store.objects), 1)

    def test_excluded_reference_is_never_silently_removed(self):
        self.write("a.blend")
        self.run_command("push")
        before = self.manifest()
        self.config["patterns"].append("!a.blend")
        assets.write_json(self.root / assets.CONFIG, self.config)
        with self.assertRaisesRegex(assets.AssetError, "Missing/excluded"):
            self.run_command("push")
        self.assertEqual(self.manifest(), before)

    def test_rename_reuses_content_after_explicit_forget(self):
        path = self.write("old.blend")
        self.run_command("push")
        old_id = self.manifest()["files"]["old.blend"]["file_id"]
        path.rename(self.root / "new.blend")
        self.run_command("forget", ["old.blend"])
        self.run_command("push")
        self.assertEqual(self.manifest()["files"]["new.blend"]["file_id"], old_id)
        self.assertEqual(self.store.uploads, 1)

    def test_equal_size_edit_with_restored_mtime_is_detected(self):
        path = self.write("a.blend", b"aaaa")
        self.run_command("push")
        before = path.stat()
        path.write_bytes(b"bbbb")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(assets.Project(self.root).status(check=True), 1)
        self.assertIn("MODIFIED", self.output.getvalue())

    def test_forget_keeps_local_file_and_validates_all_arguments(self):
        path = self.write("a.blend")
        self.run_command("push")
        before = self.manifest()
        with self.assertRaisesRegex(assets.AssetError, "Not in manifest"):
            self.run_command("forget", ["a.blend", "missing.blend"])
        self.assertEqual(self.manifest(), before)
        self.run_command("forget", ["a.blend"])
        self.assertTrue(path.exists())

    def test_upload_failure_leaves_manifest_and_state_unchanged(self):
        path = self.write("a.blend")
        self.run_command("push")
        before = self.manifest()
        state = (self.root / assets.LOCAL / "state.json").read_bytes()
        path.write_bytes(b"second version")
        self.write("b.blend", b"other")
        def fail_on_second():
            if self.store.uploads == 3:
                raise assets.AssetError("network down")
        self.store.on_upload = fail_on_second
        with self.assertRaisesRegex(assets.AssetError, "network down"):
            self.run_command("push")
        self.assertEqual(self.manifest(), before)
        self.assertEqual((self.root / assets.LOCAL / "state.json").read_bytes(), state)
        self.store.on_upload = lambda: None
        self.run_command("push")
        self.assertEqual(self.store.uploads, 3)  # Successful orphan upload was reused.
        self.assertEqual(len(self.manifest()["files"]), 2)

    def test_source_edited_during_upload_keeps_old_reference(self):
        path = self.write("a.blend")
        before = self.manifest()
        self.store.on_upload = lambda: path.write_bytes(b"new Blender save")
        with self.assertRaisesRegex(assets.AssetError, "changed during upload"):
            self.run_command("push")
        self.assertEqual(self.manifest(), before)
        self.assertIn(b"version one", self.store.objects.values())

    def test_download_corruption_never_installs(self):
        path = self.write("a.blend")
        self.run_command("push")
        path.unlink()
        self.store.corrupt = True
        with self.assertRaisesRegex(assets.AssetError, "checksum mismatch"):
            self.run_command("pull")
        self.assertFalse(path.exists())

    def test_download_failure_leaves_all_destinations_untouched(self):
        a, b = self.write("a.blend"), self.write("b.blend", b"b")
        self.run_command("push")
        a.unlink()
        b.unlink()
        def fail_second():
            if self.store.downloads == 2:
                raise assets.AssetError("network down")
        self.store.on_download = fail_second
        with self.assertRaisesRegex(assets.AssetError, "network down"):
            self.run_command("pull")
        self.assertFalse(a.exists())
        self.assertFalse(b.exists())

    def test_local_edit_during_download_is_preserved(self):
        path = self.write("a.blend")
        self.run_command("push")
        path.unlink()
        self.store.on_download = lambda: path.write_bytes(b"concurrent edit")
        with self.assertRaisesRegex(assets.AssetError, "changed during download"):
            self.run_command("pull")
        self.assertEqual(path.read_bytes(), b"concurrent edit")

    def test_manifest_change_during_network_aborts(self):
        self.write("a.blend")
        manifest_path = self.root / assets.MANIFEST
        original = manifest_path.read_text()
        self.store.on_upload = lambda: manifest_path.write_text(original + "\n")
        with self.assertRaisesRegex(assets.AssetError, "manifest changed"):
            self.run_command("push")
        self.assertEqual(manifest_path.read_text(), original + "\n")

    def test_unreferenced_files_remain_after_pull(self):
        path = self.write("a.blend")
        self.run_command("push")
        assets.write_json(self.root / assets.MANIFEST, {"version": 1, "files": {}})
        self.run_command("pull")
        self.assertTrue(path.exists())
        self.assertEqual(assets.Project(self.root).status(check=True), 1)

    def test_patterns_exceptions_and_gitignore_preservation(self):
        self.write("model.blend")
        self.write("previews/keep.png")
        self.write("nested/texture.png")
        self.config["patterns"].append("!previews/*.png")
        assets.write_json(self.root / assets.CONFIG, self.config)
        ignore = self.root / ".gitignore"
        ignore.write_text("# custom user rule\n/private-notes/\n" + ignore.read_text())
        self.run_command("ignore")
        first = ignore.read_text()
        self.run_command("ignore")
        self.assertEqual(ignore.read_text(), first)
        self.assertIn("# custom user rule\n/private-notes/", first)
        self.run_command("push")
        self.assertEqual(set(self.manifest()["files"]), {"model.blend", "nested/texture.png"})

    def test_unignored_assets_block_upload(self):
        self.write("model.blend")
        (self.root / ".gitignore").write_text("")
        with self.assertRaisesRegex(assets.AssetError, "not ignored"):
            self.run_command("push")
        self.assertEqual(self.store.uploads, 0)

    def test_git_tracked_assets_block_upload_without_modifying_index(self):
        self.write("model.blend")
        with patch.object(assets.Project, "git", return_value=b"model.blend\0"):
            with self.assertRaisesRegex(assets.AssetError, "already tracked"):
                self.run_command("push")
        self.assertEqual(self.store.uploads, 0)

    def test_credentials_must_be_ignored_and_untracked_before_reading(self):
        project = assets.Project(self.root)
        with patch.object(assets, "B2Store") as store:
            (self.root / ".gitignore").write_text("")
            with self.assertRaisesRegex(assets.AssetError, "not ignored"):
                project.b2_store(self.config)
            with patch.object(project, "git", return_value=assets.CREDENTIALS.encode() + b"\0"):
                with self.assertRaisesRegex(assets.AssetError, "already tracked"):
                    project.b2_store(self.config)
            store.assert_not_called()

    def test_symlink_asset_and_destination_are_rejected(self):
        real = self.write("real.bin")
        (self.root / "a.blend").symlink_to(real)
        with self.assertRaisesRegex(assets.AssetError, "Symlinks"):
            self.run_command("push")
        (self.root / "a.blend").unlink()
        self.write("folder/a.blend")
        self.run_command("push")
        (self.root / "folder/a.blend").unlink()
        (self.root / "folder").rmdir()
        (self.root / "folder").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(assets.AssetError, "Symlinks"):
            self.run_command("pull")

    def test_manifest_path_traversal_and_control_files_rejected(self):
        self.write("a.blend")
        self.run_command("push")
        entry = self.manifest()["files"]["a.blend"]
        for name in ("../outside.blend", "/tmp/escape.blend", ".git/config", ".assets.json",
                     "foo/../escape.blend", "C:/escape.blend", ".env", "foo/.env.local"):
            with self.subTest(name=name):
                assets.write_json(self.root / assets.MANIFEST, {"version": 1, "files": {name: entry}})
                with self.assertRaises(assets.AssetError):
                    assets.Project(self.root)

    def test_lock_blocks_second_writer_and_is_released_after_failure(self):
        first = assets.Project(self.root)
        with first.locked():
            with self.assertRaisesRegex(assets.AssetError, "Another asset command"):
                self.run_command("push")
        self.run_command("push")
        self.assertFalse((self.root / assets.LOCAL / "lock").exists())

    def test_zero_byte_asset_roundtrip(self):
        path = self.write("empty.blend", b"")
        self.run_command("push")
        path.unlink()
        self.run_command("pull")
        self.assertEqual(path.read_bytes(), b"")

    def test_status_and_noop_push_do_not_create_remote_client(self):
        self.write("a.blend")
        self.run_command("push")
        project = assets.Project(self.root)
        def unexpected(config):
            self.fail("No network expected")
        self.assertEqual(project.status(check=True), 0)
        with project.locked():
            project.push(unexpected)


class B2AdapterTests(unittest.TestCase):
    """Exercise the actual SDK against Backblaze's in-memory API simulator."""

    def setUp(self):
        from b2sdk.v2 import B2Api, B2HttpApiConfig, InMemoryAccountInfo, RawSimulator
        self.api = B2Api(InMemoryAccountInfo(), api_config=B2HttpApiConfig(_raw_api_class=RawSimulator))
        account, key = self.api.session.raw_api.create_account()
        self.api.authorize_account("production", account, key)
        self.bucket = self.api.create_bucket("test-bucket", "allPrivate")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.credentials_path = self.root / assets.CREDENTIALS
        self.credentials_path.parent.mkdir()
        assets.write_json(self.credentials_path, {"application_key_id": account, "application_key": key})
        # Stale environment values must not override the local file.
        with patch("b2sdk.v2.B2Api", return_value=self.api), patch.dict(os.environ, {
                "B2_APPLICATION_KEY_ID": "wrong-id", "B2_APPLICATION_KEY": "wrong-key"}):
            self.store = assets.B2Store({"bucket": "test-bucket", "prefix": "project"}, self.root)

    def test_real_sdk_upload_verify_reuse_and_download_by_immutable_id(self):
        path = self.root / "source"
        path.write_bytes(b"original Blender bytes")
        expected = assets.fingerprint(path)
        entry = self.store.ensure(path, expected)
        self.assertEqual(self.store.ensure(path, expected), entry)
        self.assertEqual(len(list(self.bucket.ls(recursive=True, latest_only=False))), 1)
        # Simulate someone overwriting the same B2 name externally.
        self.bucket.upload_bytes(b"new bytes", entry["key"])
        destination = self.root / "restored"
        self.store.download(entry, destination)
        self.assertEqual(destination.read_bytes(), path.read_bytes())
        with self.assertRaisesRegex(assets.AssetError, "metadata mismatch"):
            self.store.ensure(path, expected)

    def test_permission_failure_does_not_fall_back_to_upload(self):
        from b2sdk.v2.exception import Unauthorized
        path = self.root / "source"
        path.write_bytes(b"asset")
        with patch.object(self.store.bucket, "get_file_info_by_name", side_effect=Unauthorized("denied", "unauthorized")), \
                patch.object(self.store.bucket, "upload_local_file") as upload:
            with self.assertRaisesRegex(assets.AssetError, "verification failed"):
                self.store.ensure(path, assets.fingerprint(path))
            upload.assert_not_called()

    def test_sdk_multipart_upload_roundtrip(self):
        from b2sdk.v2 import RawSimulator
        path = self.root / "large-source"
        path.write_bytes(b"x" * (RawSimulator.MIN_PART_SIZE * 3 + 1))
        raw = self.api.session.raw_api
        with patch.object(raw, "start_large_file", wraps=raw.start_large_file) as multipart:
            entry = self.store.ensure(path, assets.fingerprint(path))
            multipart.assert_called_once()
        destination = self.root / "large-restored"
        self.store.download(entry, destination)
        self.assertEqual(assets.fingerprint(destination), assets.fingerprint(path))

    def test_missing_credentials_file_does_not_fall_back_to_environment(self):
        self.credentials_path.unlink()
        with patch("b2sdk.v2.B2Api") as api, patch.dict(os.environ, {
                "B2_APPLICATION_KEY_ID": "environment-id", "B2_APPLICATION_KEY": "environment-key"}):
            with self.assertRaisesRegex(assets.AssetError, "Create .assets-local/b2.json"):
                assets.B2Store({"bucket": "test-bucket", "prefix": "project"}, self.root)
            api.assert_not_called()

    def test_invalid_credentials_fail_without_exposing_values(self):
        for value in ([], {}, {"application_key_id": "", "application_key": "test-secret-value"},
                      {"application_key_id": 123, "application_key": "test-secret-value"}):
            with self.subTest(value_type=type(value).__name__):
                assets.write_json(self.credentials_path, value)
                with patch("b2sdk.v2.B2Api") as api:
                    with self.assertRaises(assets.AssetError) as raised:
                        assets.B2Store({"bucket": "test-bucket", "prefix": "project"}, self.root)
                    self.assertNotIn("test-secret-value", str(raised.exception))
                    api.assert_not_called()

    def test_malformed_credentials_json_does_not_expose_content(self):
        self.credentials_path.write_text('{"application_key": "test-secret-value"')
        with self.assertRaisesRegex(assets.AssetError, "Cannot read JSON: b2.json") as raised:
            assets.B2Store({"bucket": "test-bucket", "prefix": "project"}, self.root)
        self.assertNotIn("test-secret-value", str(raised.exception))

    def test_credentials_symlink_is_rejected(self):
        target = self.root / "other.json"
        self.credentials_path.rename(target)
        self.credentials_path.symlink_to(target)
        with self.assertRaisesRegex(assets.AssetError, "Symlinks"):
            assets.B2Store({"bucket": "test-bucket", "prefix": "project"}, self.root)


if __name__ == "__main__":
    unittest.main()
