# Django Components People

Django Components has reached its current form thanks to the passion and efforts of its outstanding contributors and maintainers.

## Maintainers

These are the maintainers who play a key role in keeping Django Components running.

{% if people.maintainers %}
<div class="user-list">
{% for user in people.maintainers %}
<div class="user">
    <a href="{{ user.url }}" target="_blank">
        <div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div>
        <div class="title">@{{ user.login }}</div>
    </a>
</div>
{% endfor %}
</div>
{% endif %}

## Contributors

These are the individual contributors who help make Django Components better for everyone.

{% if people.contributors %}
<div class="user-list">
{% for user in people.contributors %}
<div class="user">
    <a href="{{ user.url }}" target="_blank">
        <div class="avatar-wrapper"><img src="{{ user.avatarUrl }}"/></div>
        <div class="title">@{{ user.login }}</div>
    </a>
    <div class="info">Contributions: {{ user.count }}</div>
</div>
{% endfor %}
</div>
{% endif %}
