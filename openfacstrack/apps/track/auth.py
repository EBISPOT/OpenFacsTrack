from django.contrib.auth.models import User, Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class TrackOIDCAB(OIDCAuthenticationBackend):
    def create_user(self, claims):
        user: User = super(TrackOIDCAB, self).create_user(claims)

        user.username = claims.get("preferred_username", "")
        user.email = claims.get("email", "")
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.is_staff = "admin" in claims.get("group", [])
        for group_name in claims.get("group", []):
            user_group = Group.objects.get(name=group_name)
            user_group.user_set.add(user)
        user.save()
        print(user)
        print(claims)
        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", "")
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.is_staff = "admin" in claims.get("group", [])
        user.save()

        return user
