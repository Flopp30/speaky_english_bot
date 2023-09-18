from django.urls import path

from user.views import SendMessageView

app_name = 'users'

urlpatterns = [
    path('send_message/', SendMessageView.as_view(), name='send_message')
]
