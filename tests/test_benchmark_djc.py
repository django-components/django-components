# NOTE: This file is used for benchmarking. Before editing this file,
# please read through these:
# - `benchmarks/README`
# - https://github.com/django-components/django-components/pull/999

import difflib
import json
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field, MISSING
from enum import Enum
from inspect import signature
from itertools import chain
from pathlib import Path
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

import django
from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.middleware import csrf
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.template.defaulttags import register as default_library

from django_components import Component, registry, register, types


# DO NOT REMOVE - See https://github.com/django-components/django-components/pull/999
# ----------- IMPORTS END ------------ #

# This variable is overridden by the benchmark runner
CONTEXT_MODE: Literal["django", "isolated"] = "isolated"

if not settings.configured:
    settings.configure(
        BASE_DIR=Path(__file__).resolve().parent,
        INSTALLED_APPS=["django_components"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    "tests/templates/",
                    "tests/components/",  # Required for template relative imports in tests
                ],
                "OPTIONS": {
                    "builtins": [
                        "django_components.templatetags.component_tags",
                    ]
                },
            }
        ],
        COMPONENTS={
            "autodiscover": False,
            "context_behavior": CONTEXT_MODE,
        },
        MIDDLEWARE=[],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        SECRET_KEY="secret",
        ROOT_URLCONF="django_components.urls",
    )
    django.setup()
else:
    settings.COMPONENTS["context_behavior"] = CONTEXT_MODE

#####################################
# RENDER ENTRYPOINT
#####################################

def gen_render_data():
    data = load_project_data_from_json(data_json)

    # Generate Request and User
    users = data.pop("users")
    user = users[0]

    bookmarks: List[ProjectBookmark] = [
        {
            "id": 82,
            "project": data["project"],
            "text": "Test bookmark",
            "url": "http://localhost:8000/bookmarks/9/create",
            "attachment": None,
        }
    ]

    request = HttpRequest()
    request.user = user
    request.method = "GET"
    request.path = "/projects/1"

    data["layout_data"] = ProjectLayoutData(
        bookmarks=bookmarks,
        project=data["project"],
        active_projects=[data["project"]],
        request=request,
    )

    return data


def render(data):
    result = ProjectPage.render(kwargs=data)
    return result


#####################################
# DATA
#####################################

data_json = """
{
  "project": {
    "pk": 1,
    "fields": {
      "name": "Project Name",
      "organization": 1,
      "status": "INPROGRESS",
      "start_date": "2022-02-06",
      "end_date": "2024-02-07"
    }
  },
  "project_tags": [],
  "phases": [
    {
      "pk": 8,
      "fields": {
        "project": 1,
        "phase_template": 3
      }
    },
    {
      "pk": 7,
      "fields": {
        "project": 1,
        "phase_template": 4
      }
    },
    {
      "pk": 6,
      "fields": {
        "project": 1,
        "phase_template": 5
      }
    },
    {
      "pk": 5,
      "fields": {
        "project": 1,
        "phase_template": 6
      }
    },
    {
      "pk": 4,
      "fields": {
        "project": 1,
        "phase_template": 2
      }
    }
  ],
  "notes_1": [
    {
      "pk": 1,
      "fields": {
        "created": "2025-02-07T08:59:58.689Z",
        "modified": "2025-02-07T08:59:58.689Z",
        "project": 1,
        "text": "Test note 1"
      }
    },
    {
      "pk": 2,
      "fields": {
        "created": "2025-02-07T08:59:58.689Z",
        "modified": "2025-02-07T08:59:58.689Z",
        "project": 1,
        "text": "Test note 2"
      }
    }
  ],
  "comments_by_notes_1": {
    "1": [
      {
        "pk": 3,
        "fields": {
          "parent": 1,
          "notes": "Test note one two three",
          "modified_by": 1
        }
      },
      {
        "pk": 4,
        "fields": {
          "parent": 1,
          "notes": "Test note 2",
          "modified_by": 1
        }
      }
    ]
  },
  "notes_2": [
    {
      "pk": 1,
      "fields": {
        "created": "2024-02-07T11:20:49.085Z",
        "modified": "2024-02-07T11:20:55.003Z",
        "project": 1,
        "text": "Test note x"
      }
    }
  ],
  "comments_by_notes_2": {
    "1": [
      {
        "pk": 1,
        "fields": {
          "parent": 1,
          "text": "Test note 6",
          "modified_by": 1
        }
      },
      {
        "pk": 2,
        "fields": {
          "parent": 1,
          "text": "Test note 5",
          "modified_by": 1
        }
      },
      {
        "pk": 4,
        "fields": {
          "parent": 1,
          "text": "Test note 4",
          "modified_by": 1
        }
      },
      {
        "pk": 6,
        "fields": {
          "parent": 1,
          "text": "Test note 3",
          "modified_by": 1
        }
      }
    ]
  },
  "notes_3": [
    {
      "pk": 2,
      "fields": {
        "created": "2024-02-07T11:20:49.085Z",
        "modified": "2024-02-07T11:20:55.003Z",
        "project": 1,
        "text": "Test note 2"
      }
    }
  ],
  "comments_by_notes_3": {
    "2": [
      {
        "pk": 1,
        "fields": {
          "parent": 2,
          "text": "Test note 1",
          "modified_by": 1
        }
      },
      {
        "pk": 3,
        "fields": {
          "parent": 2,
          "text": "Test note 0",
          "modified_by": 1
        }
      }
    ]
  },
  "roles_with_users": [
    {
      "pk": 6,
      "fields": {
        "user": 2,
        "project": 1,
        "name": "Assistant"
      }
    },
    {
      "pk": 7,
      "fields": {
        "user": 2,
        "project": 1,
        "name": "Owner"
      }
    }
  ],
  "contacts": [],
  "outputs": [
    [
      {
        "pk": 14,
        "fields": {
          "name": "Lorem ipsum 16",
          "description": "",
          "completed": false,
          "phase": 8,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 15,
        "fields": {
          "name": "Lorem ipsum 15",
          "description": "",
          "completed": false,
          "phase": 8,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 16,
        "fields": {
          "name": "Lorem ipsum 14",
          "description": "",
          "completed": false,
          "phase": 8,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 17,
        "fields": {
          "name": "Lorem ipsum 13",
          "description": "",
          "completed": false,
          "phase": 8,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 18,
        "fields": {
          "name": "Lorem ipsum 12",
          "description": "",
          "completed": true,
          "phase": 4,
          "dependency": null
        }
      },
      [
        [
          {
            "pk": 19,
            "fields": {
              "text": "Test bookmark",
              "url": "http://localhost:8000/create/bookmmarks/9/",
              "created_by": 1,
              "output": 18
            }
          },
          []
        ]
      ],
      []
    ],
    [
      {
        "pk": 20,
        "fields": {
          "name": "Lorem ipsum 11",
          "description": "",
          "completed": false,
          "phase": 7,
          "dependency": 14
        }
      },
      [],
      [
        [
          {
            "pk": 14,
            "fields": {
              "name": "Lorem ipsum 10",
              "description": "",
              "completed": false,
              "phase": 8,
              "dependency": null
            }
          },
          []
        ]
      ]
    ],
    [
      {
        "pk": 21,
        "fields": {
          "name": "Lorem ipsum 9",
          "description": "",
          "completed": false,
          "phase": 7,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 22,
        "fields": {
          "name": "Lorem ipsum 8",
          "description": "",
          "completed": false,
          "phase": 7,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 23,
        "fields": {
          "name": "Lorem ipsum 7",
          "description": "",
          "completed": false,
          "phase": 7,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 24,
        "fields": {
          "name": "Lorem ipsum 6",
          "description": "",
          "completed": false,
          "phase": 7,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 25,
        "fields": {
          "name": "Lorem ipsum 5",
          "description": "",
          "completed": false,
          "phase": 6,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 26,
        "fields": {
          "name": "Lorem ipsum 4",
          "description": "",
          "completed": false,
          "phase": 6,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 27,
        "fields": {
          "name": "Lorem ipsum 3",
          "description": "",
          "completed": false,
          "phase": 5,
          "dependency": null
        }
      },
      [],
      []
    ],
    [
      {
        "pk": 28,
        "fields": {
          "name": "Lorem ipsum 2",
          "description": "",
          "completed": false,
          "phase": 7,
          "dependency": 14
        }
      },
      [],
      [
        [
          {
            "pk": 14,
            "fields": {
              "name": "Lorem ipsum 1",
              "description": "",
              "completed": false,
              "phase": 8,
              "dependency": null
            }
          },
          []
        ]
      ]
    ]
  ],
  "status_updates": [],
  "user_is_project_member": true,
  "user_is_project_owner": true,
  "phase_titles": {
    "PHASE_0": "Phase 0",
    "PHASE_1": "Phase 1",
    "PHASE_2": "Phase 2",
    "PHASE_3": "Phase 3",
    "PHASE_4": "Phase 4",
    "PHASE_5": "Phase 5",
    "LEGACY": "Legacy"
  },
  "users": [
    {
      "pk": 2,
      "fields": {
        "name": "UserName",
        "is_staff": true
      }
    }
  ],
  "organizations": [
    {
      "pk": 1,
      "fields": {
        "created": "2025-02-07T16:27:49.837Z",
        "modified": "2025-02-07T16:27:49.837Z",
        "name": "Org Name"
      }
    }
  ],
  "phase_templates": [
    {
      "pk": 3,
      "fields": {
        "created": "2025-02-07T16:27:49.837Z",
        "modified": "2025-02-07T16:27:49.837Z",
        "name": "Phase 3",
        "description": "## Phase 3",
        "type": "PHASE_3"
      }
    },
    {
      "pk": 4,
      "fields": {
        "created": "2025-02-07T16:27:49.837Z",
        "modified": "2025-02-07T16:27:49.837Z",
        "name": "Phase 2",
        "description": "## Phase 2",
        "type": "PHASE_2"
      }
    },
    {
      "pk": 5,
      "fields": {
        "created": "2025-02-07T16:27:49.837Z",
        "modified": "2025-02-07T16:27:49.837Z",
        "name": "Phase 4",
        "description": "## Phase 4",
        "type": "PHASE_4"
      }
    },
    {
      "pk": 6,
      "fields": {
        "created": "2025-02-07T16:27:49.837Z",
        "modified": "2025-02-07T16:27:49.837Z",
        "name": "Phase 5",
        "description": "## Phase 5",
        "type": "PHASE_5"
      }
    },
    {
      "pk": 2,
      "fields": {
        "created": "2025-02-07T16:27:49.837Z",
        "modified": "2025-02-07T16:27:49.837Z",
        "name": "Phase 1",
        "description": "## Phase 1",
        "type": "PHASE_1"
      }
    }
  ]
}
"""

#####################################
# DATA LOADER
#####################################

def load_project_data_from_json(contents: str) -> dict:
    """
    Loads project data from JSON and resolves references between objects.
    Returns the data with all resolvable references replaced with actual object references.
    """
    data = json.loads(contents)

    # First create lookup tables for objects that will be referenced
    users_by_id = {
        user['pk']: {'id': user['pk'], **user['fields']}
        for user in data.get('users', [])
    }

    def _get_user(user_id: int):
        return users_by_id[user_id] if user_id in users_by_id else data.get('users', [])[0]

    organizations_by_id = {
        org['pk']: {'id': org['pk'], **org['fields']}
        for org in data.get('organizations', [])
    }

    phase_templates_by_id = {
        pt['pk']: {'id': pt['pk'], **pt['fields']}
        for pt in data.get('phase_templates', [])
    }

    # 1. Resolve project's organization reference
    project = {'id': data['project']['pk'], **data['project']['fields']}
    if 'organization' in project:
        org_id = project.pop('organization')  # Remove the ID field
        project['organization'] = organizations_by_id[org_id]  # Add the reference

    # 2. Project tags - no changes needed
    project_tags = data['project_tags']

    # 3. Resolve phases' references
    phases = []
    phases_by_id = {}  # We'll need this for resolving output references later
    for phase_data in data['phases']:
        phase = {'id': phase_data['pk'], **phase_data['fields']}
        if 'project' in phase:
            phase['project'] = project
        if 'phase_template' in phase:
            template_id = phase.pop('phase_template')
            phase['phase_template'] = phase_templates_by_id[template_id]
        phases.append(phase)
        phases_by_id[phase['id']] = phase

    # 4. Resolve notes_1 references
    notes_1 = []
    notes_1_by_id = {}  # We'll need this for resolving notes references
    for note_data in data['notes_1']:
        note = {'id': note_data['pk'], **note_data['fields']}
        if 'project' in note:
            note['project'] = project
        notes_1.append(note)
        notes_1_by_id[note['id']] = note

    # 5. Resolve comments_by_notes_1 references
    comments_by_notes_1 = {}
    for note_id, comments_list in data['comments_by_notes_1'].items():
        resolved_comments = []
        for comment_data in comments_list:
            comment = {'id': comment_data['pk'], **comment_data['fields']}
            if 'modified_by' in comment:
                comment['modified_by'] = _get_user(comment['modified_by'])
            if 'parent' in comment:
                comment['parent'] = notes_1_by_id[comment['parent']]
            resolved_comments.append(comment)
        comments_by_notes_1[note_id] = resolved_comments

    # 6. Resolve notes_2' references
    notes_2 = []
    notes_2_by_id = {}  # We'll need this for resolving notes references
    for note_data in data['notes_2']:
        note = {'id': note_data['pk'], **note_data['fields']}
        if 'project' in note:
            note['project'] = project
        notes_2.append(note)
        notes_2_by_id[note['id']] = note

    # 7. Resolve comments_by_notes_2 references
    comments_by_notes_2 = {}
    for note_id, comments_list in data['comments_by_notes_2'].items():
        resolved_comments = []
        for comment_data in comments_list:
            comment = {'id': comment_data['pk'], **comment_data['fields']}
            if 'modified_by' in comment:
                comment['modified_by'] = _get_user(comment['modified_by'])
            if 'parent' in comment:
                comment['parent'] = notes_2_by_id[comment['parent']]
            resolved_comments.append(comment)
        comments_by_notes_2[note_id] = resolved_comments

    # 8. Resolve notes_3 references
    notes_3 = []
    notes_3_by_id = {}  # We'll need this for resolving notes references
    for note_data in data['notes_3']:
        note = {'id': note_data['pk'], **note_data['fields']}
        if 'project' in note:
            note['project'] = project
        notes_3.append(note)
        notes_3_by_id[note['id']] = note

    # 9. Resolve comments_by_notes_3 references
    comments_by_notes_3 = {}
    for note_id, comments_list in data['comments_by_notes_3'].items():
        resolved_comments = []
        for comment_data in comments_list:
            comment = {'id': comment_data['pk'], **comment_data['fields']}
            if 'modified_by' in comment:
                comment['modified_by'] = _get_user(comment['modified_by'])
            if 'parent' in comment:
                comment['parent'] = notes_3_by_id[comment['parent']]
            resolved_comments.append(comment)
        comments_by_notes_3[note_id] = resolved_comments

    # 10. Resolve roles_with_users references
    roles = []
    for role_data in data['roles_with_users']:
        role = {'id': role_data['pk'], **role_data['fields']}
        if 'project' in role:
            role['project'] = project
        if 'user' in role:
            role['user'] = _get_user(role['user'])
        roles.append(role)

    # 11. Contacts - EMPTY, so no changes needed
    contacts = data['contacts']

    # 12. Resolve outputs references
    resolved_outputs = []
    outputs_by_id = {}  # For resolving dependencies

    # First pass: Create all output objects and build lookup
    for output_tuple in data['outputs']:
        output_data = output_tuple[0]
        output = {'id': output_data['pk'], **output_data['fields']}
        if 'phase' in output:
            output['phase'] = phases_by_id[output['phase']]
        outputs_by_id[output['id']] = output

    # Second pass: Process each output with its attachments and dependencies
    for output_tuple in data['outputs']:
        output_data, attachments_data, dependencies_data = output_tuple
        output = outputs_by_id[output_data['pk']]

        # Process attachments
        resolved_attachments = []
        for attachment_tuple in attachments_data:
            attachment_data = attachment_tuple[0]
            attachment = {'id': attachment_data['pk'], **attachment_data['fields']}
            if 'created_by' in attachment:
                attachment['created_by'] = _get_user(attachment['created_by'])
            if 'output' in attachment:
                attachment['output'] = outputs_by_id[attachment['output']]
            # Keep tags as is
            resolved_attachments.append((attachment, attachment_tuple[1]))

        # Process dependencies
        resolved_dependencies = []
        for dep_tuple in dependencies_data:
            dep_data = dep_tuple[0]
            dep_output = outputs_by_id[dep_data['pk']]
            # Keep the tuple structure but with resolved references
            resolved_dependencies.append((dep_output, dep_tuple[1]))

        resolved_outputs.append((output, resolved_attachments, resolved_dependencies))

    return {
        'project': project,
        'project_tags': project_tags,
        'phases': phases,
        'notes_1': notes_1,
        'comments_by_notes_1': comments_by_notes_1,
        'notes_2': notes_2,
        'comments_by_notes_2': comments_by_notes_2,
        'notes_3': notes_3,
        'comments_by_notes_3': comments_by_notes_3,
        'roles_with_users': roles,
        'contacts': contacts,
        'outputs': resolved_outputs,
        'status_updates': data['status_updates'],
        'user_is_project_member': data['user_is_project_member'],
        'user_is_project_owner': data['user_is_project_owner'],
        'phase_titles': data['phase_titles'],
        'users': data['users'],
    }

#####################################
# TYPES
#####################################

class User(TypedDict):
    id: int
    name: str


class Organization(TypedDict):
    id: int
    name: str


class Project(TypedDict):
    id: int
    name: str
    organization: Organization
    status: str
    start_date: date
    end_date: date


class ProjectRole(TypedDict):
    id: int
    user: User
    project: Project
    name: str


class ProjectBookmark(TypedDict):
    id: int
    project: Project
    text: str
    url: str
    attachment: Optional["ProjectOutputAttachment"]


class ProjectStatusUpdate(TypedDict):
    id: int
    project: Project
    text: str
    modified_by: User
    modified: str


class ProjectContact(TypedDict):
    id: int
    project: Project
    link_id: str
    name: str
    job: str


class PhaseTemplate(TypedDict):
    id: int
    name: str
    description: str
    type: str


class ProjectPhase(TypedDict):
    id: int
    project: Project
    phase_template: PhaseTemplate


class ProjectOutput(TypedDict):
    id: int
    name: str
    description: str
    completed: bool
    phase: ProjectPhase
    dependency: Optional["ProjectOutput"]


class ProjectOutputAttachment(TypedDict):
    id: int
    text: str
    url: str
    created_by: User
    output: ProjectOutput


class ProjectNote(TypedDict):
    id: int
    project: Project
    text: str
    created: str


class ProjectNoteComment(TypedDict):
    id: int
    parent: ProjectNote
    text: str
    modified_by: User
    modified: str


#####################################
# CONSTANTS
#####################################

FORM_SHORT_TEXT_MAX_LEN = 255

# This allows us to compare Enum values against strings
class StrEnum(str, Enum):
    pass


class TagResourceType(StrEnum):
    PROJECT = "PROJECT"
    PROJECT_BOOKMARK = "PROJECT_BOOKMARK"
    PROJECT_OUTPUT = "PROJECT_OUTPUT"
    PROJECT_OUTPUT_ATTACHMENT = "PROJECT_OUTPUT_ATTACHMENT"
    PROJECT_TEMPLATE = "PROJECT_TEMPLATE"

