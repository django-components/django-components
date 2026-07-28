"""
UserGrid - avatar grid for the community People page.

Renders a centered, wrapping grid of GitHub users (avatar, @handle, and
optionally a contribution count). Used by the {% people %} template tag,
which replaces the old mkdocs-macros Jinja loop in community/people.md.

Spec: docs_site/design/DESIGN_spike_9.md section 2.7 (feature 3b.6).
"""

from __future__ import annotations

from typing import Any

from django_components import Component, register, types


@register("user_grid")
class UserGrid(Component):
    class Kwargs:
        # Each user is a dict from people.yml: {login, avatarUrl, url, count?}
        users: list
        show_count: bool = False

    template: types.django_html = """
        <div class="user-list">
            {% for user in users %}
            <div class="user">
                <a href="{{ user.url }}" target="_blank" rel="noopener">
                    <div class="avatar-wrapper">
                        <img src="{{ user.avatarUrl }}" alt="GitHub avatar of {{ user.login }}">
                    </div>
                    <div class="title">@{{ user.login }}</div>
                </a>
                {% if show_count %}
                <div class="info">Contributions: {{ user.count }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict:
        return {
            "users": kwargs.users,
            "show_count": kwargs.show_count,
        }
