from django.db.models.sql.compiler import (
    SQLAggregateCompiler,
    SQLCompiler,
    SQLDeleteCompiler,
)
from django.db.models.sql.compiler import (  # noqa
    SQLInsertCompiler as BaseSQLInsertCompiler,
)
from django.db.models.sql.compiler import (  # noqa
    SQLUpdateCompiler as BaseSQLUpdateCompiler,
)

SQLCompiler = SQLCompiler
SQLDeleteCompiler = SQLDeleteCompiler
SQLAggregateCompiler = SQLAggregateCompiler


class ReadonlySQLCompilerMixin:
    @property
    def readonly_field_names(self):
        try:
            readonly_meta = getattr(self.query.model, "ReadonlyMeta")
        except AttributeError:
            return ()
        else:
            fields = getattr(readonly_meta, "_cached_readonly", None)
            if not fields:
                readonly_meta._cached_readonly = fields = frozenset(
                    getattr(readonly_meta, "readonly", ())
                )
            return fields

    def as_sql(self):
        readonly_field_names = self.readonly_field_names
        if readonly_field_names:
            self.remove_readonly_fields(readonly_field_names)
        return super().as_sql()


class SQLUpdateCompiler(ReadonlySQLCompilerMixin, BaseSQLUpdateCompiler):
    def remove_readonly_fields(self, readonly_field_names):
        """
        Remove the values from the query which correspond to a
        readonly field
        """
        values = self.query.values

        # The tuple is (field, model, value) where model if used for FKs.
        values[:] = (
            (field, _, __)
            for (field, _, __) in values
            if field.name not in readonly_field_names
        )


class SQLInsertCompiler(ReadonlySQLCompilerMixin, BaseSQLInsertCompiler):
    def _exclude_readonly_fields(self, fields, readonly_field_names):
        for field in fields:
            if field.name not in readonly_field_names:
                yield field

    def remove_readonly_fields(self, readonly_field_names):
        """
        Remove the fields from the query which correspond to a
        readonly field
        """
        fields = self.query.fields

        try:
            fields[:] = self._exclude_readonly_fields(fields, readonly_field_names)
        except AttributeError:
            # When deserializing, we might get an attribute error because this
            # list shoud be copied first :

            # "AttributeError: The return type of 'local_concrete_fields'
            # should never be mutated. If you want to manipulate this list for
            # your own use, make a copy first."

            self.query.fields = list(
                self._exclude_readonly_fields(fields, readonly_field_names)
            )