class ProjectPhaseType(StrEnum):
    PHASE_1 = "PHASE_1"
    PHASE_2 = "PHASE_2"
    PHASE_3 = "PHASE_3"
    PHASE_4 = "PHASE_4"
    PHASE_5 = "PHASE_5"

class TagTypeMeta(NamedTuple):
    allowed_values: Tuple[str, ...]


# Additional metadata for Tags
#
# NOTE: We use MappingProxyType as an immutable dict.
#       See https://stackoverflow.com/questions/2703599
TAG_TYPE_META = MappingProxyType(
    {
        TagResourceType.PROJECT: TagTypeMeta(
            allowed_values=(
                "Tag 1",
                "Tag 2",
                "Tag 3",
                "Tag 4",
            ),
        ),
        TagResourceType.PROJECT_BOOKMARK: TagTypeMeta(
            allowed_values=(
                "Tag 5",
                "Tag 6",
                "Tag 7",
                "Tag 8",
            ),
        ),
        TagResourceType.PROJECT_OUTPUT: TagTypeMeta(
            allowed_values=tuple(),
        ),
        TagResourceType.PROJECT_OUTPUT_ATTACHMENT: TagTypeMeta(
            allowed_values=(
                "Tag 9",
                "Tag 10",
                "Tag 11",
                "Tag 12",
                "Tag 13",
                "Tag 14",
                "Tag 15",
                "Tag 16",
                "Tag 17",
                "Tag 18",
                "Tag 19",
                "Tag 20",
            ),
        ),
        TagResourceType.PROJECT_TEMPLATE: TagTypeMeta(
            allowed_values=("Tag 21",),
        ),
    }
)

class ProjectOutputDef(NamedTuple):
    title: str
    description: Optional[str] = None
    dependency: Optional[str] = None


class ProjectPhaseMeta(NamedTuple):
    type: ProjectPhaseType
    outputs: List[ProjectOutputDef]


# This constant decides in which order the project phases are shown,
# as well as what kind of name of description they have.
#
# NOTE: We use MappingProxyType as an immutable dict.
#       See https://stackoverflow.com/questions/2703599
PROJECT_PHASES_META = MappingProxyType(
    {
        ProjectPhaseType.PHASE_1: ProjectPhaseMeta(
            type=ProjectPhaseType.PHASE_1,
            outputs=[
                ProjectOutputDef(title="Lorem ipsum 0"),
            ],
        ),
        ProjectPhaseType.PHASE_2: ProjectPhaseMeta(
            type=ProjectPhaseType.PHASE_2,
            outputs=[
                ProjectOutputDef(title="Lorem ipsum 1"),
                ProjectOutputDef(title="Lorem ipsum 2"),
                ProjectOutputDef(title="Lorem ipsum 3"),
                ProjectOutputDef(title="Lorem ipsum 4"),
            ],
        ),
        ProjectPhaseType.PHASE_3: ProjectPhaseMeta(
            type=ProjectPhaseType.PHASE_3,
            outputs=[
                ProjectOutputDef(
                    title="Lorem ipsum 6",
                    dependency="Lorem ipsum 1",
                ),
                ProjectOutputDef(
                    title="Lorem ipsum 7",
                    dependency="Lorem ipsum 1",
                ),
                ProjectOutputDef(title="Lorem ipsum 8"),
                ProjectOutputDef(title="Lorem ipsum 9"),
                ProjectOutputDef(title="Lorem ipsum 10"),
                ProjectOutputDef(title="Lorem ipsum 11"),
            ],
        ),
        ProjectPhaseType.PHASE_4: ProjectPhaseMeta(
            type=ProjectPhaseType.PHASE_4,
            outputs=[
                ProjectOutputDef(title="Lorem ipsum 12"),
                ProjectOutputDef(title="Lorem ipsum 13"),
            ],
        ),
        ProjectPhaseType.PHASE_5: ProjectPhaseMeta(
            type=ProjectPhaseType.PHASE_5,
            outputs=[
                ProjectOutputDef(title="Lorem ipsum 14"),
            ],
        ),
    }
)

#####################################
# THEME
#####################################

ThemeColor = Literal["default", "error", "success", "alert", "info"]
ThemeVariant = Literal["primary", "secondary"]

VARIANTS = ["primary", "secondary"]

class ThemeStylingUnit(NamedTuple):
    """
    Smallest unit of info, this class defines a specific styling of a specific
    component in a specific state.

    E.g. styling of a disabled "Error" button.
    """

    color: str
    """CSS class(es) specifying color"""
    css: str = ""
    """Other CSS classes not specific to color"""


class ThemeStylingVariant(NamedTuple):
    """
    Collection of styling combinations that are meaningful as a group.

    E.g. all "error" variants - primary, disabled, secondary, ...
    """

    primary: ThemeStylingUnit
    primary_disabled: ThemeStylingUnit
    secondary: ThemeStylingUnit
    secondary_disabled: ThemeStylingUnit


class Theme(NamedTuple):
    """Class for defining a styling and color theme for the app."""

    default: ThemeStylingVariant
    error: ThemeStylingVariant
    alert: ThemeStylingVariant
    success: ThemeStylingVariant
    info: ThemeStylingVariant

    sidebar: str
    sidebar_link: str
    background: str
    tab_active: str
    tab_text_active: str
    tab_text_inactive: str
    check_interactive: str
    check_static: str
    check_outline: str


_secondary_btn_styling = "ring-1 ring-inset"

theme = Theme(
    default=ThemeStylingVariant(
        primary=ThemeStylingUnit(
            color="bg-blue-600 text-white hover:bg-blue-500 focus-visible:outline-blue-600 transition"
        ),
        primary_disabled=ThemeStylingUnit(
            color="bg-blue-300 text-blue-50 focus-visible:outline-blue-600 transition"
        ),
        secondary=ThemeStylingUnit(
            color="bg-white text-gray-800 ring-gray-300 hover:bg-gray-100 focus-visible:outline-gray-600 transition",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-gray-300 ring-gray-300 focus-visible:outline-gray-600 transition",
            css=_secondary_btn_styling,
        ),
    ),
    error=ThemeStylingVariant(
        primary=ThemeStylingUnit(
            color="bg-red-600 text-white hover:bg-red-500 focus-visible:outline-red-600"
        ),
        primary_disabled=ThemeStylingUnit(
            color="bg-red-300 text-white focus-visible:outline-red-600"
        ),
        secondary=ThemeStylingUnit(
            color="bg-white text-red-600 ring-red-300 hover:bg-red-100 focus-visible:outline-red-600",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-red-200 ring-red-100 focus-visible:outline-red-600",
            css=_secondary_btn_styling,
        ),
    ),
    alert=ThemeStylingVariant(
        primary=ThemeStylingUnit(
            color="bg-amber-500 text-white hover:bg-amber-400 focus-visible:outline-amber-500"
        ),
        primary_disabled=ThemeStylingUnit(
            color="bg-amber-100 text-orange-300 focus-visible:outline-amber-500"
        ),
        secondary=ThemeStylingUnit(
            color="bg-white text-amber-500 ring-amber-300 hover:bg-amber-100 focus-visible:outline-amber-500",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-orange-200 ring-amber-100 focus-visible:outline-amber-500",
            css=_secondary_btn_styling,
        ),
    ),
    success=ThemeStylingVariant(
        primary=ThemeStylingUnit(
            color="bg-green-600 text-white hover:bg-green-500 focus-visible:outline-green-600"
        ),
        primary_disabled=ThemeStylingUnit(
            color="bg-green-300 text-white focus-visible:outline-green-600"
        ),
        secondary=ThemeStylingUnit(
            color="bg-white text-green-600 ring-green-300 hover:bg-green-100 focus-visible:outline-green-600",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-green-200 ring-green-100 focus-visible:outline-green-600",
            css=_secondary_btn_styling,
        ),
    ),
    info=ThemeStylingVariant(
        primary=ThemeStylingUnit(
            color="bg-sky-600 text-white hover:bg-sky-500 focus-visible:outline-sky-600"
        ),
        primary_disabled=ThemeStylingUnit(
            color="bg-sky-300 text-white focus-visible:outline-sky-600"
        ),
        secondary=ThemeStylingUnit(
            color="bg-white text-sky-600 ring-sky-300 hover:bg-sky-100 focus-visible:outline-sky-600",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-sky-200 ring-sky-100 focus-visible:outline-sky-600",
            css=_secondary_btn_styling,
        ),
    ),
    sidebar="bg-neutral-900 text-neutral-200",
    sidebar_link="hover:bg-neutral-700 hover:text-white transition",
    background="bg-neutral-200",
    tab_active="border-blue-700",
    tab_text_active="text-blue-700",
    tab_text_inactive="text-gray-500 hover:text-blue-700",
    check_interactive="bg-blue-600 group-hover:bg-blue-500 transition",
    check_static="bg-blue-600",
    check_outline="border-2 border-blue-600 bg-white",
)


def get_styling_css(
    variant: Optional["ThemeVariant"] = None,
    color: Optional["ThemeColor"] = None,
    disabled: Optional[bool] = None,
):
    """
    Dynamically access CSS styling classes for a specific variant and state.

    E.g. following two calls get styling classes for:
    1. Secondary error state
    1. Secondary alert disabled state
    2. Primary default disabled state
    ```py
    get_styling_css('secondary', 'error')
    get_styling_css('secondary', 'alert', disabled=True)
    get_styling_css(disabled=True)
    ```
    """
    variant = variant or "primary"
    color = color or "default"
    disabled = disabled if disabled is not None else False

    color_variants: ThemeStylingVariant = getattr(theme, color)

    if variant not in VARIANTS:
        raise ValueError(
            f'Unknown theme variant "{variant}", must be one of {VARIANTS}'
        )

    variant_name = variant if not disabled else f"{variant}_disabled"
    styling: ThemeStylingUnit = getattr(color_variants, variant_name)

    css = f"{styling.color} {styling.css}".strip()
    return css


#####################################
# HELPERS
#####################################

T = TypeVar("T")
U = TypeVar("U")

def format_timestamp(timestamp: datetime):
    """
    If the timestamp is more than 7 days ago, format it as "Jan 1, 2025".
    Otherwise, format it as a natural time string (e.g. "3 days ago").
    """
    if now() - timestamp > timedelta(days=7):
        return timestamp.strftime("%b %-d, %Y")
    else:
        return naturaltime(timestamp)

def group_by(
    lst: Iterable[T],
    keyfn: Callable[[T, int], Any],
    mapper: Optional[Callable[[T, int], U]] = None,
):
    """
    Given a list, generates a key for each item in the list using the `keyfn`.

    Returns a dictionary of generated keys, where each value is a list of corresponding
    items.

    Similar to Lodash's `groupby`.

    Optionally map the values in the lists with `mapper`.
    """
    grouped: Dict[Any, List[Union[U, T]]] = {}
    for index, item in enumerate(lst):
        key = dynamic_apply(keyfn, item, index)
        if key not in grouped:
            grouped[key] = []

        mapped_item = dynamic_apply(mapper, item, index) if mapper else item
        grouped[key].append(mapped_item)
    return grouped

def dynamic_apply(fn: Callable, *args):
    """
    Given a function and positional arguments that should be applied to given function,
    this helper will apply only as many arguments as the function defines, or only
    as much as the number of arguments that we can apply.
    """
    mapper_args_count = len(signature(fn).parameters)
    num_args_to_apply = min(mapper_args_count, len(args))
    first_n_args = args[:num_args_to_apply]

    return fn(*first_n_args)

#####################################
# SHARED FORMS
#####################################

class ConditionalEditForm(forms.Form):
    """
    Subclass of Django's Form that sets all fields as NON-editable based
    on the `editable` field.
    """

    editable: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.editable is not None and not self.editable:
            self._disable_all_form_fields()

    def _disable_all_form_fields(self):
        fields: Dict[str, forms.Field] = self.fields  # type: ignore[assignment]
        for form_field in fields.values():
            form_field.widget.attrs["readonly"] = True

#####################################
# TEMPLATE TAG FILTERS
#####################################

@default_library.filter("alpine")
def to_alpine_json(value: dict):
    """
    Serialize Python object such that it can be passed to Alpine callbacks
    in Django templates.
    """
    # Avoid using double quotes since this value is passed to an HTML element
    # attribute.
    # NOTE: Maybe we could use HTML escaping to avoid the issue with double quotes?
    data = json.dumps(value).replace('"', "'")
    return data

@default_library.filter("json")
def to_json(value: dict):
    """Serialize Python object to JSON."""
    data = json.dumps(value)
    return data

@default_library.simple_tag
def define(val=None):
    return val

@default_library.filter
def get_item(dictionary: dict, key: str):
    return dictionary.get(key)

@default_library.filter("js")
def serialize_to_js(obj):
    """
    Serialize a Python object to a JS-like expression.
    Works recursively with nested dictionaries and lists.

    So given a dict
    `{"a": 123, "b": "console.log('abc')", "c": "'mystring'"}`

    The filter exports:
    `"{ a: 123, b: console.log('abc'), c: 'mystring' }"`
    """
    if isinstance(obj, dict):
        # If the object is a dictionary, iterate through key-value pairs
        items = []
        for key, value in obj.items():
            serialized_value = serialize_to_js(value)  # Recursively serialize the value
            items.append(f"{key}: {serialized_value}")
        return f"{{ {', '.join(items)} }}"

    elif isinstance(obj, (list, tuple)):
        # If the object is a list, recursively serialize each item
        serialized_items = [serialize_to_js(item) for item in obj]
        return f"[{', '.join(serialized_items)}]"

    elif isinstance(obj, str):
        return obj

    else:
        # For other types (int, float, etc.), just return the string representation
        return str(obj)

#####################################
# BUTTON
#####################################

@register("Button")
class Button(Component):
    def get_context_data(
        self,
        /,
        *,
        href: Optional[str] = None,
        link: Optional[bool] = None,
        disabled: Optional[bool] = False,
        variant: Union["ThemeVariant", Literal["plain"]] = "primary",
        color: Union["ThemeColor", str] = "default",
        type: Optional[str] = "button",
        attrs: Optional[dict] = None,
    ):
        common_css = (
            "inline-flex w-full text-sm font-semibold"
            " sm:mt-0 sm:w-auto focus-visible:outline-2 focus-visible:outline-offset-2"
        )
        if variant == "plain":
            all_css_class = common_css
        else:
            button_classes = get_styling_css(variant, color, disabled)  # type: ignore[arg-type]
            all_css_class = (
                f"{button_classes} {common_css} px-3 py-2 justify-center rounded-md shadow-sm"
            )

        is_link = not disabled and (href or link)

        all_attrs = {
            **(attrs or {})
        }
        if disabled:
            all_attrs["aria-disabled"] = "true"

        return {
            "href": href,
            "disabled": disabled,
            "type": type,
            "btn_class": all_css_class,
            "attrs": all_attrs,
            "is_link": is_link,
        }

    template: types.django_html = """
        {# Based on buttons from https://tailwindui.com/components/application-ui/overlays/modals #}

        {% if is_link %}
        <a
            href="{{ href }}"
            {% html_attrs attrs class=btn_class class="no-underline" %}
        >
        {% else %}
        <button
            type="{{ type }}"
            {% if disabled %} disabled {% endif %}
            {% html_attrs attrs class=btn_class %}
        >
        {% endif %}

            {% slot "content" default / %}

        {% if is_link %}
        </a>
        {% else %}
        </button>
        {% endif %}
    """


#####################################
# MENU
#####################################

MaybeNestedList = List[Union[T, List[T]]]
MenuItemGroup = List["MenuItem"]


@dataclass(frozen=True)
class MenuItem:
    """
    Single menu item used with the `menu` components.

    Menu items can be divided by a horizontal line to indicate that the items
    belong together. In code, we specify this by wrapping the item(s) as an array.

    ```py
    menu_items = [
        # Group 1
        [
            MenuItem(value="Edit", link="#"),
            MenuItem(value="Duplicate"),
        ],
        # Group 2
        MenuItem(value="Add step before"),
        MenuItem(value="Add step after"),
        MenuItem(value="Add child step"),
        # Group 3
        [
            MenuItem(value="Delete"),
        ],
    ]
    ```
    """

    value: Any
    """Value of the menu item to render."""

    link: Optional[str] = None
    """
    If set, the menu item will be wrapped in an `<a>` tag pointing to this
    link.
    """

    item_attrs: Optional[dict] = None
    """HTML attributes specific to this menu item."""


@register("Menu")
class Menu(Component):
    def get_context_data(
        self,
        /,
        *,
        items: MaybeNestedList[Union[MenuItem, str]],
        model: Optional[str] = None,
        # CSS and HTML attributes
        attrs: Optional[dict] = None,
        activator_attrs: Optional[dict] = None,
        list_attrs: Optional[dict] = None,
        # UX
        close_on_esc: Optional[bool] = True,
        close_on_click_outside: Optional[bool] = True,
        anchor: Optional[str] = None,
        anchor_dir: Optional[str] = "bottom",
    ):
        is_model_overriden = bool(model)
        model = model or "open"

        all_list_attrs: dict = {}
        if list_attrs:
            all_list_attrs.update(list_attrs)
        if anchor:
            all_list_attrs[f"x-anchor.{anchor_dir}"] = anchor
        all_list_attrs.update({
            "x-show": model,
            "x-cloak": "",
        })

        return {
            "model": model,
            "items": items,
            "is_model_overriden": is_model_overriden,
            "close_on_click_outside": close_on_click_outside,
            "close_on_esc": close_on_esc,
            "activator_attrs": activator_attrs,
            "list_attrs": all_list_attrs,
            "attrs": attrs,
        }

    template: types.django_html = """
        {# Based on https://tailwindui.com/components/application-ui/elements/dropdowns #}

        {% comment %}
        NOTE: {{ model }} is the Alpine variable used for opening/closing. The variable name
            is set dynamically, hence we use Django's double curly braces to refer to it.
        {% endcomment %}
        <div
            {% html_attrs attrs %}
            x-data="{
                'isModelOverriden': {{ is_model_overriden|alpine }},
                'modelName': {{ model|alpine }},
                'closeOnClickOutside': {{ close_on_click_outside|alpine }},

                {% if not is_model_overriden %}
                '{{ model }}': false,
                {% endif %}

                onClickOutside(event) {
                    if (this.closeOnClickOutside) {
                        if (!this.isModelOverriden) {
                            this[this.modelName] = false;
                        }
                        $dispatch('click_outside', { origEvent: event });
                    }
                },
            }"
            {% if close_on_esc %}
                @keydown.escape="{{ model }} = false"
            {% endif %}
        >
            {# This is what opens the modal #}
            {% if component_vars.is_filled.activator or component_vars.is_filled.default %}
                <div
                    @click="{{ model }} = !{{ model }}"
                    @keydown.enter="{{ model }} = !{{ model }}"
                    tabindex="0"
                    aria-haspopup="true"
                    :aria-expanded="!!{{ model }}"
                    x-ref="activator"
                    {% html_attrs activator_attrs %}
                >
                    {% slot "activator" default / %}
                </div>
            {% endif %}

            {% component "MenuList" items=items attrs=list_attrs / %}
        </div>
    """

