from django.db import models


class AutoFieldModel(models.Model):
    id = models.AutoField(primary_key=True)


class BigAutoFieldModel(models.Model):
    id = models.BigAutoField(primary_key=True)


class SmallAutoFieldModel(models.Model):
    id = models.SmallAutoField(primary_key=True)


class BinaryFieldModel(models.Model):
    value = models.BinaryField()


class BooleanFieldModel(models.Model):
    value = models.BooleanField()


class CharFieldModel(models.Model):
    value = models.CharField(max_length=100)


class DateFieldModel(models.Model):
    value = models.DateField()


class DateTimeFieldModel(models.Model):
    value = models.DateTimeField()


class DecimalFieldModel(models.Model):
    value = models.DecimalField(max_digits=10, decimal_places=2)


class DurationFieldModel(models.Model):
    value = models.DurationField()


class FileFieldModel(models.Model):
    value = models.FileField(upload_to="uploads/", max_length=255)


class FilePathFieldModel(models.Model):
    value = models.FilePathField(path=".", max_length=255)


class FloatFieldModel(models.Model):
    value = models.FloatField()


class IntegerFieldModel(models.Model):
    value = models.IntegerField()


class BigIntegerFieldModel(models.Model):
    value = models.BigIntegerField()


class SmallIntegerFieldModel(models.Model):
    value = models.SmallIntegerField()


class PositiveBigIntegerFieldModel(models.Model):
    value = models.PositiveBigIntegerField()


class PositiveIntegerFieldModel(models.Model):
    value = models.PositiveIntegerField()


class PositiveSmallIntegerFieldModel(models.Model):
    value = models.PositiveSmallIntegerField()


class GenericIPAddressFieldModel(models.Model):
    value = models.GenericIPAddressField()


class JSONFieldModel(models.Model):
    value = models.JSONField()


class SlugFieldModel(models.Model):
    value = models.SlugField(max_length=50)


class TextFieldModel(models.Model):
    value = models.TextField()


class TimeFieldModel(models.Model):
    value = models.TimeField()


class UUIDFieldModel(models.Model):
    value = models.UUIDField()
