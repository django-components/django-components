from django_components.autodiscovery import autodiscover, import_libraries
from django_components.extension import ComponentExtension, OnExtensionCreatedContext


class AutodiscoveryExtension(ComponentExtension):
    """
    Built-in extension that handles component autodiscovery and library imports.

    This extension is always loaded and runs during Django startup to:
    - Import modules specified in `COMPONENTS.libraries`
    - Run autodiscovery if `COMPONENTS.autodiscover` is enabled
    """

    name = "autodiscovery"

    def on_extension_created(self, ctx: OnExtensionCreatedContext) -> None:  # noqa: ARG002
        """Import libraries and run autodiscovery as configured in settings."""
        # Import app_settings here to avoid circular import issues
        from django_components.app_settings import app_settings  # noqa: PLC0415

        # Import modules set in `COMPONENTS.libraries` setting
        import_libraries()

        # Run autodiscovery if enabled
        if app_settings.AUTODISCOVER:
            autodiscover()