#####################################
# MENU LIST
#####################################

def _normalize_item(item: Union[MenuItem, str]):
    # Wrap plain value in MenuItem
    if not isinstance(item, MenuItem):
        return MenuItem(value=item)
    return item


# Normalize a list of MenuItems such that they are all in groups. We achieve
# this by collecting consecutive ungrouped items into a single group.
def _normalize_items_to_groups(items: MaybeNestedList[Union[MenuItem, str]]):
    def is_group(item):
        return isinstance(item, Iterable) and not isinstance(item, str)

    groups: List[List[Union[MenuItem, str]]] = []

    curr_group: Optional[List[Union[MenuItem, str]]] = None
    for index, item_or_grp in enumerate(items):
        group: List[Union[MenuItem, str]] = []
        if isinstance(item_or_grp, Iterable) and not isinstance(item_or_grp, str):
            group = item_or_grp
        else:
            if curr_group is not None:
                group = curr_group
            else:
                group = curr_group = []
            group.append(item_or_grp)

            is_not_last = index < len(items) - 1
            if is_not_last and not is_group(items[index + 1]):
                continue
        groups.append(group)
        curr_group = None

    return groups


def prepare_menu_items(items: MaybeNestedList[Union[MenuItem, str]]):
    groups = _normalize_items_to_groups(items)
    normalized_groups: List[MenuItemGroup] = []

    for group in groups:
        norm_group = list(map(_normalize_item, group))
        normalized_groups.append(norm_group)

    return normalized_groups


@register("MenuList")
class MenuList(Component):
    def get_context_data(
        self,
        /,
        *,
        items: MaybeNestedList[Union[MenuItem, str]],
        attrs: Optional[dict] = None,
    ):
        item_groups = prepare_menu_items(items)

        return {
            "item_groups": item_groups,
            "attrs": attrs,
        }

    template: types.django_html = """
        {# Based on https://tailwindui.com/components/application-ui/elements/dropdowns #}
        <div
            role="menu"
            aria-orientation="vertical"
            {% html_attrs attrs class="mt-2 divide-y divide-gray-300 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none" %}
        >
            {% for group in item_groups %}
                <div class="py-1" role="group">
                    {% for item in group %}
                        {% if item.link %}
                            <a
                                role="menuitem"
                                tabindex="0"
                                href="{{ item.link }}"
                                {% html_attrs item.item_attrs class="block" %}
                            >
                                {{ item.value }}
                            </a>
                        {% else %}
                            <div
                                role="menuitem"
                                tabindex="0"
                                {% html_attrs item.item_attrs %}
                            >
                                {{ item.value }}
                            </div>
                        {% endif %}
                    {% endfor %}
                </div>
            {% endfor %}
        </div>
    """  # noqa: E501

#####################################
# TABLE
#####################################

class TableHeader(NamedTuple):
    """Table header data structure used with the `table` components."""

    name: str
    """Header name, as displayed to the users."""

    key: str
    """Dictionary key on `TableRow.cols` that holds data for this header."""

    hidden: Optional[bool] = None
    """
    Whether to hide the header. The column will still be rendered,
    only the column title will be hidden.
    """

    cell_attrs: Optional[dict] = None
    """HTML attributes specific to this table header cell."""


@dataclass(frozen=True)
class TableCell:
    """Single table cell (row + col) used with the `table` components."""

    value: Any
    """Value of the cell to render."""

    colspan: int = 1
    """
    How many columns should this cell occupy.

    See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/td#colspan
    """

    link: Optional[str] = None
    """
    If set, the cell value will be wrapped in an `<a>` tag pointing to this
    link.
    """

    link_attrs: Optional[dict] = None
    """
    HTML attributes for the `<a>` tag wrapping the link, if `link` is set.
    """

    cell_attrs: Optional[dict] = None
    """HTML attributes specific to this table cell."""

    linebreaks: Optional[bool] = None
    """Whether to apply the `linebreaks` filter to this table cell."""

    def __post_init__(self):
        if not isinstance(self.colspan, int) or self.colspan < 1:
            raise ValueError(
                "TableCell.colspan must be a non-negative integer."
                f" Instead got {self.colspan}"
            )


NULL_CELL = TableCell("")
"""Definition of an empty cell"""


@dataclass(frozen=True)
class TableRow:
    """
    Table row data structure used with the `table` components.

    TableRow holds columnar data in the `cols` dict, e.g.:
    ```py
    rows = [
        TableRow(
            cols={
                'name': TableCell(
                    value='My Name',
                    link='https://www.example.com',
                    link_attrs={
                        "class": 'font-weight-bold',
                    },
                ),
                'desc': 'Lorem Ipsum'
            }
        ),
    ]
    ```
    """

    cols: Dict[str, TableCell] = field(default_factory=dict)
    """Data within this row."""

    row_attrs: Optional[dict] = None
    """HTML attributes for this row."""

    col_attrs: Optional[dict] = None
    """
    HTML attributes for each column in this row.

    NOTE: This may be overriden by `TableCell.cell_attrs`.
    """


def create_table_row(
    cols: Optional[Dict[str, Union[TableCell, Any]]] = None,
    row_attrs: Optional[dict] = None,
    col_attrs: Optional[dict] = None,
):
    # Normalize the values of `cols` to `TableCell` instances. This
    # way we allow to set values of `self.cols` dict as plain values, e.g.:
    #
    # ```py
    # create_table_row(
    #     cols={
    #         "my_value": 12
    #     }
    # )
    # ```
    #
    # Instead of having to wrap it in `TableCell` instance, like so:
    #
    # ```py
    # TableRow(
    #     cols={
    #         "my_value": TableCell(value=12)
    #     }
    # )
    # ```
    resolved_cols: Dict[str, TableCell] = {}
    if cols:
        for key, val in cols.items():
            resolved_cols[key] = TableCell(value=val) if not isinstance(val, TableCell) else val

    return TableRow(
        cols=resolved_cols,
        row_attrs=row_attrs,
        col_attrs=col_attrs,
    )


def prepare_row_headers(row: TableRow, headers: List[TableHeader]):
    # Skip headers when cells have colspan > 1, thus merging those cells
    final_row_headers = []
    headers_to_skip = 0
    for header in headers:
        if headers_to_skip > 0:
            headers_to_skip -= 1
            continue

        final_row_headers.append(header)
        cell = row.cols.get(header.key, None)
        if cell is not None:
            headers_to_skip = cell.colspan - 1

    return final_row_headers


@register("Table")
class Table(Component):
    def get_context_data(
        self,
        /,
        *,
        headers: List[TableHeader],
        rows: List[TableRow],
        attrs: Optional[dict] = None,
    ):
        rows_to_render = [
            tuple([row, prepare_row_headers(row, headers)]) for row in rows
        ]

        return {
            "headers": headers,
            "rows_to_render": rows_to_render,
            "NULL_CELL": NULL_CELL,
            "attrs": attrs,
        }

    template: types.django_html = """
        <div {% html_attrs attrs class="flow-root" %}>
            <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                    <table class="min-w-full divide-y divide-gray-300">
                        <thead>
                            <tr>
                                {% for header in headers %}
                                    <th
                                        scope="col"
                                        {% html_attrs
                                            header.cell_attrs
                                            class="text-left text-sm font-semibold text-gray-900 py-3.5"
                                            class="{% if forloop.first %} pl-4 pr-3 sm:pl-0 {% else %} px-3 {% endif %}"
                                        %}
                                    >

                                    {% if header.hidden %}
                                        <span class="sr-only"> {{ header.name }} </span>
                                    {% else %}
                                        {{ header.name }}
                                    {% endif %}

                                    </th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            {% for row, row_headers in rows_to_render %}
                                <tr {% html_attrs row.row_attrs %}>
                                    {% for header in row_headers %}
                                        {% define row.cols|get_item:header.key|default_if_none:NULL_CELL as cell %}

                                        <td
                                            colspan="{{ cell.colspan }}"
                                            {% html_attrs cell.cell_attrs row.col_attrs %}
                                        >

                                        {% if cell.link %}
                                            <a
                                                href="{{ cell.link }}"
                                                {% html_attrs cell.link_attrs %}
                                            >
                                                {% if cell.linebreaks %}
                                                    {{ cell.value | linebreaksbr }}
                                                {% else %}
                                                    {{ cell.value }}
                                                {% endif %}
                                            </a>
                                        {% else %}
                                            {% if cell.linebreaks %}
                                                {{ cell.value | linebreaksbr }}
                                            {% else %}
                                                {{ cell.value }}
                                            {% endif %}
                                        {% endif %}

                                        </td>
                                    {% endfor %}
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    """  # noqa: E501

#####################################
# ICON
#####################################

@register("Icon")
class Icon(Component):
    def get_context_data(
        self,
        /,
        *,
        name: str,
        variant: Optional[str] = None,
        size: Optional[int] = None,
        stroke_width: Optional[float] = None,
        viewbox: Optional[str] = None,
        svg_attrs: Optional[dict] = None,
        # Note: Unlike the underlying icon component, this component uses color CSS classes
        color: Optional[str] = "",
        icon_color: Optional[str] = "",
        text_color: Optional[str] = "",
        href: Optional[str] = None,
        text_attrs: Optional[dict] = None,
        link_attrs: Optional[dict] = None,
        attrs: Optional[dict] = None,
    ):
        # Allow to set icon and text independently, or both at same time via `color` prop
        if not icon_color:
            icon_color = color
        if not text_color:
            text_color = color

        svg_attrs = svg_attrs.copy() if svg_attrs else {}
        if not svg_attrs.get("class"):
            svg_attrs["class"] = ""
        svg_attrs["class"] += f" {icon_color or ''} h-6 w-6 shrink-0"

        return {
            "name": name,
            "variant": variant,
            "size": size,
            "viewbox": viewbox,
            "stroke_width": stroke_width,
            "svg_attrs": svg_attrs,
            "text_color": text_color,
            "text_attrs": text_attrs,
            "link_attrs": link_attrs,
            "href": href,
            "attrs": attrs,
        }

    template: types.django_html = """
        <div {% html_attrs attrs %}>
            {% if href %}
            <a
                href="{{ href }}"
                {% html_attrs
                    link_attrs
                    text_attrs
                    class=text_color
                    class="group flex gap-x-3 rounded-md text-sm leading-6 font-semibold"
                %}
            >
            {% else %}
            <span
                {% html_attrs
                    text_attrs
                    class=text_color
                    class="group flex gap-x-3 rounded-md text-sm leading-6 font-semibold"
                %}
            >
            {% endif %}
                {% component "heroicons"
                    name=name
                    variant=variant
                    size=size
                    viewbox=viewbox
                    stroke_width=stroke_width
                    attrs=svg_attrs
                / %}
                {% slot "content" default / %}

            {% if href %}
            </a>
            {% else %}
            </span>
            {% endif %}
        </div>
    """


#####################################
# HEROICONS
#####################################

