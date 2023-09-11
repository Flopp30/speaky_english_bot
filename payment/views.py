import json

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt


class YooPaymentCallBackView(View):
    # payment.canceled

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode("utf-8"))
        event = data.get('event')
        match event:
            case "payment.succeeded":
                verified_payment_id = data.get('object', {}).get('payment_method', {}).get('id', None)
                print(verified_payment_id)
            case "payment.canceled" | "refund.succeeded":
                print(data)
        return JsonResponse({"status": "success"})
