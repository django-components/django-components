from django_components.commands.components import ComponentsRootCommand
from django_components.compat.django import load_as_django_command

# TODO_V3
Command = load_as_django_command(ComponentsRootCommand)