# Single hard-coded icon
ICONS = {
    "outline": {
        "academic-cap": [
            {'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'd': 'M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5'}  # noqa: E501
        ]
    }
}


class ComponentDefaultsMeta(type):
    def __new__(mcs, name: str, bases: Tuple, namespace: Dict) -> Type:
        # Apply dataclass decorator to the class
        return dataclass(super().__new__(mcs, name, bases, namespace))


class ComponentDefaults(metaclass=ComponentDefaultsMeta):
    def __post_init__(self) -> None:
        fields = self.__class__.__dataclass_fields__  # type: ignore[attr-defined]
        for field_name, dataclass_field in fields.items():
            if dataclass_field.default is not MISSING:
                if getattr(self, field_name) is None:
                    setattr(self, field_name, dataclass_field.default)


class IconDefaults(ComponentDefaults):
    name: str
    variant: str = "outline"
    size: int = 24
    color: str = "currentColor"
    stroke_width: float = 1.5
    viewbox: str = "0 0 24 24"
    attrs: Optional[Dict] = None


@register("heroicons")
class HeroIcon(Component):
    """The icon component"""

    template: types.django_html = """
        {% load component_tags %}
        <svg {% html_attrs attrs default_attrs %}>
            {% for path_attrs in icon_paths %}
                <path {% html_attrs path_attrs %} />
            {% endfor %}
        </svg>
    """

    def get_context_data(
        self,
        /,
        *,
        name: str,
        variant: Optional[str] = None,
        size: Optional[int] = None,
        color: Optional[str] = None,
        stroke_width: Optional[float] = None,
        viewbox: Optional[str] = None,
        attrs: Optional[Dict] = None,
    ) -> Dict:
        kwargs = IconDefaults(**self.input.kwargs)

        if kwargs.variant not in ["outline", "solid"]:
            raise ValueError(f"Invalid variant: {kwargs.variant}. Must be either 'outline' or 'solid'")

        # variant_icons = ICONS[kwargs.variant]
        variant_icons = ICONS["outline"]
        icon_name = "academic-cap"

        if icon_name not in variant_icons:
            # Give users a helpful message by fuzzy-search the closest key
            msg = ""
            icon_names = list(variant_icons.keys())
            if icon_names:
                fuzzy_matches = difflib.get_close_matches(icon_name, icon_names, n=3, cutoff=0.7)
                if fuzzy_matches:
                    suggestions = ", ".join([f"'{match}'" for match in fuzzy_matches])
                    msg += f". Did you mean any of {suggestions}?"

            raise ValueError(f"Invalid icon name: {icon_name}{msg}")

        icon_paths = variant_icons[icon_name]

        # These are set as "default" attributes, so users can override them
        # by passing them in the `attrs` argument.
        default_attrs: Dict[str, Any] = {
            "viewBox": kwargs.viewbox,
            "style": f"width: {kwargs.size}px; height: {kwargs.size}px",
            "aria-hidden": "true",
        }

        # The SVG applies the color differently in "outline" and "solid" versions
        if kwargs.variant == "outline":
            default_attrs["fill"] = "none"
            default_attrs["stroke"] = kwargs.color
            default_attrs["stroke-width"] = kwargs.stroke_width
        else:
            default_attrs["fill"] = kwargs.color
            default_attrs["stroke"] = "none"

        return {
            "icon_paths": icon_paths,
            "default_attrs": default_attrs,
            "attrs": kwargs.attrs,
        }

#####################################
# EXPANSION PANEL
#####################################

@register("ExpansionPanel")
class ExpansionPanel(Component):
    def get_context_data(
        self,
        /,
        *,
        open: Optional[bool] = False,
        panel_id: Optional[str] = None,
        attrs: Optional[dict] = None,
        header_attrs: Optional[dict] = None,
        content_attrs: Optional[dict] = None,
        icon_position: Literal["left", "right"] = "left",
    ):
        init_data = {"open": open}
        return {
            "attrs": attrs,
            "header_attrs": header_attrs,
            "content_attrs": content_attrs,
            "icon_position": icon_position,
            "init_data": init_data,
            "panel_id": panel_id if panel_id else False,
        }

    template: types.django_html = """
        <div
            x-data="expansion_panel"
            data-init="{{ init_data|json|escape }}"
            {% html_attrs attrs data-panelid=panel_id %}
        >
            <div
                @click="togglePanel"
                {% html_attrs header_attrs class="pb-2 cursor-pointer" %}
            >
                {% if icon_position == "left" %}
                    {% component "Icon"
                        name="chevron-down"
                        variant="outline"
                        attrs:style="width: fit-content;"
                        attrs::class="{ 'rotate-180': isOpen }"
                    / %}
                {% endif %}

                {% slot "header" / %}

                {% if icon_position == "right" %}
                    {% component "Icon"
                        name="chevron-down"
                        variant="outline"
                        attrs:style="width: fit-content;"
                        attrs::class="{ 'rotate-180': isOpen }"
                    / %}
                {% endif %}
            </div>
            <div x-show="isOpen" {% html_attrs content_attrs %}>
                {% slot "content" default / %}
            </div>
        </div>
    """

    js: types.js = """
        document.addEventListener("alpine:init", () => {
            Alpine.data("expansion_panel", () => ({
                // Variables
                isOpen: false,

                // Methods
                init() {
                    const initDataStr = this.$el.dataset.init;
                    const initData = JSON.parse(initDataStr);

                    this.isOpen = initData.open;

                    const panelId = this.$el.dataset.panelid;
                    const panel = new URL(location.href).searchParams.get("panel");

                    if (panel && panel == panelId) {
                        this.isOpen = true;
                        this.$el.scrollIntoView();
                    }
                },

                togglePanel(event) {
                    this.isOpen = !this.isOpen;
                },
            }));
        });
    """

#####################################
# PROJECT_PAGE
#####################################

# Tabs on this page and the query params to open specific tabs on page load.
class ProjectPageTabsToQueryParams(Enum):
    PROJECT_INFO = {"tabs-proj-right": "1"}
    OUTPUTS = {"tabs-proj-right": "5"}


@register("ProjectPage")
class ProjectPage(Component):
    def get_context_data(
        self,
        /,
        *,
        phases: List[ProjectPhase],
        project_tags: List[str],
        notes_1: List[ProjectNote],
        comments_by_notes_1: Dict[str, List[ProjectNoteComment]],
        notes_2: List[ProjectNote],
        comments_by_notes_2: Dict[str, List[ProjectNoteComment]],
        notes_3: List[ProjectNote],
        comments_by_notes_3: Dict[str, List[ProjectNoteComment]],
        status_updates: List[ProjectStatusUpdate],
        roles_with_users: List[ProjectRole],
        contacts: List[ProjectContact],
        outputs: List["OutputWithAttachmentsAndDeps"],
        user_is_project_member: bool,
        user_is_project_owner: bool,
        phase_titles: Dict[ProjectPhaseType, str],
        # Used by project layout
        layout_data: "ProjectLayoutData",
        project: Project,
        breadcrumbs: Optional[List["Breadcrumb"]] = None,
    ):
        rendered_phases: List[ListItem] = []
        phases_by_type = {p['phase_template']['type']: p for p in phases}
        for phase_meta in PROJECT_PHASES_META.values():
            phase = phases_by_type[phase_meta.type]
            title = phase_titles[phase_meta.type]
            rendered_phases.append(
                ListItem(
                    value=title,
                    link=f"/projects/{project['id']}/phases/{phase['phase_template']['type']}",
                )
            )

        redirect_url = f"/projects/{project['id']}"

        return {
            "layout_data": layout_data,
            "project": project,
            "breadcrumbs": breadcrumbs or [],
            "project_tags": project_tags,
            "rendered_phases": rendered_phases,
            "contacts": contacts,
            "notes_1": notes_1,
            "comments_by_notes_1": comments_by_notes_1,
            "notes_2": notes_2,
            "comments_by_notes_2": comments_by_notes_2,
            "notes_3": notes_3,
            "comments_by_notes_3": comments_by_notes_3,
            "status_updates": status_updates,
            "roles_with_users": roles_with_users,
            "outputs": outputs,
            "user_is_project_member": user_is_project_member,
            "user_is_project_owner": user_is_project_owner,
            "project_page_url": redirect_url,
            "phase_titles": phase_titles,
        }

    template: types.django_html = """
        {% component "ProjectLayoutTabbed"
            data=layout_data
            breadcrumbs=breadcrumbs
            top_level_tab_index=1
        %}
            {% fill "header" %}
                <div class="flex pb-6">
                    <div class="flex justify-between gap-x-12">
                        <div class="prose">
                            <h3>{{ project.name }}</h3>
                        </div>
                        <div class="prose font-semibold text-gray-500 pt-1">
                            {{ project.start_date }} - {{ project.end_date }}
                        </div>
                    </div>
                </div>
            {% endfill %}

            {% fill "left_panel" %}
                {% component "List"
                    items=rendered_phases
                    item_attrs:class="py-5"
                / %}
            {% endfill %}

            {% fill "tabs" %}
                {% component "TabItem" header="Project Info" %}
                    {% component "ProjectInfo"
                        project=project
                        project_tags=project_tags
                        roles_with_users=roles_with_users
                        contacts=contacts
                        status_updates=status_updates
                        editable=user_is_project_owner
                    / %}
                {% endcomponent %}

                {% component "TabItem" header="Notes 1" %}
                    {% component "ProjectNotes"
                        project_id=project.id
                        notes=notes_1
                        comments_by_notes=comments_by_notes_1
                        editable=user_is_project_member
                    / %}
                {% endcomponent %}

                {% component "TabItem" header="Notes 2" %}
                    {% component "ProjectNotes"
                        project_id=project.id
                        notes=notes_2
                        comments_by_notes=comments_by_notes_2
                        editable=user_is_project_member
                    / %}
                {% endcomponent %}

                {% component "TabItem" header="Notes 3" %}
                    {% component "ProjectNotes"
                        project_id=project.id
                        notes=notes_3
                        comments_by_notes=comments_by_notes_3
                        editable=user_is_project_member
                    / %}
                {% endcomponent %}

                {% component "TabItem" header="Outputs" %}
                    {% component "ProjectOutputsSummary"
                        project_id=project.id
                        outputs=outputs
                        editable=user_is_project_member
                        phase_titles=phase_titles
                    / %}
                {% endcomponent %}
            {% endfill %}
        {% endcomponent %}
    """

#####################################
# PROJECT_LAYOUT_TABBED
#####################################

class ProjectLayoutData(NamedTuple):
    request: HttpRequest
    active_projects: List[Project]
    project: Project
    bookmarks: List[ProjectBookmark]


def gen_tabs(project_id: int):
    return [
        TabStaticEntry(
            header="Tab 2",
            href=f"/projects/{project_id}/tab-2",
            content=None,
        ),
        TabStaticEntry(
            header="Tab 1",
            href=f"/projects/{project_id}/tab-1",
            content=None,
        ),
    ]


@register("ProjectLayoutTabbed")
class ProjectLayoutTabbed(Component):
    def get_context_data(
        self,
        /,
        *,
        data: ProjectLayoutData,
        breadcrumbs: Optional[List["Breadcrumb"]] = None,
        top_level_tab_index: Optional[int] = None,
        variant: Literal["thirds", "halves"] = "thirds",
    ):
        projects_url = "/projects"
        curr_project_url = f"/projects/{data.project['id']}"

        prefixed_breadcrumbs = chain(
            [
                Breadcrumb(
                    link=projects_url,
                    value=Icon.render(
                        kwargs={
                            "name": "home",
                            "variant": "outline",
                            "size": 20,
                            "stroke_width": 2,
                            "color": "text-gray-400 hover:text-gray-500",
                        },
                        deps_strategy="ignore",
                    ),
                ),
                Breadcrumb(value=data.project["name"], link=curr_project_url),
            ],
            breadcrumbs or [],
        )

        top_level_tabs = gen_tabs(data.project["id"])

        left_pannel_attrs = {
            "class": "w-1/3" if variant == "thirds" else "w-1/2",
        }
        right_pannel_attrs = {
            "class": "w-2/3" if variant == "thirds" else "w-1/2",
        }

        return {
            "layout_data": data,
            "breadcrumbs": prefixed_breadcrumbs,
            "bookmarks": data.bookmarks,
            "project": data.project,
            "top_level_tabs": top_level_tabs,
            "top_level_tab_index": top_level_tab_index,
            "theme": theme,
            "left_pannel_attrs": left_pannel_attrs,
            "right_pannel_attrs": right_pannel_attrs,
        }

    template: types.django_html = """
        {% component "Layout" data=layout_data %}
            {% fill "js" %}
                {% slot "js" / %}
            {% endfill %}

            {% fill "css" %}
                {% slot "css" / %}
            {% endfill %}

            {% fill "header" %}
                {% component "Breadcrumbs" items=breadcrumbs / %}
            {% endfill %}

            {% fill "sidebar" %}
                {% component "Bookmarks" bookmarks=bookmarks project_id=project.id / %}
            {% endfill %}

            {% fill "content" %}
                {% slot "header" / %}

                {% if top_level_tab_index is not None %}
                    {% component "TabsStatic" tabs=top_level_tabs index=top_level_tab_index / %}
                {% endif %}

                <div class="flex flex-auto gap-6">

                {# Split the content to 2 columns, based on whether `left_panel` slot is filled #}
                {% if component_vars.is_filled.left_panel %}
                    <div {% html_attrs left_pannel_attrs class="relative h-full pb-4" %}>
                        <div class="absolute w-full h-full">
                            {% slot "left_panel" / %}
                        </div>
                    </div>
                    <div {% html_attrs right_pannel_attrs class="h-full" %}>
                {% endif %}

                {% slot "content" default %}
                    <div class="h-full divide-y divide-gray-200 bg-white shadow overflow-y-hidden">
                        {% component "Tabs"
                            name="proj-right"
                            attrs:class="p-6 h-full"
                            content_attrs:class="flex flex-col"
                        %}
                            {% slot "tabs" / %}
                        {% endcomponent %}
                    </div>
                {% endslot %}

                {% if component_vars.is_filled.left_panel %}
                    </div>
                {% endif %}
                </div>
            {% endfill %}
        {% endcomponent %}
    """

#####################################
# LAYOUT
#####################################

class LayoutData(NamedTuple):
    request: HttpRequest
    active_projects: List[Project]


@register("Layout")
class Layout(Component):
    def get_context_data(
        self,
        /,
        *,
        data: LayoutData,
        attrs: Optional[dict] = None,
    ):
        return {
            "request": data.request,
            "active_projects": data.active_projects,
            "attrs": attrs,
        }

    template: types.django_html = """
        {% component "RenderContextProvider" request=request %}
            {% component "Base" %}
                {% fill "js" %}
                    {% slot "js" / %}
                {% endfill %}

                {% fill "css" %}
                    {% slot "css" / %}
                {% endfill %}

                {% fill "content" %}
                    <div
                        x-data="layout"
                        @resize.window="onWindowResize"
                        {% html_attrs attrs %}
                    >
                        <!-- Static sidebar for desktop -->
                        <div
                            class="hidden"
                            :class="{
                                'fixed inset-y-0 z-40 flex w-72 flex-col': sidebarOpen,
                                'hidden': !sidebarOpen,
                            }"
                        >
                        {% component "Sidebar" active_projects=active_projects %}
                            {% fill "content" %}
                                {% slot "sidebar" / %}
                            {% endfill %}
                        {% endcomponent %}
                        </div>

                        <div :class="{ 'pl-72': sidebarOpen }" class="flex flex-col" style="height: 100vh;">
                            {% component "Navbar" attrs:@sidebar_toggle="toggleSidebar" / %}

                            <main class="flex-auto flex flex-col">
                                {% slot "header" / %}
                                <div class="px-4 pt-10 sm:px-6 lg:px-8 flex-auto flex flex-col">
                                    {% slot "content" default / %}
                                </div>
                            </main>
                        </div>
                    </div>
                {% endfill %}
            {% endcomponent %}
        {% endcomponent %}
    """

    js: types.js = """
        document.addEventListener('alpine:init', () => {
            // NOTE: Defined as standalone function so we can call it variable initialization
            const computeSidebarState = (prevState) => {
                const width = (window.innerWidth > 0) ? window.innerWidth : screen.width;
                // We automatically hide the sidebar when window is smaller than 1024px
                const sidebarBreakpoint = 1024;
                if (!prevState && width >= sidebarBreakpoint) {
                    return true;
                } else if (prevState && width < sidebarBreakpoint) {
                    return false;
                } else {
                    return prevState;
                }
            };

            Alpine.data('layout', () => ({
                // Variables
                sidebarOpen: computeSidebarState(false),

                init() {
                    this.onWindowResize();
                },

                // Handlers
                toggleSidebar() {
                    this.sidebarOpen = !this.sidebarOpen;
                },

                onWindowResize() {
                    this.sidebarOpen = computeSidebarState(this.sidebarOpen);
                },
            }));
        });
    """


#####################################
# RENDER_CONTEXT_PROVIDER
#####################################

class RenderContext(NamedTuple):
    """
    Data that's commonly available in all template rendering.

    In templates, we can assume that the data defined here is ALWAYS defined.
    """
    request: HttpRequest
    user: User
    csrf_token: str


# This component "provides" data. This is similar to ContextProviders
# in React, or the "provide" part of Vue's provide/inject feature.
#
# Components nested inside `RenderContextProvider` can access the
# data with `self.inject("render_context")`.
@register("RenderContextProvider")
class RenderContextProvider(Component):
    def get_context_data(
        self,
        /,
        *,
        request: HttpRequest,
    ):
        csrf_token = csrf.get_token(request)
        context = RenderContext(
            request=request,
            user=request.user,
            csrf_token=csrf_token,
        )

        return {
            "context": context,
        }

    template: types.django_html = """
        {% provide "render_context" render_context=context %}
            {% slot "content" default / %}
        {% endprovide %}
    """

#####################################
# BASE
#####################################

@register("Base")
class Base(Component):
    def get_context_data(self) -> dict:
        context: RenderContext = self.inject("render_context").render_context

        return {
            "csrf_token": context.csrf_token,
            "theme": theme,
        }

    template: types.django_html = """
        {% load static %}

        <!DOCTYPE html>
        <html lang="en" class="h-full">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DEMO</title>
            {% component_css_dependencies %}

            {% slot "css" / %}
        </head>
        <body class="{{ theme.background }} h-full">
            {% slot "content" default / %}

            {# AlpineJS + Plugins #}
            <script src="//unpkg.com/@alpinejs/anchor" defer></script>
            <script src="https://cdn.jsdelivr.net/npm/alpine-reactivity@0.1.10/dist/cdn.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/alpine-composition@0.1.27/dist/cdn.min.js"></script>
            <script src="//unpkg.com/alpinejs" defer></script>

            {# HTMX #}
            <script type="text/javascript" src="{% static 'js/htmx.js' %}"></script>

            {# Axios (AJAX) #}
            <script src="https://unpkg.com/axios/dist/axios.min.js"></script>

            {# JS scripts from our custom Django components #}
            {% component_js_dependencies %}

            {# Any extra scripts #}
            {% slot "js" / %}

            <script>
                {# Configure csrf_token for HTMX #}
                (function () {
                    const token = '{{ csrf_token }}';
                        document.body.addEventListener('htmx:configRequest', (event) => {
                        event.detail.headers['X-CSRFToken'] = token;
                    });

                    {# Expose csrf_token to AlpineJS #}
                    document.addEventListener('alpine:init', () => {
                        Alpine.store('csrf', {
                            token,
                        });
                    });
                })();
            </script>
        </body>
        </html>
    """

    js: types.js = """
        ////////////////////////////////////////////////////////////////
        // base.js
        ////////////////////////////////////////////////////////////////

        /** Global JS state / methods */
        const app = {
            // NOTE: queryManager.js MUST be loaded before this script!
            query: createQueryManager(),
        };

        app.query.load();

        ////////////////////////////////////////////////////////////////
        // queryManager.js
        ////////////////////////////////////////////////////////////////

        /**
         * Callback when a URL's query param changes.
         *
         * @callback OnParamChangeCallback
         * @param {string | null} newValue - New value of the query param.
         * @param {string | null} oldValue - Old value of the query param.
         */

        /**
         * Function that can be called once to remove the registered callback.
         *
         * @callback UnregisterFn
         */

        /**
         * Callback for modifying URL.
         *
         * @callback OnUrlModifyCallback
         * @param {URL} currUrl - Current URL.
         * @returns {URL | string} New URL.
         */

        /**
         * Singular interface for manipulating URL search/query parameters
         * and reacting to changes.
         *
         * See https://developer.mozilla.org/en-US/docs/Web/API/Location/search
         */
        const createQueryManager = () => {
            /**
             * @type {Record<string, OnParamChangeCallback[]>}
             */
            const callbacks = {};

            /**
             * Store previous values of query params, so we can provide both new and old
             * values to the callbacks.
             *
             * NOTE: Use `setParamValue` instead of setting values directly.
             *
             * @type {Record<string, string | null>}
             */
            const previousParamValues = {};

            /**
             * @param {string} key
             * @param {string | null} newValue
             */
            const setParamValue = (key, newValue) => {
                const oldValue =
                previousParamValues[key] === undefined ? null : previousParamValues[key];

                previousParamValues[key] = newValue;

                const paramCallbacks = callbacks[key] || [];

                paramCallbacks.forEach((cb) => cb(newValue, oldValue));
            };

            /**
             * Register a listener that will be triggered when a value changes for the query param
             * of given name.
             *
             * Returns a function that can be called once to remove the registered callback.
             *
             * @param {string} paramName
             * @param {OnParamChangeCallback} callback
             * @returns {UnregisterFn}
             */
            const registerParam = (paramName, callback) => {
                if (callbacks[paramName] == undefined) {
                    callbacks[paramName] = [];
                }

                callbacks[paramName].push(callback);

                // Run the callback once if the query param already has some value
                if (previousParamValues[paramName] != null) {
                    callback(previousParamValues[paramName], null);
                }

                // Return a function that can be called once to remove the registered callback
                let unregisterCalled = false;
                const unregister = () => {
                    if (unregisterCalled) return;
                    unregisterCalled = true;

                    unregisterParam(paramName, callback);
                };

                return unregister;
            };

            /**
             * Unregister a callback that was previously registered with `registerParam`
             * for the query param of given name.
             *
             * @param {string} paramName
             * @param {OnParamChangeCallback} callback
             */
            const unregisterParam = (paramName, callback) => {
                // Nothing to do
                if (callbacks[paramName] == undefined) return;

                // Remove one instance of callback from the array to simulate similar behavior
                // as browser's addEventListener/removeEventListener.
                // See https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener
                const indexToRemove = callbacks[paramName].indexOf(callback);
                if (indexToRemove !== -1) {
                    callbacks[paramName].splice(indexToRemove, 1);
                }
            };

            /**
             * Shared logic for modifying the page's URL in-place (without reload).
             *
             * @param {OnUrlModifyCallback} mapFn
             */
            const modifyUrl = (mapFn) => {
                // Prepare current URL
                const currUrl = new URL(globalThis.location.href);

                // Let the user of this function decide how to transform the URL
                let updatedUrl = mapFn(currUrl);

                // Update browser URL without reloading the page
                // See https://developer.mozilla.org/en-US/docs/Web/API/History/pushState
                // And https://stackoverflow.com/a/3354511/9788634
                globalThis.history.replaceState(null, "", updatedUrl.toString());
            };

            /**
             * Set query parameters to the URL.
             *
             * If the URL already contains query params of the same name, these will be overwritten.
             *
             * @param {Record<string, string>} params
             */
            const setParams = (params) => {
                modifyUrl((currUrl) => {
                    Object.entries(params).forEach(([key, val]) => {
                        currUrl.searchParams.set(key, val);
                    });
                    return currUrl.href;
                });

                // Trigger callbacks for all params that were set.
                Object.entries(params).forEach(([key, val]) => setParamValue(key, val));
            };

            /** Clear all query parameters from the URL. */
            const clearParams = () => {
                modifyUrl((currUrl) => {
                    currUrl.search = "";
                    return currUrl.href;
                });

                // Trigger callbacks for all params that were unset.
                Object.entries(previousParamValues)
                    .filter(([key, val]) => val !== null)
                    .forEach(([key, val]) => setParamValue(key, val));
            };

            /** Load query params from the current page URL, triggering any registered callbacks. */
            const load = () => {
                const currUrl = new URL(globalThis.location.href);
                currUrl.searchParams.forEach((value, key) => setParamValue(key, value));
            };

            return {
                setParams,
                clearParams,
                registerParam,
                unregisterParam,
                load,
            };
        };

        ////////////////////////////////////////////////////////////////
        // submitForm.js
        ////////////////////////////////////////////////////////////////

        /**
         * @param {HTMLFormElement} formEl
         */
        const getFormData = (formEl) => {
            return Object.fromEntries(new FormData(formEl));
        };

        /**
         * @param {HTMLFormElement} formEl
         * @param {object} formData
         */
        const submitForm = (formEl, data, { reload = false } = {}) => {
            // Do not submit anything when the form doesn't specify the target URL
            if (!formEl.hasAttribute('action')) Promise.resolve();

            return axios.post(formEl.action, data, {
                method: formEl.method,
            })
                .then((response) => {
                    if (reload) location.reload();
                })
                .catch((error) => {
                    console.error(error);
                });
        };
    """

#####################################
# SIDEBAR
#####################################

class SidebarItem(NamedTuple):
    name: str
    icon: Optional[str] = None
    icon_variant: Optional[str] = None
    href: Optional[str] = None
    children: Optional[List["SidebarItem"]] = None


# Links in the sidebar.
def gen_sidebar_menu_items(active_projects: List[Project]) -> List[SidebarItem]:
    items: List[SidebarItem] = [
        SidebarItem(
            name="Homepage",
            icon="home",
            icon_variant="outline",
            href="/",
        ),
        SidebarItem(
            name="Projects",
            icon="folder",
            icon_variant="outline",
            href="/projects",
            children=[
                SidebarItem(
                    name=project['name'],
                    icon=None,
                    href=f"/projects/{project['id']}",
                )
                for project in active_projects
            ],
        ),
        SidebarItem(
            name="Page 3",
            icon="folder",
            icon_variant="outline",
            href="/page-3",
        ),
        SidebarItem(
            name="Page 4",
            icon="bars-arrow-down",
            icon_variant="outline",
            href="/page-4",
        ),
        SidebarItem(
            name="page-5",
            icon="forward",
            icon_variant="outline",
            href="/page-5",
        ),
        SidebarItem(
            name="FAQ",
            icon="archive-box",
            icon_variant="outline",
            href="/faq",
        ),
    ]

    return items


@register("Sidebar")
class Sidebar(Component):
    def get_context_data(
        self,
        /,
        *,
        active_projects: List[Project],
        attrs: Optional[dict] = None,
    ):
        context: RenderContext = self.inject("render_context").render_context
        user = context.user
        items = gen_sidebar_menu_items(active_projects)

        faq_url = "/faq"

        return {
            "items": items,
            "attrs": attrs,
            "user": user,
            "theme": theme,
            "faq_url": faq_url,
        }

    template: types.django_html = """
        <div
            {% html_attrs
                attrs
                class="flex grow flex-col gap-y-5 overflow-y-auto px-6 pb-4"
                class=theme.sidebar
            %}
        >
            <div class="flex h-16 shrink-0 items-center">
                DEMO
            </div>
            <nav class="flex flex-1 flex-col">
                <ul role="list" class="flex flex-1 flex-col gap-y-7">
                    <li>
                        {% slot "content" / %}

                        <ul role="list" class="-mx-2 space-y-1">
                            {% for sidebar_item in items %}
                                <li>
                                    {% component "Icon"
                                        name=sidebar_item.icon
                                        variant=sidebar_item.icon_variant
                                        href=sidebar_item.href
                                        color=theme.sidebar_link
                                        text_attrs:class="p-2"
                                    %}
                                        {{ sidebar_item.name }}
                                    {% endcomponent %}
                                </li>

                                {% for child_item in sidebar_item.children %}
                                    <li class="ml-8 rounded-md {{ theme.sidebar_link }}">
                                        {% component "Button"
                                            variant="plain"
                                            href=child_item.href
                                            attrs:class="p-2 !w-full"
                                        %}
                                            {{ child_item.name }}
                                        {% endcomponent %}
                                    </li>
                                {% endfor %}
                            {% endfor %}
                        </ul>

                        <li class="mt-auto">
                            {% component "Icon"
                                name='user-group'
                                variant='outline'
                                href=faq_url
                                color=theme.sidebar_link
                                text_attrs:class="p-2"
                            %}
                                FAQ
                            {% endcomponent %}

                            {% component "Icon"
                                name='megaphone'
                                variant='outline'
                                color=theme.sidebar_link
                                link_attrs:target="_blank"
                                text_attrs:class="p-2"
                            %}
                                Feedback
                            {% endcomponent %}
                        </li>

                        {% if user.is_staff %}
                            <li>
                                {% component "Icon"
                                    name='document-arrow-down'
                                    variant='outline'
                                    color=theme.sidebar_link
                                    text_attrs:class="p-2"
                                %}
                                    Download
                                {% endcomponent %}
                            </li>
                        {% endif %}
                    </li>
                </ul>
            </nav>
        </div>
    """

#####################################
# NAVBAR
#####################################

@register("Navbar")
class Navbar(Component):
    def get_context_data(
        self,
        /,
        *,
        attrs: Optional[dict] = None,
    ):
        return {
            "attrs": attrs,
        }

    template: types.django_html = """
        <div
            {% html_attrs
                attrs
                class="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8"
            %}
        >
            <button
                type="button"
                class="-m-2.5 p-2.5 text-gray-700"
                @click="$dispatch('sidebar_toggle')"
            >
                <span class="sr-only">Open sidebar</span>
                {% component "Icon" name='bars-3' variant='outline' / %}
            </button>

            <!-- Separator -->
            <div class="h-6 w-px bg-gray-900/10 lg:hidden" aria-hidden="true"></div>

            <div class="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
                {# Search not implemented #}
                <form class="relative flex flex-1 items-center" action="#" method="GET">
                </form>

                <div class="flex items-center gap-x-4 lg:gap-x-6">
                    <!-- Separator -->
                    <div
                        class="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-900/10"
                        aria-hidden="true"
                    ></div>

                </div>
            </div>
        </div>
    """  # noqa: E501

#####################################
# DIALOG
#####################################

def construct_btn_onclick(model: str, btn_on_click: Optional[str]):
    """
    We want to allow the component users to define Alpine.js `@click` actions.
    However, we also need to use `@click` to close the dialog after clicking
    one of the buttons.

    Hence, this function constructs the '@click' attribute, such that we can do both.

    NOTE: `model` is the name of the Alpine variable used by the dialog.
    """
    on_click_cb = f"{model} = false;"
    if btn_on_click:
        on_click_cb = f"{btn_on_click}; {on_click_cb}"
    return mark_safe(on_click_cb)


@register("Dialog")
class Dialog(Component):
    def get_context_data(
        self,
        /,
        *,
        model: Optional[str] = None,
        # Classes and HTML attributes
        attrs: Optional[dict] = None,
        activator_attrs: Optional[dict] = None,
        title_attrs: Optional[dict] = None,
        content_attrs: Optional[dict] = None,
        # Confirm button
        confirm_hide: Optional[bool] = None,
        confirm_text: Optional[str] = "Confirm",
        confirm_href: Optional[str] = None,
        confirm_disabled: Optional[bool] = None,
        confirm_variant: Optional["ThemeVariant"] = "primary",
        confirm_color: Optional["ThemeColor"] = None,
        confirm_type: Optional[str] = None,
        confirm_on_click: Optional[str] = "",
        confirm_attrs: Optional[dict] = None,
        # Cancel button
        cancel_hide: Optional[bool] = None,
        cancel_text: Optional[str] = "Cancel",
        cancel_href: Optional[str] = None,
        cancel_disabled: Optional[bool] = None,
        cancel_variant: Optional["ThemeVariant"] = "secondary",
        cancel_color: Optional["ThemeColor"] = None,
        cancel_type: Optional[str] = None,
        cancel_on_click: Optional[str] = "",
        cancel_attrs: Optional[dict] = None,
        # UX
        close_on_esc: Optional[bool] = True,
        close_on_click_outside: Optional[bool] = True,
    ):
        is_model_overriden = bool(model)
        model = model or "open"

        # Modify "attrs" passed to buttons, so we close the dialog when clicking the buttons
        cancel_attrs = {
            **(cancel_attrs or {}),
            "@click": construct_btn_onclick(model, cancel_on_click),
        }
        confirm_attrs = {
            **(confirm_attrs or {}),
            "@click": construct_btn_onclick(model, confirm_on_click),
        }

        return {
            "model": model,
            "is_model_overriden": is_model_overriden,
            # Classes and HTML attributes
            "attrs": attrs,
            "activator_attrs": activator_attrs,
            "content_attrs": content_attrs,
            "title_attrs": title_attrs,
            # UX
            "close_on_esc": close_on_esc,
            "close_on_click_outside": close_on_click_outside,
            # Confirm button
            "confirm_hide": confirm_hide,
            "confirm_text": confirm_text,
            "confirm_href": confirm_href,
            "confirm_disabled": confirm_disabled,
            "confirm_variant": confirm_variant,
            "confirm_color": confirm_color,
            "confirm_type": confirm_type,
            "confirm_attrs": confirm_attrs,
            # Cancel button
            "cancel_hide": cancel_hide,
            "cancel_text": cancel_text,
            "cancel_href": cancel_href,
            "cancel_disabled": cancel_disabled,
            "cancel_variant": cancel_variant,
            "cancel_color": cancel_color,
            "cancel_type": cancel_type,
            "cancel_attrs": cancel_attrs,
        }

    template: types.django_html = """
        {# Based on https://tailwindui.com/components/application-ui/overlays/modals #}

        {% comment %}
        NOTE: {{ model }} is the Alpine variable used for opening/closing. The variable name
            is set dynamically, hence we use Django's double curly braces to refer to it.
        {% endcomment %}
        <div
            x-data="{
                id: $id('modal-title'),

                {% if not is_model_overriden %}
                '{{ model }}': false,
                {% endif %}
            }"
            {% if close_on_esc %}
                @keydown.escape="{{ model }} = false"
            {% endif %}
            {% html_attrs attrs %}
        >
            {% if component_vars.is_filled.activator or component_vars.is_filled.default %}
                {# This is what opens the modal #}
                <div
                    @click="{{ model }} = true"
                    {% html_attrs activator_attrs %}
                >
                    {% slot "activator" default / %}
                </div>
            {% endif %}

            <div
                class="relative z-50"
                :aria-labelledby="id"
                role="dialog"
                aria-modal="true"
                x-cloak
            >
                <!-- Background backdrop, show/hide based on modal state. -->
                <div
                    class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
                    x-show="{{ model }}"
                ></div>

                <div
                    class="fixed inset-0 z-50 w-screen overflow-y-auto"
                    x-show="{{ model }}"
                >
                    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">

                        <!-- Modal panel, show/hide based on modal state. -->
                        <div
                            class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg"
                            {% if close_on_click_outside %}
                            @click.away="{{ model }} = false"
                            {% endif %}
                        >
                            <div class="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                                <div class="sm:flex sm:items-start">
                                    {% slot "prepend" / %}

                                    <div {% html_attrs content_attrs %}>
                                        {% if component_vars.is_filled.title %}
                                            <h3
                                                :id="id"
                                                {% html_attrs title_attrs class="font-semibold text-gray-900" %}
                                            >
                                                {% slot "title" / %}
                                            </h3>
                                        {% endif %}

                                        {% slot "content" / %}
                                    </div>

                                    {% slot "append" / %}
                                </div>
                            </div>
                            <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6 gap-5">
                                {% if not confirm_hide %}
                                    {% component "Button"
                                        variant=confirm_variant
                                        color=confirm_color
                                        disabled=confirm_disabled
                                        href=confirm_href
                                        type=confirm_type
                                        attrs=confirm_attrs
                                    %}
                                        {{ confirm_text }}
                                    {% endcomponent %}
                                {% endif %}

                                {% if not cancel_hide %}
                                    {% component "Button"
                                        variant=cancel_variant
                                        color=cancel_color
                                        disabled=cancel_disabled
                                        href=cancel_href
                                        type=cancel_type
                                        attrs=cancel_attrs
                                    %}
                                        {{ cancel_text }}
                                    {% endcomponent %}
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """  # noqa: E501

#####################################
# TAGS
#####################################

class TagEntry(NamedTuple):
    tag: str
    selected: bool = False


# JS props that can be passed to the Alpine component via python
class TagsJsProps(TypedDict):
    initTags: str


@register("Tags")
class Tags(Component):
    def get_context_data(
        self,
        /,
        *,
        tag_type: str,
        js_props: dict,
        editable: bool = True,
        max_width: Union[int, str] = '300px',
        attrs: Optional[dict] = None,
    ):
        all_tags = TAG_TYPE_META[tag_type.upper()].allowed_values  # type: ignore[index]

        return {
            "editable": editable,
            "all_tags": all_tags,
            "max_width": max_width,
            "attrs": attrs,
            "js_props": js_props,
        }

    template: types.django_html = """
        <div
            x-data="tags"
            x-props="{
                initAllTags: '{{ all_tags|json|escape }}',
                initTags: {{ js_props.initTags|escape }},
                onChange: {{ js_props.onChange|escape }},
            }"
            {% html_attrs attrs class="pt-3 flex flex-col gap-y-3 items-start" %}
        >
            <input x-ref="tagsInput" type="hidden" name="tags" value="" />

            {% slot "title" %}
                <p class="text-sm">
                    Tags:
                </p>
            {% endslot %}

            <template x-for="(tag, index) in tags.value">
                <div
                    class="tag text-sm flex flex-col gap-1 w-full"
                    style="max-width: {{ max_width }}"
                >
                    <div class="flex gap-6 w-full justify-between items-center">
                        <select
                            name="_tags"
                            class="flex-auto py-1 px-2"
                            @change="(ev) => setTag(index, ev.target.value)"
                            {% if not editable %}
                                disabled
                            {% endif %}
                        >
                            <template x-for="option in tag.options">
                                <option
                                    :value="option"
                                    :selected="option === tag.value"
                                    x-text="option"
                                >
                                </option>
                            </template>
                        </select>

                        {% if editable %}
                            <div>
                                {% component "Button"
                                    color="error"
                                    attrs:class="!py-1"
                                    attrs:@click="removeTag(index)"
                                %}
                                    Remove
                                {% endcomponent %}
                            </div>
                        {% endif %}
                    </div>
                </div>
            </template>

            {% if editable %}
                <div x-show="tags.value.length < allTags.value.length">
                    {% component "Button"
                        attrs:class="!py-1"
                        attrs:@click="addTag"
                    %}
                        Add tag
                    {% endcomponent %}
                </div>
            {% endif %}
        </div>
    """

    js: types.js = """
        // Define component similarly to defining Vue components
        const Tags = AlpineComposition.defineComponent({
            name: "tags",

            props: {
                initAllTags: { type: String, required: true },
                initTags: { type: Array, required: true },
            },

            emits: {
                change: () => true,
            },

            // Instead of Alpine's init(), use setup()
            // Props are passed down as reactive props, same as in Vue
            // Second argument is the Alpine component instance.
            setup(props, vm) {
                const { ref, watch } = AlpineComposition.createReactivityAPI(vm);

                const allTags = ref([]);
                const tags = ref([]);

                // Set the initial state from HTML
                if (props.initAllTags) {
                    allTags.value = JSON.parse(props.initAllTags);
                }

                if (props.initTags) {
                    tags.value = props.initTags.map((t) => ({
                        value: t,
                        options: [],
                    }));

                    const availableTags = getAvailableTags();
                    tags.value = tags.value.map((t) => ({
                        value: t.value,
                        options: [t.value, ...availableTags],
                    }));
                }

                watch(tags, () => {
                    onTagsChange();
                });

                onTagsChange();

                // Methods
                const addTag = () => {
                    const availableTags = getAvailableTags();
                    if (!availableTags.length) return;

                    // Add tag by removing it from available tags
                    const nextValue = availableTags.shift();
                    const newSelectedTags = [
                        ...tags.value.map((t) => t.value),
                        nextValue,
                    ];

                    // And add it to the selected tags
                    tags.value = newSelectedTags.map((t) => ({
                        value: t,
                        options: [t, ...availableTags],
                    }));
                }

                const removeTag = (index) => {
                    // Remove the removed tag from selected items
                    tags.value = tags.value.filter((_, i) => i !== index);

                    // And add it to the available tags
                    const availableTags = getAvailableTags();
                    tags.value = tags.value.map((t) => ({
                        value: t.value,
                        options: [t.value, ...availableTags],
                    }));
                }

                const setTag = (index, value) => {
                    // Update the value
                    const oldValue = tags.value[index].value;
                    tags.value = tags.value.map((t) => ({
                        value: t.value === oldValue ? value : t.value,
                        options: t.options,
                    }));

                    // Then update the available tags
                    const availableTags = getAvailableTags();
                    tags.value = tags.value.map((t) => ({
                        value: t.value,
                        options: [t.value, ...availableTags],
                    }));
                }

                // When tags are added or removed, we add/remove HTML by AlpineJS,
                // so user doesn't have to refresh the page.
                function onTagsChange() {
                    if (vm.$refs.tagsInput) {
                        vm.$refs.tagsInput.value = tags.value.map((t) => t.value).join(',');
                    }

                    // Emit the final list of selected tags
                    const payload = tags.value.map((t) => t.value);
                    vm.$emit("change", payload);
                }

                function getAvailableTags() {
                    const selectedTagsSet = new Set(tags.value.map((t) => t.value));
                    return allTags.value.filter((t) => !selectedTagsSet.has(t));
                }

                return {
                    tags,
                    allTags,
                    addTag,
                    removeTag,
                    setTag,
                };
            },
        });

        document.addEventListener('alpine:init', () => {
            AlpineComposition.registerComponent(Alpine, Tags);
        });
    """

#####################################
# FORM
#####################################

@register("Form")
class Form(Component):
    def get_context_data(
        self,
        /,
        *,
        type: Literal["table", "paragraph", "ul", None] = None,
        editable: bool = True,
        method: str = "post",
        # Submit btn
        submit_hide: Optional[bool] = None,
        submit_text: Optional[str] = "Submit",
        submit_href: Optional[str] = None,
        submit_disabled: Optional[bool] = None,
        submit_variant: Optional["ThemeVariant"] = "primary",
        submit_color: Optional["ThemeColor"] = None,
        submit_type: Optional[str] = "submit",
        submit_attrs: Optional[dict] = None,
        # Cancel btn
        cancel_hide: Optional[bool] = None,
        cancel_text: Optional[str] = "Cancel",
        cancel_href: Optional[str] = None,
        cancel_disabled: Optional[bool] = None,
        cancel_variant: Optional["ThemeVariant"] = "secondary",
        cancel_color: Optional["ThemeColor"] = None,
        cancel_type: Optional[str] = "button",
        cancel_attrs: Optional[dict] = None,
        # Actions
        actions_hide: Optional[bool] = None,
        actions_attrs: Optional[dict] = None,
        # Other
        form_content_attrs: Optional[dict] = None,
        attrs: Optional[dict] = None,
    ):
        if type == "table":
            form_content_tag = "table"
        elif type == "paragraph":
            form_content_tag = "div"
        elif type == "ul":
            form_content_tag = "ul"
        else:
            form_content_tag = "div"

        # Add AlpineJS bindings to submit button
        submit_attrs = {
            **(submit_attrs or {}),
            ":disabled": "isSubmitting",
        }

        return {
            "form_content_tag": form_content_tag,
            "form_content_attrs": form_content_attrs,
            "method": method,
            "editable": editable,
            "submit_hide": submit_hide,
            "submit_text": submit_text,
            "submit_href": submit_href,
            "submit_disabled": submit_disabled or not editable,
            "submit_variant": submit_variant,
            "submit_color": submit_color,
            "submit_type": submit_type,
            "submit_attrs": submit_attrs,
            "cancel_hide": cancel_hide,
            "cancel_text": cancel_text,
            "cancel_href": cancel_href,
            "cancel_disabled": cancel_disabled,
            "cancel_variant": cancel_variant,
            "cancel_color": cancel_color,
            "cancel_type": cancel_type,
            "cancel_attrs": cancel_attrs,
            "actions_hide": actions_hide,
            "actions_attrs": actions_attrs,
            "attrs": attrs,
        }

    template: types.django_html = """
        <form
            {% if submit_href and editable %} action="{{ submit_href }}" {% endif %}
            method="{{ method }}"
            x-data="form"
            {% html_attrs attrs %}
        >
            <{{ form_content_tag }}
                @click="updateFormModel"
                @change="updateFormModel"
                {% html_attrs form_content_attrs %}
            >
                {% slot "form" default / %}
            </{{ form_content_tag }}>

            {% slot "below_form" / %}

            {% if not actions_hide %}
                <div {% html_attrs actions_attrs class="pt-4" %}>
                    {% slot "actions_prepend" / %}

                    {% if not submit_hide %}
                        {% component "Button"
                            variant=submit_variant
                            color=submit_color
                            disabled=submit_disabled
                            type=submit_type
                            attrs=submit_attrs
                        %}
                            {{ submit_text }}
                        {% endcomponent %}
                    {% endif %}

                    {% if not cancel_hide %}
                        {% component "Button"
                            variant=cancel_variant
                            color=cancel_color
                            disabled=cancel_disabled
                            href=cancel_href
                            type=cancel_type
                            attrs=cancel_attrs
                        %}
                            {{ cancel_text }}
                        {% endcomponent %}
                    {% endif %}

                    {% slot "actions_append" / %}
                </div>
            {% endif %}
        </form>
    """

    js: types.js = """
        document.addEventListener('alpine:init', () => {
            Alpine.data('form', () => {
                const data = Alpine.reactive({
                    // Variables
                    formData: {},
                    isSubmitting: false,

                    // Methods
                    updateFormModel(event) {
                        const form = this.$el.closest("form");
                        if (!form) {
                            this.formData = null;
                            return;
                        };

                        const formDataObj = new FormData(form)
                        this.formData = [...formDataObj.entries()].reduce((agg, [key, val]) => {
                            agg[key] = val;
                            return agg;
                        }, {});
                    },

                    onSubmit(event) {
                        if (this.isSubmitting) return;

                        this.isSubmitting = true;
                        event.target.submit();
                    },
                });

                // Detect when Alpine's form state has changed and emit event when that happens
                // NOTE: Alpine's reactivity is based on @vue/reactivity
                Alpine.watch(() => data.formData, (newVal, oldVal) => {
                    const hasDataChanged = JSON.stringify(newVal || null) !== JSON.stringify(oldVal || null);
                    if (!hasDataChanged) return;

                    data.$dispatch('change', newVal);
                });

                return data;
            });
        });
    """

#####################################
# BREADCRUMBS
#####################################

@dataclass(frozen=True)
class Breadcrumb:
    """
    Single breadcrumb item used with the `breadcrumb` components.
    """

    value: Any
    """Value of the menu item to render."""

    link: Optional[str] = None
    """
    If set, the item will be wrapped in an `<a>` tag pointing to this
    link.
    """

    item_attrs: Optional[dict] = None
    """HTML attributes specific to this item."""


@register("Breadcrumbs")
class Breadcrumbs(Component):
    def get_context_data(
        self,
        /,
        *,
        items: List[Breadcrumb],
        attrs: Optional[dict] = None,
    ):
        return {
            "items": items,
            "attrs": attrs,
        }

    template: types.django_html = """
        <nav
            aria-label="Breadcrumb"
            {% html_attrs attrs class="flex border-b border-gray-200 bg-white" %}
        >
            <ol
                role="list"
                class="mx-auto flex w-full max-w-screen-xl space-x-4 px-4 sm:px-6 lg:px-8"
            >
                {% for crumb in items %}
                    <li class="flex">
                        <div class="flex items-center">
                            {# Divider #}
                            {% if not forloop.first %}
                                <svg
                                    class="h-full w-6 flex-shrink-0 text-gray-200"
                                    viewBox="0 0 24 44"
                                    preserveAspectRatio="none"
                                    fill="currentColor"
                                    aria-hidden="true"
                                >
                                    <path d="M.293 0l22 22-22 22h1.414l22-22-22-22H.293z" />
                                </svg>
                            {% endif %}

                            {# Breadcrumb link #}
                            {% if crumb.link %}
                                <a
                                    href="{{ crumb.link }}"
                                    {% html_attrs
                                        crumb.item_attrs
                                        class="ml-4 text-sm font-medium text-gray-500 hover:text-gray-700"
                                    %}
                                >
                            {% else %}
                                <span
                                    {% html_attrs
                                        crumb.item_attrs
                                        class="ml-4 text-sm font-medium text-gray-500 hover:text-gray-700"
                                    %}
                                >
                            {% endif %}

                            {{ crumb.value }}

                            {% if crumb.link %}
                                </a>
                            {% else %}
                                </span>
                            {% endif %}
                        </div>
                    </li>
                {% endfor %}
            </ol>
        </nav>
    """


#####################################
# BOOKMARKS
#####################################

item_class = "px-4 py-1 text-sm text-gray-900 hover:bg-gray-100 cursor-pointer"
menu_items = [
    [
        MenuItem(
            value="Edit",
            link="#",
            item_attrs={
                "class": item_class,
                ":href": "contextMenuItem.value.edit_url",
            },
        ),
    ],
]


@register("Bookmarks")
class Bookmarks(Component):
    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        bookmarks: List[ProjectBookmark],
        attrs: Optional[dict] = None,
    ):
        bookmark_data: List[BookmarkItem] = []
        attachment_data: List[BookmarkItem] = []

        for bookmark in bookmarks:
            is_attachment = bookmark['attachment'] is not None

            if is_attachment:
                # Send user to the Output tab in Project page and open and scroll
                # to the relevent output that has the correct attachment.
                edit_url = (
                    f"/edit/{project_id}/bookmark/{bookmark['id']}"
                    f"?{ProjectPageTabsToQueryParams.OUTPUTS.value}"
                    f"&panel={bookmark['attachment']['output']['id']}"  # type: ignore[index]
                )  # type: ignore[index]
            else:
                edit_url = f"/edit/{project_id}/bookmark/{bookmark['id']}"

            entry = BookmarkItem(
                text=bookmark['text'],
                url=bookmark['url'],
                id=bookmark['id'],
                edit_url=edit_url,
            )

            if is_attachment:
                attachment_data.append(entry)
            else:
                bookmark_data.append(entry)

        create_bookmark_url = f"/create/{project_id}/bookmark"

        return {
            "bookmark_data": bookmark_data,
            "attachment_data": attachment_data,
            "create_bookmark_url": create_bookmark_url,
            "menu_items": menu_items,
            "attrs": attrs,
            "theme": theme,
        }

    template: types.django_html = """
        <li x-data="bookmarks" {% html_attrs attrs class="pt-4" %}>
            {% component "Icon"
                name="bookmark"
                variant="outline"
                text_attrs:class="py-2 text-sm"
            %}
                Project Bookmarks
            {% endcomponent %}
            <ul class="mx-4">
                {% for bookmark in bookmark_data %}
                    {% component "Bookmark"
                        bookmark=bookmark
                        js:onMenuToggle="onContextMenuToggle"
                    / %}
                {% endfor %}

                <li>
                    {% component "Icon"
                        name="plus"
                        variant="outline"
                        size=18
                        href=create_bookmark_url
                        color=theme.sidebar_link
                        text_attrs:class="px-2 py-1 text-xs"
                        svg_attrs:class="mt-0.5 ml-1"
                    %}
                        Add New Bookmark
                    {% endcomponent %}
                </li>

                <div class="border-b border-gray-200 my-2 pt-2 text-sm font-bold">
                    Attachments:
                </div>

                {% for bookmark in attachment_data %}
                    {% component "Bookmark"
                        bookmark=bookmark
                        js:onMenuToggle="onContextMenuToggle"
                    / %}
                {% endfor %}
            </ul>

            <template x-if="contextMenuItem.value">
                <div class="self-center">
                    {% component "Menu"
                        items=menu_items
                        model="contextMenuItem.value"
                        anchor="contextMenuRef.value"
                        anchor_dir="bottom"
                        list_attrs:class="w-24 ml-8 z-40"
                        attrs:@click_outside="onContextMenuClickOutside"
                    / %}
                </div>
            </template>
        </li>
    """

    js: types.js = """
        const useContextMenu = (reactivity) => {
            const { ref } = reactivity;

            const contextMenuItem = ref(null);
            const contextMenuRef = ref(null);

            const contextMenuReset = () => {
                contextMenuItem.value = null;
                contextMenuRef.value = null;
            };

            const onContextMenuToggle = (data) => {
                const { item, el } = data;

                const willUntoggle = contextMenuItem.value && contextMenuItem.value.id === item.id;

                // NOTE: We need to remove the component first before we can re-render it
                // at a different place using `x-anchor`.
                contextMenuItem.value = null;
                contextMenuRef.value = null;

                // If we are to untoggled currently-active menu, since we've already set values to null,
                // there's nothing more to be done.
                if (willUntoggle) {
                    return;
                }

                // Otherwise, we should open a new menu
                setTimeout(() => {
                    contextMenuItem.value = item;
                    contextMenuRef.value = el;
                });
            };

            const onContextMenuClickOutside = (event) => {
                contextMenuReset();
            };

            return {
                contextMenuItem,
                contextMenuRef,
                contextMenuReset,
                onContextMenuToggle,
                onContextMenuClickOutside,
            };
        };

        // Define component similarly to defining Vue components
        const Bookmarks = AlpineComposition.defineComponent({
            name: "bookmarks",

            props: {},
            emits: {},

            setup(props, vm, reactivity) {
                const {
                    contextMenuItem,
                    contextMenuRef,
                    onContextMenuToggle,
                    onContextMenuClickOutside,
                } = useContextMenu(reactivity);

                return {
                    contextMenuItem,
                    contextMenuRef,
                    onContextMenuToggle,
                    onContextMenuClickOutside,
                };
            },
        });

        document.addEventListener('alpine:init', () => {
            AlpineComposition.registerComponent(Alpine, Bookmarks);
        });
    """

