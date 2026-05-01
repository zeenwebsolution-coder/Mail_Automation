from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from django_apscheduler.jobstores import DjangoJobStore
from carrierservice.models import Package
from carrierservice.views import get_tracking_status
from carrierservice.services.llm import generate_mail
from carrierservice.services.mail_sender import send_status_email
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

def check_status_job():
    print("--- Worker Heartbeat: Searching for due packages... ---", flush=True)
    
    # We use 30 seconds for your testing. Change back to minutes=30 for real use.
    thirty_seconds_ago = timezone.now() - timedelta(seconds=30)
    packages_due = Package.objects.filter(updated_at__lte=thirty_seconds_ago)
    
    print(f"Found {packages_due.count()} packages due for update.", flush=True)
    
    for package in packages_due:
        try:
            # 1. Check Cache first
            cache_key = f"status_{package.tracking_number}"
            cached_status = cache.get(cache_key)
            
            # 2. Fetch current status from API
            api_data = get_tracking_status(package.tracking_number)
            
            new_status = None
            if "shipments" in api_data and len(api_data["shipments"]) > 0:
                new_status = api_data["shipments"][0].get("status", {}).get("status")
            
            if new_status:
                current_ref_status = cached_status or package.package_status
                
                if new_status != current_ref_status:
                    print(f"CHANGE DETECTED for {package.tracking_number}!", flush=True)
                    
                    # 3. Use simple status message (No LLM)
                    subject = f"Package Update: {package.tracking_number}"
                    body_text = f"Your package {package.tracking_number} status has changed to: {new_status}"
                    
                    # 4. Send Email
                    if package.email:
                        send_status_email(
                            to_email=package.email,
                            subject=subject,
                            body_text=body_text
                        )
                    
                    package.package_status = new_status
                    # package.agent_summary = "" # We can clear or ignore this
                    cache.set(cache_key, new_status, timeout=3600)
                
                # 5. Reset timer
                package.save() 
                print(f"Check complete for {package.tracking_number}. Current status: {new_status}", flush=True)
        except Exception as e:
            print(f"Error checking package {package.tracking_number}: {str(e)}", flush=True)

class Command(BaseCommand):
    help = "Starts the background worker to poll DHL API for package updates."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            check_status_job,
            "interval",
            minutes=1,
            id="check_package_status",
            replace_existing=True
        )

        print("Running initial package check...", flush=True)
        check_status_job()

        print("Starting tracking worker scheduler... Press Ctrl+C to exit.", flush=True)
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("Worker stopped.", flush=True)
