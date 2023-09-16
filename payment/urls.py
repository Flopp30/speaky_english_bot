from django.urls import path
from payment import views
from payment.views import RefundCreateView

app_name = 'payments'

urlpatterns = [
    path('yookassa_callback/', views.YooPaymentCallBackView.as_view(), name='yoo_callback'),
    path('refund/create/', RefundCreateView.as_view(), name='refund_create')
]