#####################################
# BOOKMARK
#####################################

class BookmarkItem(NamedTuple):
    id: int
    text: str
    url: str
    edit_url: str


@register("Bookmark")
class Bookmark(Component):
    def get_context_data(
        self,
        /,
        *,
        bookmark: BookmarkItem,
        js: Optional[dict] = None,
    ):
        return {
            "theme": theme,
            "bookmark": bookmark._asdict(),
            "js": js,
        }

    template: types.django_html = """
        <li
            x-data="bookmark"
            x-props="{
                onMenuToggle: {{ js.onMenuToggle|escape }},
                bookmark: {{ bookmark|alpine }},
            }"
            class="list-disc ml-8"
        >
            <div class="flex">
                <a
                    href="{{ bookmark.url }}"
                    target="_blank"
                    class="grow px-2 py-1 text-xs font-semibold {{ theme.sidebar_link }}"
                >
                    {{ bookmark.text }}
                </a>

                {% component "Icon"
                    name='ellipsis-vertical'
                    variant='outline'
                    color=theme.sidebar_link
                    svg_attrs:class="inline"
                    text_attrs:class="p-0"
                    attrs:class="self-center cursor-pointer"
                    attrs:x-ref="bookmark_menu"
                    attrs:@click="onMenuToggle"
                / %}
            </div>
        </li>
    """

    js: types.js = """
        // Define component similarly to defining Vue components
        const Bookmark = AlpineComposition.defineComponent({
            name: "bookmark",

            props: {
                bookmark: { type: Object, required: true },
            },

            emits: {
                menuToggle: (obj) => true,
            },

            setup(props, vm) {
                const onMenuToggle = () => {
                    vm.$emit('menuToggle', { item: props.bookmark, el: vm.$refs.bookmark_menu });
                }

                return {
                    bookmark: props.bookmark,
                    onMenuToggle,
                };
            },
        });

        document.addEventListener('alpine:init', () => {
            AlpineComposition.registerComponent(Alpine, Bookmark);
        });
    """

