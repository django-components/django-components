from django_components.commands.create import CreateCommand


# TODO_REMOVE_IN_V1 - Superseded by `components create`
class StartComponentCommand(CreateCommand):
    """**Deprecated**. Use [`components create`](commands.md#components-create) instead."""

    name = "startcomponent"
    help = "Deprecated. Use `components create` instead."
