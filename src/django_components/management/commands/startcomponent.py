from django_components.commands.startcomponent import StartComponentCommand
from django_components.compat.django import load_as_django_command

# TODO_V3
Command = load_as_django_command(StartComponentCommand)