#####################################
# LIST
#####################################

@dataclass(frozen=True)
class ListItem:
    """
    Single menu item used with the `menu` components.

    Menu items can be divided by a horizontal line to indicate that the items
    belong together. In code, we specify this by wrapping the item(s) as an array.
    """

    value: Any
    """Value of the menu item to render."""

    link: Optional[str] = None
    """
    If set, the list item will be wrapped in an `<a>` tag pointing to this link.
    """

    attrs: Optional[dict] = None
    """Any additional attributes to apply to the list item."""

    meta: Optional[dict] = None
    """Any additional data to pass along the list item."""


@register("List")
class ListComponent(Component):
    def get_context_data(
        self,
        /,
        *,
        items: List[ListItem],
        attrs: Optional[dict] = None,
        item_attrs: Optional[dict] = None,
    ):
        return {
            "items": items,
            "attrs": attrs,
            "item_attrs": item_attrs,
        }

    template: types.django_html = """
        <ul role="list" {% html_attrs attrs class="flex flex-col gap-4" %}>
            {% for item in items %}
                <li {% html_attrs item.attrs item_attrs class="group flex justify-between gap-x-6 border border-gray-300 pl-4 pr-6 bg-white" %}>
                    <div class="flex min-w-0 w-full gap-x-4">
                        <div class="min-w-0 flex-auto">
                            {% if item.link %}
                            <a href="{{ item.link }}">
                            {% endif %}

                            <p class="text-sm font-semibold leading-6 text-gray-900 hover:text-gray-500">
                                {{ item.value }}
                            </p>

                            {% if item.link %}
                            </a>
                            {% endif %}
                        </div>
                    </div>
                </li>
            {% empty %}
                {% slot "empty" default / %}
            {% endfor %}
        </ul>
    """  # noqa: E501

#####################################
# TABS
#####################################

class TabEntry(NamedTuple):
    header: str
    content: str
    disabled: bool = False


class TabStaticEntry(NamedTuple):
    header: str
    href: str
    content: Optional[str]
    disabled: bool = False


@register("_tabs")
class _TabsImpl(Component):
    def get_context_data(
        self,
        /,
        *,
        tabs: List[TabEntry],
        # Unique name to identify this tabs instance, so we can open/close the tabs
        # based on the query params.
        name: Optional[str] = None,
        attrs: Optional[dict] = None,
        header_attrs: Optional[dict] = None,
        content_attrs: Optional[dict] = None,
    ):
        return {
            "attrs": attrs,
            "tabs": tabs,
            "header_attrs": header_attrs,
            "content_attrs": content_attrs,
            "tabs_data": {"name": name},
            "theme": theme,
        }

    template: types.django_html = """
        <div
            x-data="tabs"
            data-init="{{ tabs_data|json|escape }}"
            {% html_attrs attrs class="flex flex-col" %}
        >
            <ul class="flex border-b text-sm">
                {% for tab in tabs %}
                    {% if not tab.disabled %}
                        <li
                            @click="setOpenTab( {{ forloop.counter }} )"
                            :class="{
                                'border-b-2 {{ theme.tab_active }}': openTab === {{ forloop.counter }}
                            }"
                            {% html_attrs header_attrs %}
                        >
                            <a
                                href="#"
                                :class="openTab === {{ forloop.counter }} ? '{{ theme.tab_text_active }}' : '{{ theme.tab_text_inactive }}'"
                                class="bg-white inline-block py-2 px-4 font-semibold transition"
                            >
                                {{ tab.header }}
                            </a>
                        </li>
                    {% else %}
                        <li class="mr-1">
                            <p class="text-gray-300 bg-white inline-block py-2 px-4 font-semibold">
                                {{ tab.header }}
                            </p>
                        </li>
                    {% endif %}
                {% endfor %}
            </ul>
            <div class="w-full h-full flex-grow-1 relative overflow-y-scroll" x-ref="container">
                <article class="px-4 pt-5 absolute w-full h-full">
                    {% for tab in tabs %}
                        <div
                            x-show="openTab === {{ forloop.counter }}"
                            {% html_attrs content_attrs %}
                        >
                            {{ tab.content }}
                        </div>
                    {% endfor %}
                </article>
            </div>
        </div>
    """  # noqa: E501

    js: types.js = """
        document.addEventListener("alpine:init", () => {
            Alpine.data("tabs", () => ({
                // Variables
                openTab: 1,
                name: null,

                // Computed
                get tabQueryName() {
                    return `tabs-${this.name}`;
                },

                // Methods
                init() {
                    // If we provided the `name` argument to the "tabs" component, then
                    // we register a listener for the query param `tabs-{name}`.
                    // The value of this query param is the current active tab (index).
                    //
                    // When user changes the currently-open tab, we push that info to the URL
                    // by updating the `tabs-{name}` query param.
                    //
                    // And when we navigate to a URL that already had `tabs-{name}` query param
                    // set, we load that tab.
                    if (this.$el.dataset['init']) {
                        const { name } = JSON.parse(this.$el.dataset['init']);

                        if (name) {
                            this.name = name
                            app.query.registerParam(
                                this.tabQueryName,
                                (newVal, oldVal) => this.onTabQueryParamChange(newVal, oldVal),
                            );
                        }
                    }

                    // Sometimes, the scrollable tab content area is scrolled to the bottom
                    // when the page loads. So we ensure here that the we scroll to the top if not already
                    // Also see https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollTop
                    const containerEl = this.$refs.container;
                    if (containerEl.scrollTop) {
                        this.$refs.container.scrollTop = 0;
                    }
                },

                /**
                 * Set the current open tab and push the info to query params.
                 *
                 * @param {number} tabIndex
                 */
                setOpenTab(tabIndex) {
                    this.openTab = tabIndex;

                    if (this.name) {
                        app.query.setParams({ [this.tabQueryName]: tabIndex });
                    }
                },

                /**
                 * Handle tab change from URL
                 *
                 * @param {*} newValue
                 * @param {*} oldValue
                 */
                onTabQueryParamChange(newValue, oldValue) {
                    if (newValue == null) return;

                    const newValNum = typeof newValue === "number" ? newValue : Number.parseInt(newValue);
                    if (newValNum === this.openTab) return;

                    this.setOpenTab(newValNum);
                },
            }));
        });
    """


# This is an "API" component, meaning that it's designed to process
# user input provided as nested components. But after the input is
# processed, it delegates to an internal "implementation" component
# that actually renders the content.
@register("Tabs")
class Tabs(Component):
    def get_context_data(
        self,
        /,
        *,
        # Unique name to identify this tabs instance, so we can open/close the tabs
        # based on the query params.
        name: Optional[str] = None,
        attrs: Optional[dict] = None,
        header_attrs: Optional[dict] = None,
        content_attrs: Optional[dict] = None,
    ):
        return {
            "tabs": [],
            "name": name,
            "attrs": attrs,
            "header_attrs": header_attrs,
            "content_attrs": content_attrs,
            "tabs_data": {"name": name},
        }

    def on_render_after(self, context, template, rendered, error=None) -> str:
        # By the time we get here, all child TabItem components should have been
        # rendered, and they should've populated the tabs list.
        tabs: List[TabEntry] = context["tabs"]
        return _TabsImpl.render(
            kwargs={
                "tabs": tabs,
                "name": context["name"],
                "attrs": context["attrs"],
                "header_attrs": context["header_attrs"],
                "content_attrs": context["content_attrs"],
            },
            deps_strategy="ignore",
        )

    template: types.django_html = """
        {% provide "_tab" tabs=tabs enabled=True %}
            {% slot "content" default / %}
        {% endprovide %}
    """


# Use this component to define individual tabs inside the default slot
# inside the `tab` component.
@register("TabItem")
class TabItem(Component):
    def get_context_data(
        self,
        /,
        *,
        header: str,
        disabled: bool = False,
    ):
        # Access the list of tabs registered for parent Tabs component
        # This raises if we're not nested inside the Tabs component.
        tab_ctx = self.inject("_tab")

        # We accessed the _tab context, but we're inside ANOTHER TabItem
        if not tab_ctx.enabled:
            raise RuntimeError(
                f"Component '{self.name}' was called with no parent Tabs component. "
                f"Either wrap '{self.name}' in Tabs component, or check if the component "
                f"is not a descendant of another instance of '{self.name}'"
            )
        parent_tabs = tab_ctx.tabs

        return {
            "empty_tabs": [],
            "parent_tabs": parent_tabs,
            "header": header,
            "disabled": disabled,
        }

    def on_render_after(self, context, template, content, error=None) -> None:
        parent_tabs: List[dict] = context["parent_tabs"]
        parent_tabs.append({
            "header": context["header"],
            "disabled": context["disabled"],
            "content": mark_safe(content.strip()),
        })

    template: types.django_html = """
        {% provide "_tab" tabs=empty_tabs enabled=False %}
            {% slot "content" default / %}
        {% endprovide %}
    """


@register("TabsStatic")
class TabsStatic(Component):
    def get_context_data(
        self,
        /,
        *,
        tabs: List[TabStaticEntry],
        index: int = 0,
        hide_body: bool = False,
        attrs: Optional[dict] = None,
        header_attrs: Optional[dict] = None,
        content_attrs: Optional[dict] = None,
    ):
        selected_content = tabs[index].content

        tabs_data = []
        for tab_index, tab in enumerate(tabs):
            is_selectd = tab_index == index
            styling = {
                "tab": "border-b-2 " + theme.tab_active if is_selectd else "",
                "text": theme.tab_text_active if is_selectd else theme.tab_text_inactive,
            }
            tabs_data.append((tab, styling))

        return {
            "attrs": attrs,
            "tabs_data": tabs_data,
            "header_attrs": header_attrs,
            "content_attrs": content_attrs,
            "hide_body": hide_body,
            "selected_content": selected_content,
            "theme": theme,
        }

    template: types.django_html = """
        <div {% html_attrs attrs class="flex flex-col" %}>
            <ul class="flex border-b mb-5 bg-white">
                {% for tab, styling in tabs_data %}
                    {% if not tab.disabled %}
                        <li {% html_attrs header_attrs class="border-b-2" class=styling.tab %}>
                            <a
                                href="{{ tab.href }}"
                                {% html_attrs
                                    header_attrs
                                    class="bg-white inline-block py-2 px-4 font-semibold transition"
                                    class=styling.text
                                %}
                            >
                                {{ tab.header }}
                            </a>
                        </li>
                    {% else %}
                        <li class="mr-1">
                            <p class="text-gray-300 bg-white inline-block py-2 px-4 font-semibold">
                                {{ tab.header }}
                            </p>
                        </li>
                    {% endif %}
                {% endfor %}
            </ul>

            {% if not hide_body %}
                <div class="w-full h-full flex-grow-1 relative overflow-y-scroll">
                    <article class="px-4 pt-5 absolute w-full h-full">
                        <div {% html_attrs content_attrs %}>
                            {{ selected_content }}
                        </div>
                    </article>
                </div>
            {% endif %}
        </div>
    """


