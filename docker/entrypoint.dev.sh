#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

if [ "$AUTH_BACKEND" = "keycloak" ]
then
    echo "Waiting for keycloak..."

    while ! nc -z $KEYCLOAK_HOST $KEYCLOAK_PORT; do
      sleep 0.1
    done

    echo "Keycloak started"
fi

python manage.py flush --no-input
python manage.py migrate
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('$DJANGO_ADMIN_USER', '$DJANGO_ADMIN_EMAIL', '$DJANGO_ADMIN_PASSWORD')" | python manage.py shell
python manage.py collectstatic --no-input --clear

exec "$@"