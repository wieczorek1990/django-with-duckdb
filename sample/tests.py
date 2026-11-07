import datetime
import decimal
import uuid

from django.apps import apps
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, connection, models, transaction
from django.db.models import Count
from django.test import TestCase, TransactionTestCase

from sample.models import (
    AutoFieldModel,
    BigAutoFieldModel,
    BigIntegerFieldModel,
    BinaryFieldModel,
    BooleanFieldModel,
    CharFieldModel,
    DateFieldModel,
    DateTimeFieldModel,
    DecimalFieldModel,
    DurationFieldModel,
    FileFieldModel,
    FilePathFieldModel,
    FloatFieldModel,
    GenericIPAddressFieldModel,
    IntegerFieldModel,
    JSONFieldModel,
    PositiveBigIntegerFieldModel,
    PositiveIntegerFieldModel,
    PositiveSmallIntegerFieldModel,
    SlugFieldModel,
    SmallAutoFieldModel,
    SmallIntegerFieldModel,
    TextFieldModel,
    TimeFieldModel,
    UUIDFieldModel,
)


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


class GroupPermissionModelTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            password="secret-1",
            first_name="Alice",
            last_name="Smith",
        )
        self.editors = Group.objects.create(name="editors")
        self.add_user_perm = Permission.objects.get(
            codename="add_user", content_type__app_label="auth"
        )

    def test_user_str_and_full_name(self):
        self.assertEqual(str(self.alice), "alice")
        self.assertEqual(self.alice.get_full_name(), "Alice Smith")

    def test_user_can_join_group_idempotently(self):
        self.alice.groups.add(self.editors)
        self.alice.groups.add(self.editors)
        self.assertEqual(self.alice.groups.count(), 1)
        self.assertIn(self.alice, self.editors.user_set.all())

    def test_filter_users_by_group_name(self):
        self.alice.groups.add(self.editors)
        User.objects.create_user(username="bob", password="secret-2")
        names = list(
            User.objects.filter(groups__name="editors").values_list(
                "username", flat=True
            )
        )
        self.assertEqual(names, ["alice"])

    def test_group_member_count_annotation(self):
        self.alice.groups.add(self.editors)
        group = Group.objects.annotate(members=Count("user")).get(name="editors")
        self.assertEqual(group.members, 1)

    def test_group_permission_is_granted_to_member(self):
        self.editors.permissions.add(self.add_user_perm)
        self.alice.groups.add(self.editors)
        user = User.objects.get(pk=self.alice.pk)
        self.assertTrue(user.has_perm("auth.add_user"))
        self.assertFalse(user.has_perm("auth.delete_user"))

    def test_removing_membership_revokes_group_permission(self):
        self.editors.permissions.add(self.add_user_perm)
        self.alice.groups.add(self.editors)
        self.alice.groups.remove(self.editors)
        user = User.objects.get(pk=self.alice.pk)
        self.assertFalse(user.has_perm("auth.add_user"))

    def test_direct_user_permission_is_granted(self):
        self.alice.user_permissions.add(self.add_user_perm)
        user = User.objects.get(pk=self.alice.pk)
        self.assertTrue(user.has_perm("auth.add_user"))
        self.assertIn(self.add_user_perm, user.user_permissions.all())

    def test_deleting_group_keeps_user(self):
        self.alice.groups.add(self.editors)
        self.editors.delete()
        self.assertTrue(User.objects.filter(pk=self.alice.pk).exists())
        self.assertEqual(User.objects.get(pk=self.alice.pk).groups.count(), 0)

    def test_permission_belongs_to_expected_content_type(self):
        self.assertEqual(self.add_user_perm.codename, "add_user")
        self.assertEqual(self.add_user_perm.content_type.app_label, "auth")
        self.assertEqual(self.add_user_perm.content_type.model, "user")
        self.assertIs(self.add_user_perm.content_type.model_class(), User)

    def test_content_type_lookup_for_user_model(self):
        content_type = ContentType.objects.get_for_model(User)
        self.assertEqual(content_type.app_label, "auth")
        self.assertEqual(content_type.model, "user")


class TransactionTests(TransactionTestCase):
    def test_group_name_is_unique(self):
        Group.objects.create(name="editors")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Group.objects.create(name="editors")
        self.assertEqual(Group.objects.filter(name="editors").count(), 1)

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


class ModelConstructionTests(TestCase):
    FIELD_MODEL_CASES = [
        (AutoFieldModel, models.AutoField, "id", 1),
        (BigAutoFieldModel, models.BigAutoField, "id", 2),
        (SmallAutoFieldModel, models.SmallAutoField, "id", 3),
        (BinaryFieldModel, models.BinaryField, "value", b"\x00\x01"),
        (BooleanFieldModel, models.BooleanField, "value", True),
        (CharFieldModel, models.CharField, "value", "hello"),
        (DateFieldModel, models.DateField, "value", datetime.date(2026, 11, 7)),
        (
            DateTimeFieldModel,
            models.DateTimeField,
            "value",
            datetime.datetime(2026, 11, 7, 11, 33, tzinfo=datetime.timezone.utc),
        ),
        (DecimalFieldModel, models.DecimalField, "value", decimal.Decimal("12.34")),
        (DurationFieldModel, models.DurationField, "value", datetime.timedelta(days=1)),
        (FileFieldModel, models.FileField, "value", "uploads/readme.txt"),
        (FilePathFieldModel, models.FilePathField, "value", "tests.py"),
        (FloatFieldModel, models.FloatField, "value", 1.5),
        (GenericIPAddressFieldModel, models.GenericIPAddressField, "value", "::1"),
        (IntegerFieldModel, models.IntegerField, "value", -5),
        (BigIntegerFieldModel, models.BigIntegerField, "value", 2**40),
        (SmallIntegerFieldModel, models.SmallIntegerField, "value", -7),
        (PositiveBigIntegerFieldModel, models.PositiveBigIntegerField, "value", 2**40),
        (PositiveIntegerFieldModel, models.PositiveIntegerField, "value", 5),
        (PositiveSmallIntegerFieldModel, models.PositiveSmallIntegerField, "value", 6),
        (JSONFieldModel, models.JSONField, "value", {"key": ["a", 1]}),
        (SlugFieldModel, models.SlugField, "value", "my-slug"),
        (TextFieldModel, models.TextField, "value", "long text"),
        (TimeFieldModel, models.TimeField, "value", datetime.time(11, 33)),
        (UUIDFieldModel, models.UUIDField, "value", uuid.UUID(int=1)),
    ]

    def test_every_model_can_be_constructed(self):
        for model, field_class, attr, value in self.FIELD_MODEL_CASES:
            with self.subTest(model=model.__name__):
                instance = model(**{attr: value})
                self.assertIsInstance(instance, model)
                self.assertIsInstance(model._meta.get_field(attr), field_class)
                self.assertEqual(getattr(instance, attr), value)

    def test_unsaved_model_has_no_primary_key(self):
        for model, _, _, _ in self.FIELD_MODEL_CASES:
            with self.subTest(model=model.__name__):
                self.assertIsNone(model().pk)

    def test_every_backend_field_type_has_a_model(self):
        covered = {field_class.__name__ for _, field_class, _, _ in self.FIELD_MODEL_CASES}
        expected = set(connection.data_types) - {"IPAddressField"}
        self.assertEqual(covered, expected)