#####################################
# PROJECT_INFO
#####################################

class ProjectInfoEntry(NamedTuple):
    title: str
    value: str


@register("ProjectInfo")
class ProjectInfo(Component):
    def get_context_data(
        self,
        /,
        *,
        project: Project,
        project_tags: List[str],
        contacts: List[ProjectContact],
        status_updates: List[ProjectStatusUpdate],
        roles_with_users: List[ProjectRole],
        editable: bool,
    ):
        project_edit_url = f"/edit/{project['id']}/"
        edit_project_roles_url = f"/edit/{project['id']}/roles/"
        edit_contacts_url = f"/edit/{project['id']}/contacts/"
        create_status_update_url = f"/create/{project['id']}/status_update/"

        contacts_data = [
            {
                "contact": contact,
                "link_url": f"/contacts/{contact['link_id']}",
            }
            for contact in contacts
        ]

        project_info = [
            ProjectInfoEntry("Org", project['organization']['name']),
            ProjectInfoEntry("Duration", f"{project['start_date']} - {project['end_date']}"),
            ProjectInfoEntry("Status", project['status']),
            ProjectInfoEntry("Tags", ", ".join(project_tags) or "-"),
        ]

        return {
            "project_edit_url": project_edit_url,
            "edit_contacts_url": edit_contacts_url,
            "edit_project_roles_url": edit_project_roles_url,
            "create_status_update_url": create_status_update_url,
            "contacts_data": contacts_data,
            "project": project,
            "roles_with_users": roles_with_users,
            "project_info": project_info,
            "status_updates": status_updates,
            "editable": editable,
        }

    template: types.django_html = """
        <div class="prose flex flex-col gap-8">
            {# Info section #}
            <div class="border-b border-neutral-300">
                <div class="flex justify-between items-start">
                    <h3 class="mt-0">Project Info</h3>

                    {% if editable %}
                        {% component "Button"
                            href=project_edit_url
                            attrs:class="not-prose"
                        %}
                            Edit Project
                        {% endcomponent %}
                    {% endif %}
                </div>

                <table>
                    {% for key, value in project_info %}
                        <tr>
                            <td class="font-bold pr-4">
                                {{ key }}:
                            </td>
                            <td>
                                {{ value }}
                            </td>
                        </tr>
                    {% endfor %}
                </table>
            </div>

            {# Status Updates section #}
            {% component "ProjectStatusUpdates"
                project_id=project.id
                status_updates=status_updates
                editable=editable
            / %}
            <div class="xl:grid xl:grid-cols-2 gap-10">
                {# Team section #}
                <div class="border-b border-neutral-300">
                    <div class="flex justify-between items-start">
                        <h3 class="mt-0">Team</h3>

                        {% if editable %}
                            {% component "Button"
                                href=edit_project_roles_url
                                attrs:class="not-prose"
                            %}
                                Edit Team
                            {% endcomponent %}
                        {% endif %}
                    </div>

                    {% component "ProjectUsers"
                        project_id=project.id
                        roles_with_users=roles_with_users
                        available_roles=None
                        available_users=None
                        editable=False
                    / %}
                </div>

                {# Contacts section #}
                <div>
                    <div class="flex justify-between items-start max-xl:mt-6">
                        <h3 class="mt-0">Contacts</h3>

                        {% if editable %}
                            {% component "Button"
                                href=edit_contacts_url
                                attrs:class="not-prose"
                            %}
                                Edit Contacts
                            {% endcomponent %}
                        {% endif %}
                    </div>

                    {% if contacts_data %}
                        <table>
                            <tr>
                                <th>Name</th>
                                <th>Job</th>
                                <th>Link</th>
                            </tr>
                            {% for row in contacts_data %}
                                <tr>
                                    <td>{{ row.contact.name }}</td>
                                    <td>{{ row.contact.job }}</td>
                                    <td>
                                        {% component "Icon"
                                            href=row.link_url
                                            name="arrow-top-right-on-square"
                                            variant="outline"
                                            color="text-gray-400 hover:text-gray-500"
                                        / %}
                                    </td>
                                </tr>
                            {% endfor %}
                        </table>
                    {% else %}
                        <p class="text-sm italic">No entries</p>
                    {% endif %}
                </div>
            </div>
        </div>
    """

#####################################
# PROJECT_NOTES
#####################################

def _make_comments_data(note: ProjectNote, comment: ProjectNoteComment):
    modified_time_str = format_timestamp(datetime.fromisoformat(comment['modified']))
    formatted_modified_by = (
        modified_time_str
        + " "
        + comment['modified_by']['name']
    )

    return {
        "timestamp": formatted_modified_by,
        "notes": comment['text'],
        "edit_href": f"/update/{note['project']['id']}/note/{note['id']}/comment/{comment['id']}/",
    }


def _make_notes_data(
    notes: List[ProjectNote],
    comments_by_notes: Dict[int, List[ProjectNoteComment]],
):
    notes_data: List[dict] = []
    for note in notes:
        comments = comments_by_notes.get(note['id'], [])
        comments_data = [_make_comments_data(note, comment) for comment in comments]

        notes_data.append(
            {
                "text": note['text'],
                "timestamp": note['created'],
                "edit_href": f"/edit/{note['project']['id']}/note/{note['id']}/",
                "comments": comments_data,
                "create_comment_url": f"/create/{note['project']['id']}/note/{note['id']}/",
            }
        )

    return notes_data


@register("ProjectNotes")
class ProjectNotes(Component):
    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        notes: List[ProjectNote],
        comments_by_notes: Dict[int, List[ProjectNoteComment]],
        editable: bool,
    ):
        create_note_url = f"/create/{project_id}/note/"
        notes_data = _make_notes_data(notes, comments_by_notes)

        return {
            "create_note_url": create_note_url,
            "notes_data": notes_data,
            "editable": editable,
        }

    template: types.django_html = """
        <div class="prose">
            <h3>Notes</h3>
            {% if notes_data %}
                <div class="mt-8">
                    {% for note in notes_data %}
                        <div class="py-2" style="border-top: solid 1px lightgrey">
                            <div class="flex justify-between gap-4 pt-2">
                                <span class="prose-sm prose-figure">
                                    {{ note.timestamp }}
                                </span>
                                {% if editable %}
                                    {% component "Icon"
                                        name="pencil-square"
                                        variant="outline"
                                        href=note.edit_href
                                        color="text-gray-400 hover:text-gray-500"
                                    / %}
                                {% endif %}
                            </div>
                            <p class="my-0 text-gray-900">
                                {{ note.text }}
                            </p>

                            <details class="px-8 py-2">
                                <summary class="font-medium">
                                    Comments
                                </summary>

                                {% for comment in note.comments %}
                                    <div class="pl-8 pb-2" style="border-top: solid 1px grey;">
                                        <div class="flex justify-between gap-4 pt-2">
                                            <span class="prose-sm prose-figure">
                                                {{ comment.timestamp }}
                                            </span>
                                            {% if editable %}
                                                {% component "Icon"
                                                    name="pencil-square"
                                                    variant="outline"
                                                    href=comment.edit_href
                                                    color="text-gray-400 hover:text-gray-500"
                                                / %}
                                            {% endif %}
                                        </div>
                                        <div class="flex-auto">
                                            <p class="my-0">
                                                {{ comment.text }}
                                            </p>
                                        </div>
                                    </div>
                                {% endfor %}

                                <div class="text-right">
                                    {% if editable %}
                                        {% component "Button" href=note.create_comment_url %}
                                            Add comment
                                        {% endcomponent %}
                                    {% endif %}
                                </div>
                            </details>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}

            {% if editable %}
                {% component "Button" href=create_note_url %}
                    Add Note
                {% endcomponent %}
            {% endif %}
        </div>
    """


#####################################
# PROJECT_OUTPUTS_SUMMARY
#####################################

class AttachmentWithTags(NamedTuple):
    attachment: ProjectOutputAttachment
    tags: List[str]


class OutputWithAttachments(NamedTuple):
    output: ProjectOutput
    attachments: List[AttachmentWithTags]


class OutputWithAttachmentsAndDeps(NamedTuple):
    output: ProjectOutput
    attachments: List[AttachmentWithTags]
    dependencies: List[OutputWithAttachments]


@register("ProjectOutputsSummary")
class ProjectOutputsSummary(Component):
    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        outputs: List["OutputWithAttachmentsAndDeps"],
        editable: bool,
        phase_titles: Dict[ProjectPhaseType, str],
    ):
        outputs_by_phase = group_by(outputs, lambda output, _: output[0]['phase']['phase_template']['type'])

        groups: List[dict] = []
        for phase_meta in PROJECT_PHASES_META.values():
            phase_outputs = outputs_by_phase.get(phase_meta.type, [])
            title = phase_titles[phase_meta.type]
            groups.append(
                {
                    "phase_title": title,
                    "phase_type": phase_meta.type,
                    "outputs": phase_outputs,
                    "has_outputs": bool(phase_outputs),
                }
            )

        return {
            "project_id": project_id,
            "editable": editable,
            "groups": groups,
        }

    template: types.django_html = """
        <div class="flex flex-col gap-y-3">
            {% for group in groups %}
                {% component "ExpansionPanel"
                    open=group.has_outputs
                    header_attrs:class="flex gap-x-2 prose"
                %}
                    {% fill "header" %}
                        <h3 class="m-0">
                            {{ group.phase_title }}
                        </h3>
                    {% endfill %}

                    {% fill "content" %}
                        {% if group.outputs %}
                            {% component "ProjectOutputs"
                                outputs=group.outputs
                                project_id=project_id
                                phase_type=group.phase_type
                                editable=editable
                            / %}
                        {% else %}
                            No outputs
                        {% endif %}
                    {% endfill %}
                {% endcomponent %}
            {% endfor %}
        </div>
    """


#####################################
# PROJECT_STATUS_UPDATES
#####################################

def _make_status_update_data(status_update: ProjectStatusUpdate):
    modified_time_str = format_timestamp(datetime.fromisoformat(status_update['modified']))
    formatted_modified_by = (
        modified_time_str
        + " "
        + status_update['modified_by']['name']
    )

    return {
        "timestamp": formatted_modified_by,
        "text": status_update['text'],
        "edit_href": f"/edit/{status_update['project']['id']}/status_update/{status_update['id']}",
    }


@register("ProjectStatusUpdates")
class ProjectStatusUpdates(Component):

    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        status_updates: List[ProjectStatusUpdate],
        editable: bool,
    ):
        create_status_update_url = f"/create/{project_id}/status_update"

        updates_data = [_make_status_update_data(status_update) for status_update in status_updates]

        return {
            "create_status_update_url": create_status_update_url,
            "updates_data": updates_data,
            "editable": editable,
        }

    template: types.django_html = """
        <div class="prose border-b border-neutral-300 pb-8">
            <div class="flex justify-between items-start mb-4">
                <h3 class="mt-0">Status Updates</h3>
                {% if editable %}
                    {% component "Button" href=create_status_update_url %}
                        Add status update
                    {% endcomponent %}
                {% endif %}
            </div>
            {% if updates_data %}
                <div class="mt-8">
                    {% for update in updates_data %}
                        <div class="px-3 py-2" style="border-top: solid 1px lightgrey">
                            <div class="flex justify-between gap-4 pt-2">
                                <span class="prose-sm prose-figure">
                                    {{ update.timestamp }}
                                </span>
                                {% if editable %}
                                    {% component "Icon"
                                        name="pencil-square"
                                        variant="outline"
                                        href=update.edit_href
                                        color="text-gray-400 hover:text-gray-500"
                                    / %}
                                {% endif %}
                            </div>
                            <p class="my-0 text-gray-900">
                                {{ update.text }}
                            </p>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    """


#####################################
# PROJECT USERS
#####################################

roles_table_headers = [
    TableHeader(key="name", name="Name"),
    TableHeader(key="role", name="Role"),
    TableHeader(key="delete", name="", hidden=True),
]


class ProjectAddUserForm(ConditionalEditForm):
    user_id = forms.ChoiceField(required=True, choices=[], label="User")
    role = forms.ChoiceField(required=True, choices=[])

    def __init__(
        self,
        editable: bool,
        available_role_choices: List[Tuple[str, str]],
        available_user_choices: List[Tuple[str, str]],
        *args,
        **kwargs,
    ):
        self.editable = editable

        super().__init__(*args, **kwargs)

        user_field: forms.ChoiceField = self.fields["user_id"]  # type: ignore[assignment]
        user_field.choices = available_user_choices

        role_field: forms.ChoiceField = self.fields["role"]  # type: ignore[assignment]
        role_field.choices = available_role_choices


@register("ProjectUsers")
class ProjectUsers(Component):
    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        roles_with_users: List[ProjectRole],
        available_roles: Optional[List[str]],
        available_users: Optional[List[User]],
        editable: bool = False,
    ):
        roles_table_rows = []
        for role in roles_with_users:
            user = role['user']

            if editable:
                delete_action = ProjectUserAction.render(
                    kwargs={
                        "user_name": user['name'],
                        "project_id": project_id,
                        "role_id": role['id'],
                    },
                    deps_strategy="ignore",
                )
            else:
                delete_action = ""

            roles_table_rows.append(
                create_table_row(
                    cols={
                        "name": TableCell(user['name']),
                        "role": TableCell(role['name']),
                        "delete": delete_action,
                    }
                )
            )

        submit_url = f"/submit/{project_id}/role/create"
        project_url = f"/project/{project_id}"

        if available_roles:
            available_role_choices = [
                (role, role) for role in available_roles
            ]
        else:
            available_role_choices = []

        if available_users:
            available_user_choices = [
                (str(user['id']), user['name']) for user in available_users
            ]
        else:
            available_user_choices = []

        return {
            "editable": editable,
            "table_headers": roles_table_headers,
            "table_rows": roles_table_rows,
            "add_user_form": ProjectAddUserForm(
                editable,
                available_role_choices,
                available_user_choices,
            ),
            "submit_url": submit_url,
            "project_url": project_url,
        }

    template: types.django_html = """
        <div x-data="project_users">
            {% if table_rows %}
                {% component "Table"
                    headers=table_headers
                    rows=table_rows
                    attrs:@user_delete="onUserDelete"
                / %}
            {% endif %}

            {% if editable %}
                <h4>Set project roles</h4>

                <form
                    hx-post="{{ submit_url }}"
                    hx-swap="outerHTML"
                    method="post"
                >
                    <table>
                        {{ add_user_form.as_table }}
                    </table>

                    {% component "Button" type="submit" %}
                        Set role
                    {% endcomponent %}
                    {% component "Button" variant="secondary" href=project_url %}
                        Go back
                    {% endcomponent %}
                </form>

                <template x-if="role && isDeleteDialogOpen">
                    {% component "Dialog"
                        model="isDeleteDialogOpen"
                        confirm_text="Delete"
                        confirm_href='#'
                        confirm_color="error"
                        confirm_attrs::href="role.delete_url"
                        content_attrs:class="w-full"
                    %}
                        {% fill "title" %}
                            <div class="flex">
                                <span>
                                    Remove
                                    <span x-text="role && role.user_name"></span>
                                    from this project?
                                </span>
                                {% component "Icon"
                                    name="trash"
                                    variant="outline"
                                    size=18
                                    attrs:class="p-2 self-center"
                                / %}
                            </div>
                        {% endfill %}

                        {% fill "content" %}
                            <div>
                                This action cannot be undone.
                            </div>
                        {% endfill %}

                    {% endcomponent %}
                </template>
            {% endif %}
        </div>
    """

    js: types.js = """
        document.addEventListener('alpine:init', () => {
            Alpine.data('project_users', () => ({
                // Variables
                isDeleteDialogOpen: false,
                role: null,

                // Methods
                onUserDelete(event) {
                    const { role } = event.detail;

                    this.role = role;
                    this.isDeleteDialogOpen = !!role;
                },
            }));
        });
    """

#####################################
# PROJECT_USER_ACTION
#####################################

@register("ProjectUserAction")
class ProjectUserAction(Component):

    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        role_id: int,
        user_name: str,
    ):
        delete_url = f"/delete/{project_id}/{role_id}"

        role_data = {
            "delete_url": delete_url,
            "role_id": role_id,
            "user_name": user_name,
        }

        return {
            "role": role_data,
        }

    template: types.django_html = """
        <div x-data="{
            role: {{ role | alpine }},
        }">
            {% component "Icon"
                name="trash"
                variant="outline"
                size=18
                href="#"
                color="text-gray-500 hover:text-gray-400"
                svg_attrs:class="inline mb-1"
                attrs:class="p-2"
                attrs:@click.stop="$dispatch('user_delete', { role })"
            / %}
        </div>
    """

#####################################
# PROJECT_OUTPUTS
#####################################


@register("ProjectOutputs")
class ProjectOutputs(Component):

    def get_context_data(
        self,
        /,
        *,
        project_id: int,
        phase_type: str,
        outputs: List[OutputWithAttachmentsAndDeps],
        editable: bool,
    ) -> Any:
        outputs_data: List[RenderedProjectOutput] = []
        for output_tuple in outputs:
            output, attachments, dependencies = output_tuple

            attach_data: List[RenderedAttachment] = []
            for attachment in attachments:
                attach_data.append(RenderedAttachment(
                    url=attachment[0]['url'],
                    text=attachment[0]['text'],
                    tags=attachment[1],
                ))

            update_output_url = "/update"

            deps: List[RenderedOutputDep] = []
            for dep in dependencies:
                output, attachments = dep
                phase_url = f"/phase/{project_id}/{output['phase']['phase_template']['type']}"
                deps.append(
                    RenderedOutputDep(
                        dependency=dep,
                        phase_url=phase_url,
                        attachments=[
                            {
                                "url": d.attachment['url'],
                                "text": d.attachment['text'],
                                "tags": d.tags,
                            }
                            for d in attachments
                        ],
                    )
                )

            has_missing_deps = any(
                [not output['completed'] for output, _ in dependencies]
            )

            outputs_data.append(
                RenderedProjectOutput(
                    output=output,
                    dependencies=deps,
                    has_missing_deps=has_missing_deps,
                    output_data={
                        "editable": editable,
                    },
                    attachments=attach_data,
                    update_output_url=update_output_url,
                )
            )

        return {
            "outputs_data": outputs_data,
            "editable": editable,
        }

    template: types.django_html = """
        <div class="flex flex-col">
            {% for data in outputs_data %}
                <div class="flex gap-x-3">
                    <div>
                        {% component "ProjectOutputBadge"
                            completed=data.output.completed
                            missing_deps=data.has_missing_deps
                        / %}
                    </div>
                    <div class="w-full">
                        {% component "ExpansionPanel"
                            panel_id=data.output.id
                            icon_position="right"
                            attrs:class="border-b border-solid border-gray-300 pb-2 mb-3"
                            header_attrs:class="flex align-center justify-between"
                        %}
                            {% fill "header" %}
                                <div>
                                    {{ data.output.name }}
                                </div>
                            {% endfill %}

                            {% fill "content" %}
                                <div>
                                    {# Dependencies #}
                                    {% for dep in data.dependencies %}
                                        {% component "ProjectOutputDependency" dependency=dep / %}
                                    {% endfor %}

                                    {# Own data + attachments #}
                                    {% component "ProjectOutputForm" data=data editable=editable / %}
                                </div>
                            {% endfill %}
                        {% endcomponent %}
                    </div>
                </div>
            {% endfor %}
        </div>
    """

