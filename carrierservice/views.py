from carrierservice.models import Package
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from rest_framework.decorators import api_view
import requests
from carrierservice.services.llm import generate_mail
from carrierservice.services.predictor import predict_delivery
import os
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def index_view(request):
    return render(request, "index.html")


def get_tracking_status(tracking_number):
    try:
        url=os.getenv("DHL_SHIPMENT_TRACKING")
        api_key=os.getenv("DHL_API_KEY")
        response=requests.get(url,params={"trackingNumber":tracking_number},headers={"DHL-API-Key":api_key})
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@api_view(['POST'])
def Track_shipment(request):
    try:
        package, created = Package.objects.get_or_create(
            tracking_number=request.data.get("tracking_number"),
            defaults={
                'email': request.data.get("email"),
                'carrier': request.data.get("carrier"),
            }
        )
        
        status_data = get_tracking_status(request.data.get("tracking_number"))

        # --- AI ETA Prediction ---
        ai_prediction = None
        try:
            ai_prediction = predict_delivery(status_data)
            logger.info(f"ETA prediction for {request.data.get('tracking_number')}: "
                        f"{ai_prediction.get('estimated_delivery')} "
                        f"(confidence: {ai_prediction.get('confidence')}%)")
        except Exception as pred_err:
            logger.warning(f"ETA prediction failed: {pred_err}")

        # Merge prediction into response
        response_data = dict(status_data)
        response_data["ai_prediction"] = ai_prediction

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

