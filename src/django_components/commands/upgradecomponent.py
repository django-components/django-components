from django_components.commands.upgrade import UpgradeCommand


# TODO_REMOVE_IN_V1 - No longer needed?
class UpgradeComponentCommand(UpgradeCommand):
    """**Deprecated**. Use [`components upgrade`](../commands#components-upgrade) instead."""

    name = "upgradecomponent"
    help = "Deprecated. Use `components upgrade` instead."