#####################################
# PROJECT_OUTPUT_BADGE
#####################################

@register("ProjectOutputBadge")
class ProjectOutputBadge(Component):
    def get_context_data(
        self,
        /,
        *,
        completed: bool,
        missing_deps: bool,
    ):
        return {
            "completed": completed,
            "missing_deps": missing_deps,
            "theme": theme,
        }

    template: types.django_html = """
        <span class="flex h-9 items-center">
            {# Missing dependencies #}
            {% if missing_deps %}
                {% component "Icon"
                    name="exclamation-triangle"
                    variant="outline"
                    color="text-black"
                    size=32
                    stroke_width=2
                    attrs:title="A dependent dependency has not been met!"
                / %}

            {# Completed #}
            {% elif completed %}
                <span class="relative z-10 flex h-8 w-8 items-center justify-center rounded-full {{ theme.check_interactive }}">
                    {% component "Icon"
                        name="check"
                        variant="outline"
                        color="text-white"
                        size=20
                        stroke_width=2
                        attrs:class="p-2"
                    / %}
                </span>

            {# NOT completed #}
            {% else %}
                <span class="flex h-9 items-center" aria-hidden="true">
                    <span class="relative z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 border-gray-300 bg-white">
                    </span>
                </span>
            {% endif %}
        </span>
    """  # noqa: E501

#####################################
# PROJECT_OUTPUT_DEPENDENCY
#####################################

@register("ProjectOutputDependency")
class ProjectOutputDependency(Component):
    def get_context_data(self, /, *, dependency: "RenderedOutputDep"):
        return {
            "attachments": dependency.attachments,
            "dependency": dependency.dependency,
            "phase_url": dependency.phase_url,
            "OUTPUT_DESCRIPTION_PLACEHOLDER": OUTPUT_DESCRIPTION_PLACEHOLDER,
        }

    template: types.django_html = """
        <div
            class="pb-3 mb-3 border-b border-solid border-gray-300"
            x-data="project_output_dependency"
            x-props="{
                initAttachments: '{{ attachments|json|escape }}'
            }"
        >
            <div class="w-full bg-gray-100 text-sm p-2" style="min-height: 100px;">
                {% if dependency.output.completed %}
                    {% if dependency.output.description %}
                        {{ dependency.output.description }}
                    {% else %}
                        <span class="italic text-gray-500">
                            {{ OUTPUT_DESCRIPTION_PLACEHOLDER }}
                        </span>
                    {% endif %}
                {% else %}
                    <span class="text-gray-500 italic">
                        {% component "Icon"
                            name="exclamation-triangle"
                            variant="outline"
                            size=24
                            stroke_width=2
                            color="text-gray-500"
                            attrs:class="float-left pr-1"
                        / %}

                        Missing '{{ dependency.output.name }}' from

                        {% component "Button"
                            variant="plain"
                            href=phase_url
                            attrs:target="_blank"
                            attrs:class="hover:text-gray-600 !underline"
                        %}
                            {{ dependency.output.phase.phase_template.type|title }}
                        {% endcomponent %}
                    </span>
                {% endif %}
            </div>

            {# Attachments of parent dependencies #}
            {% component "ProjectOutputAttachments"
                editable=False
                has_attachments=dependency.attachments
                js_props:attachments="attachments.value"
            / %}
        </div>
    """

    js: types.js = """
        // Define component similarly to defining Vue components
        const ProjectOutputDependency = AlpineComposition.defineComponent({
            name: 'project_output_dependency',

            props: {
                initAttachments: { type: String, required: true },
            },

            // Instead of Alpine's init(), use setup()
            // Props are passed down as reactive props, same as in Vue
            // Second argument is the Alpine component instance.
            setup(props, vm, { ref }) {
                const attachments = ref([]);

                // Set the initial state from HTML
                if (props.initAttachments) {
                    attachments.value = JSON.parse(props.initAttachments).map(({ url, text, tags }) => ({
                        url,
                        text,
                        tags,
                        isPreview: true,
                    }));
                }

                // Only those variables exposed by returning can be accessed from within HTML
                return {
                    attachments,
                };
            },
        });

        document.addEventListener('alpine:init', () => {
            AlpineComposition.registerComponent(Alpine, ProjectOutputDependency);
        });
    """

#####################################
# PROJECT_OUTPUT_ATTACHMENTS
#####################################

class ProjectOutputAttachmentsJsProps(TypedDict):
    attachments: str


@register("ProjectOutputAttachments")
class ProjectOutputAttachments(Component):
    def get_context_data(
        self,
        /,
        *,
        has_attachments: bool,
        js_props: ProjectOutputAttachmentsJsProps,
        editable: bool,
        attrs: Optional[dict] = None,
    ):
        return {
            "has_attachments": has_attachments,
            "editable": editable,
            "attrs": attrs,
            "js_props": js_props,
            "text_max_len": FORM_SHORT_TEXT_MAX_LEN,
            "tag_type": "project_output_attachment",
        }

    template: types.django_html = """
        <div
            x-data="project_output_attachments"
            x-props="{
                ...{{ js_props|js }},
            }"
            {% html_attrs attrs class="pt-3 flex flex-col gap-y-3 items-start" %}
        >
            <div>
                {% if not has_attachments and editable %}
                    This output does not have any attachments, create one below:
                {% elif not has_attachments and not editable %}
                    This output does not have any attachments.
                {% elif has_attachments and not editable %}
                    Attachments:
                {% else %} {# NOTE: Else branch required by django-shouty #}
                {% endif %}
            </div>

            <template x-for="(attachment, index) in attachments.value">
                <div class="project-output-form-attachment w-full">
                    <div class="text-sm flex gap-3 w-full justify-between">
                        {# Attachment preview #}
                        <div x-show="attachment.isPreview">
                            {% component "Button"
                                variant="plain"
                                link=True
                                attrs:x-bind:href="attachment.url"
                                attrs:x-text="attachment.text"
                                attrs:target="_blank"
                                attrs:class="hover:text-gray-600 !underline"
                                attrs:style="color: cornflowerblue;"
                            / %}
                        </div>

                        {# Attachment form #}
                        <div x-show="!attachment.isPreview" class="flex flex-col gap-1">
                            <label for="id_text">Text:</label>
                            <input
                                type="text"
                                name="text"
                                id="id_text"
                                maxlength="{{ text_max_len }}"
                                required
                                {% if not editable %} disabled {% endif %}
                                class="text-sm py-1 px-2"
                                :value="attachment.text"
                                @change="(ev) => $emit('updateAttachmentData', index, { text: ev.target.value })"
                            >

                            <label for="id_url">Url:</label>
                            <input
                                type="url"
                                name="url"
                                id="id_url"
                                required
                                {% if not editable %} disabled {% endif %}
                                class="text-sm py-1 px-2"
                                :value="attachment.url"
                                @change="(ev) => $emit('updateAttachmentData', index, { url: ev.target.value })"
                            >
                        </div>

                        {% if editable %}
                            <div class="flex gap-2 flex-wrap justify-end">
                                <div>
                                    {% component "Button"
                                        attrs:class="!py-1"
                                        attrs:x-text="attachment.isPreview ? 'Edit' : 'Preview'"
                                        attrs:@click="() => $emit('toggleAttachment', index)"
                                    %}
                                        Edit
                                    {% endcomponent %}
                                </div>

                                <div>
                                    {% component "Button"
                                        color="error"
                                        attrs:class="!py-1"
                                        attrs:@click="() => $emit('removeAttachment', index)"
                                    %}
                                        Remove
                                    {% endcomponent %}
                                </div>
                            </div>
                        {% endif %}
                    </div>

                    {% component "Tags"
                        tag_type=tag_type
                        editable=editable
                        js_props:initTags="attachment.tags"
                        js_props:onChange="(tags) => $emit('setAttachmentTags', index, tags)"
                        attrs:class="pb-8"
                    / %}
                </div>
            </template>
        </div>
    """

    js: types.js = """
        const ProjectOutputAttachments = AlpineComposition.defineComponent({
            name: "project_output_attachments",

            props: {
                attachments: { type: Object, required: true },
            },

            emits: {
                updateAttachmentData: (index, data) => true,
                setAttachmentTags: (index, tags) => true,
                removeAttachment: (index) => true,
                toggleAttachment: (index) => true,
            },

            setup(props, vm, { toRefs, watch }) {
                const { attachments } = toRefs(props);

                return {
                    attachments,
                };
            },
        });

        document.addEventListener("alpine:init", () => {
            AlpineComposition.registerComponent(Alpine, ProjectOutputAttachments);
        });
    """


#####################################
# PROJECT_OUTPUT_FORM
#####################################

OUTPUT_DESCRIPTION_PLACEHOLDER = "Placeholder text"


class RenderedAttachment(NamedTuple):
    url: str
    text: str
    tags: List[str]


class RenderedOutputDep(NamedTuple):
    dependency: OutputWithAttachments
    phase_url: str
    attachments: List[dict]


class RenderedProjectOutput(NamedTuple):
    output: ProjectOutput
    dependencies: List[RenderedOutputDep]
    has_missing_deps: bool
    output_data: dict
    attachments: List[RenderedAttachment]
    update_output_url: str


@register("ProjectOutputForm")
class ProjectOutputForm(Component):
    def get_context_data(
        self,
        /,
        *,
        data: RenderedProjectOutput,
        editable: bool,
    ):
        return {
            "data": data,
            "editable": editable,
            "alpine_attachments": [d._asdict() for d in data.attachments],
            "OUTPUT_DESCRIPTION_PLACEHOLDER": OUTPUT_DESCRIPTION_PLACEHOLDER,
        }

    template: types.django_html = """
        <div
            x-data="project_output_form"
            x-props="{
                initAttachments: '{{ alpine_attachments|json|escape }}'
            }"
        >
            {% component "Form"
                submit_href=data.update_output_url
                actions_hide=True
            %}
                {# Output description - editable #}
                {% if editable %}
                    <textarea
                        name="description"
                        class="w-full text-sm p-2 mb-2"
                        placeholder="{{ OUTPUT_DESCRIPTION_PLACEHOLDER }}"
                        style="min-height: 100px;"
                    >{{ data.output.description }}</textarea>
                {% else %}
                    {# Output description - readonly #}
                    <div
                        class="w-full bg-gray-100 italic text-gray-500 text-sm p-2 mb-2"
                        style="min-height: 100px;"
                    >
                        {% if data.output.description %}
                            {{ data.output.description }}
                        {% else %}
                            {{ OUTPUT_DESCRIPTION_PLACEHOLDER }}
                        {% endif %}
                    </div>
                {% endif %}

                <div class="flex flex-wrap justify-between items-center gap-y-3">
                    <div class="flex items-center gap-x-2">
                        Completed:

                        {# NOTE: See https://stackoverflow.com/a/1992745/9788634 #}
                        <input type='hidden' value='0' name='completed'
                            {% if not editable %} disabled {% endif %}
                        >
                        <input type="checkbox"
                            name="completed"
                            style="height: 20px; width: 20px"
                            {% if data.output.completed %} checked {% endif %}
                            {% if not editable %} disabled {% endif %}
                        />
                    </div>
                    <div class="flex gap-x-2 ml-auto items-center justify-between {% if editable %} basis-52 {% endif %}">
                        {% if editable %}
                            {% component "Button"
                                variant="secondary"
                                attrs:@click="addAttachment"
                            %}
                                Add attachment
                            {% endcomponent %}

                            {% component "Button"
                                attrs:@click="onOutputSubmit({ reload: true })"
                            %}
                                Save
                            {% endcomponent %}
                        {% endif %}
                    </div>
                </div>

                {% component "ProjectOutputAttachments"
                    has_attachments=data.attachments
                    editable=editable
                    js_props:attachments="attachments.value"
                    js_props:onToggleAttachment="(index) => toggleAttachmentPreview(index)"
                    js_props:onSetAttachmentTags="(index, tags) => setAttachmentTags(index, tags)"
                    js_props:onUpdateAttachmentData="(index, data) => updateAttachmentData(index, data)"
                    js_props:onRemoveAttachment="(index) => removeAttachment(index)"
                / %}
            {% endcomponent %}
        </div>
    """  # noqa: E501

    js: types.js = """
        // Define component similarly to defining Vue components
        const ProjectOutputForm = AlpineComposition.defineComponent({
            name: 'project_output_form',

            props: {
                initAttachments: { type: String, required: true },
            },

            // Instead of Alpine's init(), use setup()
            // Props are passed down as reactive props, same as in Vue
            // Second argument is the Alpine component instance.
            setup(props, vm, { ref, nextTick, watch }) {
                const attachments = ref([]);

                // Set the initial state
                if (props.initAttachments) {
                    attachments.value = JSON.parse(props.initAttachments).map(({ url, text, tags }) => ({
                        url,
                        text,
                        isPreview: true,
                        tags,
                    }));
                }

                watch(attachments, () => {
                    onAttachmentsChange();
                }, { immediate: true });

                // Methods
                const addAttachment = () => {
                    attachments.value = [...attachments.value, { url: "", text: "", tags: [], isPreview: false }];
                };

                const removeAttachment = (index) => {
                    attachments.value = attachments.value.filter((_, i) => i !== index);

                    // NOTE: For unknown reason, AlpineJS removes the attachment from for-loop
                    // only on second click. So we do so ourselves
                    const attachmentEls = [...vm.$el.querySelectorAll('.project-output-form-attachment')];
                    if (attachmentEls.length > attachments.value.length) {
                        attachmentEls[index].remove();
                    }

                    // Send the request to remove the attachment in the server too, but
                    // don't yet reload the page in case user is editing other attachments.
                    onOutputSubmit({ reload: false });
                };

                const setAttachmentTags = (index, tags) => {
                    attachments.value = attachments.value.map((attach, currIndex) => {
                        if (index !== currIndex) return attach;

                        return { ...attach, tags };
                    });
                };

                const updateAttachmentData = (index, data) => {
                    attachments.value = attachments.value.map((attach, currIndex) => {
                        if (index !== currIndex) return attach;

                        return { ...attach, ...data };
                    });
                };

                const toggleAttachmentPreview = (index) => {
                    let didCloseEditing = false;

                    attachments.value = attachments.value.map((attach, i) => {
                        if (index === i) {
                            attach.isPreview = !attach.isPreview;

                            if (attach.isPreview) didCloseEditing = true;
                        }
                        return attach;
                    });

                    if (didCloseEditing) onOutputSubmit({ reload: false });
                };

                // When attachments are added or removed, we add/remove HTML by AlpineJS,
                // so user doesn't have to refresh the page.
                function onAttachmentsChange() {
                    // We wait until the HTML is updated...
                    nextTick(() => {
                        // ...Then populate the generated HTML
                        const attachmentEls = [...vm.$el.querySelectorAll('.project-output-form-attachment')];
                        attachmentEls.forEach((attachEl, index) => {
                            if (index >= attachments.value.length) return;

                            const attachment = attachments.value[index];
                            attachEl.querySelector('input[name="url"]').value = attachment.url;
                            attachEl.querySelector('input[name="text"]').value = attachment.text;
                        });
                    });
                }

                const onOutputSubmit = ({ reload }) => {
                    /** @type {HTMLFormElement} */
                    const formEl = vm.$el.querySelector('form');
                    const formData = Object.fromEntries(new FormData(formEl));
                    const data = {
                        description: formData.description,
                        completed: formData.completed.toLowerCase() === "on",
                        attachments: attachments.value.map(({ text, url, tags }) => ({ text, url, tags })),
                    };

                    axios.post(formEl.action, data, {
                        method: formEl.method,
                    })
                        .then((response) => {
                            if (reload) location.reload();
                        })
                        .catch((error) => {
                            console.error(error);
                        });
                };

                return {
                    attachments,
                    addAttachment,
                    removeAttachment,
                    setAttachmentTags,
                    updateAttachmentData,
                    toggleAttachmentPreview,
                    onOutputSubmit,
                };
            },
        });

        document.addEventListener('alpine:init', () => {
            AlpineComposition.registerComponent(Alpine, ProjectOutputForm);
        });
    """


#####################################
#
# IMPLEMENTATION END
#
#####################################

# DO NOT REMOVE - See https://github.com/django-components/django-components/pull/999
# ----------- TESTS START ------------ #
# The code above is used also used when benchmarking.
# The section below is NOT included.

from django_components.testing import djc_test  # noqa: E402

@djc_test
def test_render(snapshot):
    registry.register("Button", Button)
    registry.register("Menu", Menu)
    registry.register("MenuList", MenuList)
    registry.register("Table", Table)
    registry.register("Icon", Icon)
    registry.register("heroicons", HeroIcon)
    registry.register("ExpansionPanel", ExpansionPanel)
    registry.register("ProjectPage", ProjectPage)
    registry.register("ProjectLayoutTabbed", ProjectLayoutTabbed)
    registry.register("Layout", Layout)
    registry.register("RenderContextProvider", RenderContextProvider)
    registry.register("Base", Base)
    registry.register("Sidebar", Sidebar)
    registry.register("Navbar", Navbar)
    registry.register("Dialog", Dialog)
    registry.register("Tags", Tags)
    registry.register("Form", Form)
    registry.register("Breadcrumbs", Breadcrumbs)
    registry.register("Bookmarks", Bookmarks)
    registry.register("Bookmark", Bookmark)
    registry.register("List", ListComponent)
    registry.register("_tabs", _TabsImpl)
    registry.register("Tabs", Tabs)
    registry.register("TabItem", TabItem)
    registry.register("TabsStatic", TabsStatic)
    registry.register("ProjectInfo", ProjectInfo)
    registry.register("ProjectNotes", ProjectNotes)
    registry.register("ProjectOutputsSummary", ProjectOutputsSummary)
    registry.register("ProjectStatusUpdates", ProjectStatusUpdates)
    registry.register("ProjectUsers", ProjectUsers)
    registry.register("ProjectUserAction", ProjectUserAction)
    registry.register("ProjectOutputs", ProjectOutputs)
    registry.register("ProjectOutputBadge", ProjectOutputBadge)
    registry.register("ProjectOutputDependency", ProjectOutputDependency)
    registry.register("ProjectOutputAttachments", ProjectOutputAttachments)
    registry.register("ProjectOutputForm", ProjectOutputForm)

    data = gen_render_data()
    rendered = render(data)
    assert rendered == snapshot
