from django.apps import apps
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, connection, transaction
from django.db.models import Count
from django.test import TestCase, TransactionTestCase


class SampleProjectSetupTests(TestCase):
    def test_sample_app_is_installed(self):
        self.assertTrue(apps.is_installed("sample"))

    def test_connection_uses_duckdb_backend(self):
        self.assertEqual(connection.vendor, "duckdb")

    def test_database_version_is_reported(self):
        version = connection.get_database_version()
        self.assertIsInstance(version, tuple)
        self.assertGreaterEqual(version[0], 1)

    def test_auth_tables_exist(self):
        self.assertIn("auth_user", connection.introspection.table_names())
        self.assertIn("django_content_type", connection.introspection.table_names())

    def test_post_migrate_creates_content_types_and_permissions(self):
        self.assertTrue(
            ContentType.objects.filter(app_label="auth", model="user").exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                codename="add_user", content_type__app_label="auth"
            ).exists()
        )


class UserOrmTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="secret-1")
        self.bob = User.objects.create_user(username="bob", password="secret-2")

    def test_create_user_assigns_primary_key(self):
        self.assertIsNotNone(self.alice.pk)
        self.assertNotEqual(self.alice.pk, self.bob.pk)

    def test_get_returns_created_user(self):
        user = User.objects.get(username="alice")
        self.assertEqual(user.pk, self.alice.pk)
        self.assertEqual(user.username, "alice")

    def test_password_is_hashed_and_checkable(self):
        user = User.objects.get(username="alice")
        self.assertNotEqual(user.password, "secret-1")
        self.assertTrue(user.check_password("secret-1"))
        self.assertFalse(user.check_password("wrong"))

    def test_filter_and_count(self):
        self.assertEqual(User.objects.filter(username__startswith="b").count(), 1)
        self.assertEqual(User.objects.count(), 2)

    def test_update_persists_changes(self):
        User.objects.filter(pk=self.bob.pk).update(first_name="Robert")
        self.assertEqual(User.objects.get(pk=self.bob.pk).first_name, "Robert")

    def test_save_updates_existing_row(self):
        self.alice.email = "alice@example.com"
        self.alice.save()
        self.assertEqual(User.objects.get(pk=self.alice.pk).email, "alice@example.com")
        self.assertEqual(User.objects.count(), 2)

    def test_delete_removes_row(self):
        self.bob.delete()
        self.assertFalse(User.objects.filter(username="bob").exists())
        self.assertEqual(User.objects.count(), 1)

    def test_ordering_and_values_list(self):
        names = list(
            User.objects.order_by("username").values_list("username", flat=True)
        )
        self.assertEqual(names, ["alice", "bob"])

    def test_aggregate_count_grouped_by_active_flag(self):
        User.objects.filter(pk=self.bob.pk).update(is_active=False)
        rows = (
            User.objects.values("is_active")
            .annotate(total=Count("id"))
            .order_by("is_active")
        )
        result = {row["is_active"]: row["total"] for row in rows}
        self.assertEqual(result, {False: 1, True: 1})

    def test_bulk_create(self):
        User.objects.bulk_create([User(username=f"user{i}") for i in range(5)])
        self.assertEqual(User.objects.count(), 7)
        self.assertEqual(User.objects.filter(username__startswith="user").count(), 5)


class TransactionTests(TransactionTestCase):
    def test_unique_username_is_enforced(self):
        User.objects.create_user(username="alice", password="x")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username="alice", password="other")
        self.assertEqual(User.objects.filter(username="alice").count(), 1)

    def test_atomic_block_rolls_back_on_exception(self):
        class Boom(Exception):
            pass

        with self.assertRaises(Boom):
            with transaction.atomic():
                User.objects.create_user(username="ghost", password="x")
                raise Boom()
        self.assertFalse(User.objects.filter(username="ghost").exists())

    def test_atomic_block_commits_on_success(self):
        with transaction.atomic():
            User.objects.create_user(username="committed", password="x")
        self.assertTrue(User.objects.filter(username="committed").exists())
