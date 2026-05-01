from carrierservice.models import Package
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.core.cache import cache
import requests
from carrierservice.services.llm import generate_mail
from carrierservice.services.predictor import predict_delivery
from carrierservice.services.agent import ask_agent
import os
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def index_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "login.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Logic: If "Remember Me" is checked, keep the session for 2 weeks.
            # Otherwise, it expires when the browser closes.
            if not request.POST.get('remember_me'):
                request.session.set_expiry(0) # Browser close
            else:
                request.session.set_expiry(1209600) # 2 weeks in seconds
                
            return redirect('dashboard')
        else:
            return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Username already exists"})
        
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('dashboard')
    return render(request, "signup.html")

@login_required
def dashboard_view(request):
    packages = Package.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, "dashboard.html", {"packages": packages})

def logout_view(request):
    logout(request)
    return redirect('home')


def get_tracking_status(tracking_number):
    try:
        url=os.getenv("DHL_SHIPMENT_TRACKING")
        api_key=os.getenv("DHL_API_KEY")
        response=requests.get(url,params={"trackingNumber":tracking_number},headers={"DHL-API-Key":api_key})
        return response.json()
    except Exception as e:
        return {"error": str(e)}

    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def Track_shipment(request):
    try:
        package, created = Package.objects.get_or_create(
            tracking_number=request.data.get("tracking_number"),
            user=request.user,
            defaults={
                'email': request.user.email,
                'carrier': request.data.get("carrier"),
                'country': request.data.get("country"),
            }
        )
        
        # --- Multi-Carrier Agent Support ---
        tracking_number = request.data.get("tracking_number")
        carrier = request.data.get("carrier", "DHL")
        country = request.data.get("country", "")
        
        # Ask the agent to fetch info, summarize, and get coordinates
        agent_query = f"Track {carrier} package {tracking_number} in {country}."
        agent_response_raw = ask_agent(agent_query)
        
        import json
        import re

        def extract_json(text):
            # Try to find content between ```json and ```
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                return json_match.group(1).strip()
            # If not found, try to find the first '{' and last '}'
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return text[start:end+1]
            return text.strip()

        try:
            cleaned_response = extract_json(agent_response_raw)
            agent_data = json.loads(cleaned_response)
        except Exception as e:
            logger.error(f"Failed to parse agent response: {e}")
            logger.error(f"Raw response was: {agent_response_raw}")
            agent_data = {"status": "Error", "summary": "Failed to parse agent response.", "coordinates": []}

        # Update DB with the status from the agent
        new_status = agent_data.get("status", "Unknown")
        new_summary = agent_data.get("summary", "")
        events = agent_data.get("events", [])
        coords = agent_data.get("coordinates", [])
        
        package.package_status = new_status
        package.agent_summary = new_summary
        package.events_json = json.dumps(events)
        package.coordinates_json = json.dumps(coords)
        package.save()
            
        # Update Cache
        cache.set(f"status_{tracking_number}", new_status, timeout=3600)

        # Merge everything into response
        response_data = {
            "status": new_status,
            "agent_summary": new_summary,
            "coordinates": coords,
            "events": events,
            "tracking_number": tracking_number,
            "carrier": carrier
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def Get_package(request, tracking_number):
    try:
        package = Package.objects.get(user=request.user, tracking_number=tracking_number)
        import json
        events = []
        if package.events_json:
            events = json.loads(package.events_json)
        
        coords = []
        if package.coordinates_json:
            coords = json.loads(package.coordinates_json)
            
        return Response({
            "tracking_number": package.tracking_number,
            "status": package.package_status,
            "carrier": package.carrier,
            "summary": package.agent_summary,
            "events": events,
            "coordinates": coords
        }, status=status.HTTP_200_OK)
    except Package.DoesNotExist:
        return Response({"error": "Package not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def List_packages(request):
    packages = Package.objects.filter(user=request.user).order_by('-updated_at')
    data = []
    for p in packages:
        data.append({
            "tracking_number": p.tracking_number,
            "status": p.package_status,
            "carrier": p.carrier
        })
    return Response(data, status=status.HTTP_200_OK)
