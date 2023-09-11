from django.urls import path
from payment import views

app_name = 'payments'

urlpatterns = [
    path('yookassa_callback/', views.YooPaymentCallBackView.as_view(), name='yoo_callback')
]
